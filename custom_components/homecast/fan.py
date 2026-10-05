"""Fan platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.fan import FanEntity, FanEntityFeature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast fans."""
    coordinator = entry.runtime_data.coordinator

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "fan":
                entities.append(HomecastFan(coordinator, device))
    async_add_entities(entities)


class HomecastFan(HomecastEntity, FanEntity):
    """Represents a Homecast fan.

    HomeKit has two fan services: the original Fan switches with `on`, the newer
    Fan v2 with `active`. Whichever the accessory reports is the one driven.
    """

    _attr_name = None

    @property
    def _power_key(self) -> str:
        device = self.device
        if device is not None and "on" not in device.state and "active" in device.state:
            return "active"
        return "on"

    @property
    def supported_features(self) -> FanEntityFeature:
        features = FanEntityFeature.TURN_ON | FanEntityFeature.TURN_OFF
        if self.settable("speed", "rotation_speed"):
            features |= FanEntityFeature.SET_SPEED
        return features

    @property
    def is_on(self) -> bool | None:
        value = self.state_value(self._power_key)
        return None if value is None else bool(value)

    @property
    def percentage(self) -> int | None:
        """Return speed percentage (Homecast uses 0-100, same as HA)."""
        speed = self.state_value("speed", "rotation_speed")
        return None if speed is None else round(speed)

    async def async_turn_on(
        self,
        percentage: int | None = None,
        preset_mode: str | None = None,
        **kwargs: Any,
    ) -> None:
        payload: dict[str, Any] = {self._power_key: True}
        if percentage is not None:
            payload["speed"] = percentage
        await self._async_set_state(payload)

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_state({self._power_key: False})

    async def async_set_percentage(self, percentage: int) -> None:
        if percentage == 0:
            await self.async_turn_off()
            return
        await self._async_set_state({"speed": percentage})
