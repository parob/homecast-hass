"""DataUpdateCoordinator for Homecast."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
from datetime import timedelta
import logging
from typing import Any

from pyhomecast import (
    HomecastAuthError,
    HomecastClient,
    HomecastConnectionError,
    HomecastError,
    HomecastState,
    HomecastWebSocket,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, UPDATE_INTERVAL_WS

_LOGGER = logging.getLogger(__name__)

# Map relay characteristic types (what a `characteristic_update` broadcast
# carries) to the keys GET /rest/state reports them under. A characteristic not
# listed here is reported under its own name, so an update to it is applied
# under that name if the accessory already has it.
CHAR_TO_STATE_KEY: dict[str, str] = {
    "on": "on",
    "power_state": "on",
    "active": "active",
    "brightness": "brightness",
    "hue": "hue",
    "saturation": "saturation",
    "color_temperature": "color_temp",
    "current_temperature": "current_temp",
    "heating_threshold": "heat_target",
    "cooling_threshold": "cool_target",
    "target_temperature": "target_temp",
    "lock_current_state": "locked",
    "lock_target_state": "lock_target",
    "security_system_current_state": "alarm_state",
    "security_system_target_state": "alarm_target",
    "motion_detected": "motion",
    "contact_state": "contact",
    "battery_level": "battery",
    "status_low_battery": "low_battery",
    "volume": "volume",
    "mute": "mute",
    "rotation_speed": "speed",
    "target_position": "target",
    "target_heater_cooler_state": "hvac_mode",
    "current_heater_cooler_state": "hvac_state",
}

# Broadcasts carry HomeKit's raw values; GET /rest/state reports these as words
# or booleans. Convert so a pushed update reads the same as a polled one.
_ENUM_WORDS: dict[str, dict[int, str]] = {
    "alarm_state": {0: "home", 1: "away", 2: "night", 3: "off", 4: "triggered"},
    "alarm_target": {0: "home", 1: "away", 2: "night", 3: "off"},
    "hvac_state": {0: "inactive", 1: "idle", 2: "heating", 3: "cooling"},
    "hvac_mode": {0: "auto", 1: "heat", 2: "cool"},
}
_BOOLEANS = {"on", "active", "motion", "mute", "low_battery"}


def state_key_for(char_type: str, state: dict[str, Any]) -> str | None:
    """The state key a broadcast for `char_type` updates on this accessory."""
    key = CHAR_TO_STATE_KEY.get(char_type)
    if key is not None:
        return key
    # Reported under its own name: current_position, position_state,
    # current_ambient_light_level, relative_humidity, swing_mode, ...
    return char_type if char_type in state else None


def format_state_value(key: str, value: Any) -> Any:
    """A broadcast value in the form GET /rest/state reports it."""
    if value is None:
        return None
    if key in _ENUM_WORDS and isinstance(value, (int, float)) and not isinstance(value, bool):
        return _ENUM_WORDS[key].get(int(value), f"unknown_{value}")
    if key == "locked":
        return value == 1 if isinstance(value, (int, float)) else bool(value)
    if key in _BOOLEANS:
        return bool(value)
    return value


class HomecastCoordinator(DataUpdateCoordinator[HomecastState]):
    """Coordinator that polls the Homecast REST API and receives WebSocket push updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: HomecastClient,
        refresh_token: Callable[[], Coroutine[Any, Any, str]],
        ws: HomecastWebSocket | None = None,
        initial_token: str | None = None,
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            config_entry=entry,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self._refresh_token = refresh_token
        self._ws = ws
        self._current_token: str | None = initial_token
        self._uuid_to_device: dict[str, str] = {}

    async def async_setup_websocket(self) -> None:
        """Set up the WebSocket connection for push updates."""
        if not self._ws:
            return

        self._ws.set_callback(self._on_ws_message)

        try:
            if self._current_token:
                await self._ws.connect(self._current_token)
        except (HomecastAuthError, HomecastConnectionError) as err:
            _LOGGER.warning("WebSocket connection failed, using polling: %s", err)
            return

        # Subscribe to all homes
        if self.data and self.data.homes:
            await self._ws.subscribe(list(self.data.homes.keys()))

        # Build UUID-suffix to device key mapping
        self._build_uuid_mapping()

        # Reduce polling frequency — WebSocket handles real-time updates
        self.update_interval = timedelta(seconds=UPDATE_INTERVAL_WS)
        _LOGGER.info("WebSocket connected, polling reduced to %ds", UPDATE_INTERVAL_WS)

    def _build_uuid_mapping(self) -> None:
        """Build a mapping from (home_suffix, accessory_suffix) to device unique_id.

        The server broadcasts use HomeKit UUIDs (e.g. "3A14B2C1-...") while
        pyhomecast uses slug keys ending with the last 4 chars of the UUID.
        This mapping allows fast lookup from broadcast data.
        """
        self._uuid_to_device.clear()
        for unique_id, device in self.data.devices.items():
            # accessory_key is like "ceiling_light_c3d4" — last 4 chars are UUID suffix
            acc_suffix = device.accessory_key[-4:]
            home_suffix = device.home_key[-4:]
            key = f"{home_suffix}:{acc_suffix}"
            self._uuid_to_device[key] = unique_id

    def _resolve_device_key(self, home_id: str, accessory_id: str) -> str | None:
        """Resolve a broadcast's homeId + accessoryId to a device unique_id."""
        key = f"{home_id[-4:].lower()}:{accessory_id[-4:].lower()}"
        return self._uuid_to_device.get(key)

    def _on_ws_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming WebSocket broadcast message."""
        msg_type = message.get("type", "")

        if msg_type == "characteristic_update":
            device_key = self._apply_state_update(
                message.get("homeId"),
                message.get("accessoryId"),
                message.get("characteristicType", ""),
                message.get("value"),
            )
            # If this accessory is a member of a service group, propagate
            # the state change to the group entity too
            if device_key and self.data:
                group_key = self.data.member_to_group.get(device_key)
                if group_key:
                    group = self.data.devices.get(group_key)
                    if group:
                        char_type = message.get("characteristicType", "")
                        state_key = state_key_for(char_type, group.state)
                        if state_key:
                            group.state[state_key] = format_state_value(
                                state_key, message.get("value")
                            )
                            self.async_set_updated_data(self.data)
        elif msg_type == "service_group_update":
            # Update the group entity itself
            self._apply_state_update(
                message.get("homeId"),
                message.get("groupId"),
                message.get("characteristicType", ""),
                message.get("value"),
            )
            # Group toggles also change all member accessories — full refresh
            # to pick up their new states
            self.hass.async_create_task(self.async_request_refresh())
        elif msg_type == "reachability_update":
            self.hass.async_create_task(self.async_request_refresh())
        elif msg_type == "relay_status_update":
            # Both ways: a relay going offline takes its homes' accessories
            # with it, and one coming back has to bring them back — otherwise
            # they stayed unavailable until the next five-minute poll.
            self.hass.async_create_task(self.async_request_refresh())

    def _apply_state_update(
        self,
        home_id: str | None,
        entity_id: str | None,
        char_type: str,
        value: Any,
    ) -> str | None:
        """Apply an incremental state update from a WS broadcast.

        Returns the device key if the update was applied, or None.
        """
        if not self.data or not home_id or not entity_id:
            return None

        device_key = self._resolve_device_key(home_id, entity_id)
        if not device_key:
            return None

        device = self.data.devices.get(device_key)
        if not device:
            return None

        state_key = state_key_for(char_type, device.state)
        if not state_key:
            return None

        device.state[state_key] = format_state_value(state_key, value)
        self.async_set_updated_data(self.data)
        return device_key

    async def _async_update_data(self) -> HomecastState:
        """Fetch state from the Homecast API."""
        try:
            self._current_token = await self._refresh_token()
            state = await self.client.get_state()
        except HomecastAuthError as err:
            raise ConfigEntryAuthFailed from err
        except HomecastConnectionError as err:
            raise UpdateFailed(f"Error communicating with Homecast: {err}") from err

        # Re-subscribe if new homes appeared
        if self._ws and self._ws.connected and state.homes:
            old_homes = set(self.data.homes.keys()) if self.data else set()
            new_homes = set(state.homes.keys())
            if new_homes != old_homes:
                await self._ws.subscribe(list(new_homes))

        # Rebuild UUID mapping with fresh data
        self.data = state
        self._build_uuid_mapping()

        # Update WS token in case it was refreshed
        if self._ws and self._current_token:
            self._ws.set_token(self._current_token)

        return state

    async def async_set_state(self, updates: dict[str, Any]) -> None:
        """Send a state update and request a refresh."""
        self._current_token = await self._refresh_token()
        try:
            await self.client.set_state(updates)
        except HomecastAuthError as err:
            raise ConfigEntryAuthFailed from err
        except HomecastError as err:
            _LOGGER.error("Failed to control device: %s", err)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Disconnect WebSocket on shutdown."""
        await super().async_shutdown()
        if self._ws:
            await self._ws.disconnect()
