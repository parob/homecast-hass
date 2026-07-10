"""Switch platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.switch import SwitchDeviceClass, SwitchEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast switches."""
    coordinator = entry.runtime_data.coordinator

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type in ("switch", "outlet"):
                entities.append(HomecastSwitch(coordinator, device))
    async_add_entities(entities)


class HomecastSwitch(HomecastEntity, SwitchEntity):
    """Represents a Homecast switch or outlet."""

    _attr_name = None

    @property
    def device_class(self) -> SwitchDeviceClass | None:
        device = self.device
        if device and device.device_type == "outlet":
            return SwitchDeviceClass.OUTLET
        return SwitchDeviceClass.SWITCH

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("on")

    async def async_turn_on(self, **kwargs: Any) -> None:
        await self._async_set_state({"on": True})

    async def async_turn_off(self, **kwargs: Any) -> None:
        await self._async_set_state({"on": False})
