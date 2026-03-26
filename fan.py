"""Fan platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast fans."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "fan":
                entities.append(HomecastFan(coordinator, device))
    async_add_entities(entities)


class HomecastFan(HomecastEntity, FanEntity):
    """Represents a Homecast fan."""

    _attr_name = None

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        device = self.device
        if device and "speed" in device.settable:
            features |= FanEntityFeature.SET_SPEED
        return features

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("on")

    @property
    def percentage(self) -> int | None:
        """Return speed percentage (Homecast uses 0-100, same as HA)."""
        device = self.device
        if device is None:
            return None
        return device.state.get("speed")

    async def async_turn_on(
        self,
        percentage: int | None = None,
        **kwargs: Any,
    ) -> None:
        payload: dict[str, Any] = {"on": True}
        if percentage is not None:
            payload["speed"] = percentage
        await self._async_set_state(payload)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_state({"on": False})

    async def async_set_percentage(self, percentage: int) -> None:
        await self._async_set_state({"speed": percentage})
