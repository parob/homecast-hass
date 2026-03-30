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
    HomecastState,
    HomecastWebSocket,
)

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL, UPDATE_INTERVAL_WS

_LOGGER = logging.getLogger(__name__)

# Map relay characteristic types to pyhomecast state keys.
# The relay sends friendly names (e.g. "brightness") which the server passes
# through in broadcasts. CHAR_TO_SIMPLE maps these to REST API state keys.
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
}


class HomecastCoordinator(DataUpdateCoordinator[HomecastState]):
    """Coordinator that polls the Homecast REST API and receives WebSocket push updates."""

    def __init__(
        self,
        hass: HomeAssistant,
        entry: ConfigEntry,
        client: HomecastClient,
        refresh_token: Callable[[], Coroutine[Any, Any, None]],
        ws: HomecastWebSocket | None = None,
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
        self._uuid_to_device: dict[str, str] = {}

    async def async_setup_websocket(self) -> None:
        """Set up the WebSocket connection for push updates."""
        if not self._ws:
            return

        self._ws.set_callback(self._on_ws_message)

        try:
            token = self.client._token  # noqa: SLF001
            if token:
                await self._ws.connect(token)
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
        if not self.data:
            return
        self._uuid_to_device.clear()
        for unique_id, device in self.data.devices.items():
            # accessory_key is like "ceiling_light_c3d4" — last 4 chars are UUID suffix
            acc_suffix = device.accessory_key[-4:]
            home_suffix = device.home_key[-4:]
            key = f"{home_suffix}:{acc_suffix}"
            self._uuid_to_device[key] = unique_id

    def _resolve_device_key(
        self, home_id: str | None, accessory_id: str | None
    ) -> str | None:
        """Resolve a broadcast's homeId + accessoryId to a device unique_id."""
        if not home_id or not accessory_id:
            return None
        key = f"{home_id[-4:].lower()}:{accessory_id[-4:].lower()}"
        return self._uuid_to_device.get(key)

    def _on_ws_message(self, message: dict[str, Any]) -> None:
        """Handle an incoming WebSocket broadcast message."""
        msg_type = message.get("type", "")

        if msg_type == "characteristic_update":
            self._apply_characteristic_update(message)
        elif msg_type == "reachability_update":
            # Trigger a full refresh to update availability
            self.hass.async_create_task(self.async_request_refresh())
        elif msg_type == "relay_status_update":
            connected = message.get("connected", True)
            if not connected:
                # Relay went offline — full resync
                self.hass.async_create_task(self.async_request_refresh())

    def _apply_characteristic_update(self, message: dict[str, Any]) -> None:
        """Apply an incremental characteristic update to the in-memory state."""
        if not self.data:
            return

        device_key = self._resolve_device_key(
            message.get("homeId"), message.get("accessoryId")
        )
        if not device_key:
            return

        device = self.data.devices.get(device_key)
        if not device:
            return

        char_type = message.get("characteristicType", "")
        state_key = CHAR_TO_STATE_KEY.get(char_type)
        if not state_key:
            return

        value = message.get("value")
        device.state[state_key] = value
        self.async_set_updated_data(self.data)

    async def _async_update_data(self) -> HomecastState:
        """Fetch state from the Homecast API."""
        try:
            await self._refresh_token()
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
        if self._ws and self.client._token:  # noqa: SLF001
            self._ws.set_token(self.client._token)  # noqa: SLF001

        return state

    async def async_set_state(self, updates: dict[str, Any]) -> None:
        """Send a state update and request a refresh."""
        await self._refresh_token()
        await self.client.set_state(updates)
        await self.async_request_refresh()

    async def async_shutdown(self) -> None:
        """Disconnect WebSocket on shutdown."""
        await super().async_shutdown()
        if self._ws:
            await self._ws.disconnect()
