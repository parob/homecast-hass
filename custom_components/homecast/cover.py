"""Cover platform for Homecast (blinds, window coverings)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
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
    """Set up Homecast covers."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "blind":
                entities.append(HomecastCover(coordinator, device))
    async_add_entities(entities)


class HomecastCover(HomecastEntity, CoverEntity):
    """Represents a Homecast blind / window covering."""

    _attr_name = None
    _attr_device_class = CoverDeviceClass.BLIND

    @property
    def supported_features(self) -> CoverEntityFeature:
        features = CoverEntityFeature(0)
        device = self.device
        if device and "target" in device.settable:
            features |= (
                CoverEntityFeature.SET_POSITION
                | CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
            )
        return features

    @property
    def current_cover_position(self) -> int | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("target")

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get("position")
        if position is not None:
            await self._async_set_state({"target": position})

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._async_set_state({"target": 100})

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._async_set_state({"target": 0})
