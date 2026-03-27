"""Lock platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast locks."""
    coordinator = entry.runtime_data.coordinator

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "lock":
                entities.append(HomecastLock(coordinator, device))
    async_add_entities(entities)


class HomecastLock(HomecastEntity, LockEntity):
    """Represents a Homecast lock."""

    _attr_name = None

    @property
    def is_locked(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("locked")

    async def async_lock(self, **kwargs: Any) -> None:
        await self._async_set_state({"lock_target": True})

    async def async_unlock(self, **kwargs: Any) -> None:
        await self._async_set_state({"lock_target": False})
