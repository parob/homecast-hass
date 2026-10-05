"""Cover platform for Homecast (blinds, window coverings)."""

from __future__ import annotations

from typing import Any

from homeassistant.components.cover import (
    ATTR_POSITION,
    CoverDeviceClass,
    CoverEntity,
    CoverEntityFeature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity

# HomeKit PositionState
_CLOSING = 0
_OPENING = 1


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast covers."""
    coordinator = entry.runtime_data.coordinator

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
        if self.settable("target", "target_position"):
            features |= (
                CoverEntityFeature.SET_POSITION
                | CoverEntityFeature.OPEN
                | CoverEntityFeature.CLOSE
            )
        return features

    @property
    def current_cover_position(self) -> int | None:
        # Where the blind is, not where it was last told to go. Falls back to
        # the target for a covering that does not report its position.
        return self.state_value("current_position", "target", "target_position")

    @property
    def is_closed(self) -> bool | None:
        pos = self.current_cover_position
        if pos is None:
            return None
        return pos == 0

    @property
    def is_opening(self) -> bool | None:
        state = self.state_value("position_state")
        return None if state is None else state == _OPENING

    @property
    def is_closing(self) -> bool | None:
        state = self.state_value("position_state")
        return None if state is None else state == _CLOSING

    async def async_set_cover_position(self, **kwargs: Any) -> None:
        position = kwargs.get(ATTR_POSITION)
        if position is not None:
            await self._async_set_state({"target": position})

    async def async_open_cover(self, **kwargs: Any) -> None:
        await self._async_set_state({"target": 100})

    async def async_close_cover(self, **kwargs: Any) -> None:
        await self._async_set_state({"target": 0})
