"""Lock platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.lock import LockEntity
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
    """Set up Homecast locks."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

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
