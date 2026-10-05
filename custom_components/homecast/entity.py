"""Base entity for Homecast."""

from __future__ import annotations

from typing import Any

from pyhomecast import HomecastDevice

from homeassistant.helpers.device_registry import DeviceInfo
from homeassistant.helpers.update_coordinator import CoordinatorEntity

from .const import DOMAIN
from .coordinator import HomecastCoordinator


class HomecastEntity(CoordinatorEntity[HomecastCoordinator]):
    """Base class for Homecast entities."""

    _attr_has_entity_name = True

    def __init__(
        self,
        coordinator: HomecastCoordinator,
        device: HomecastDevice,
    ) -> None:
        """Initialize the entity."""
        super().__init__(coordinator)
        self._device_id = device.unique_id
        self._attr_unique_id = device.unique_id

        # Prefix room name with home name when there are multiple homes
        multiple_homes = len(coordinator.data.homes) > 1
        area = (
            f"{device.home_name} - {device.room_name}"
            if multiple_homes
            else device.room_name
        )

        self._attr_device_info = DeviceInfo(
            identifiers={(DOMAIN, device.unique_id)},
            name=device.name,
            manufacturer="Homecast (HomeKit)",
            model=device.device_type.replace("_", " ").title(),
            suggested_area=area,
        )

    @property
    def device(self) -> HomecastDevice | None:
        """Return the current device data from the coordinator."""
        return self.coordinator.data.devices.get(self._device_id)

    def state_value(self, *keys: str) -> Any:
        """The first of `keys` the accessory reports, or None.

        Homecast reports properties under the names set_state accepts
        (`target`, `speed`, `hvac_mode`). A Community relay running an older
        bundle still reports a few under HomeKit's own names
        (`target_position`, `rotation_speed`, `target_heater_cooler_state`), so
        callers pass the current name first and the legacy one after it.
        """
        device = self.device
        if device is None:
            return None
        for key in keys:
            value = device.state.get(key)
            if value is not None:
                return value
        return None

    def settable(self, *keys: str) -> bool:
        """True if any of `keys` is writable on this accessory."""
        device = self.device
        return device is not None and any(k in device.settable for k in keys)

    def valid_options(self, key: str) -> list[Any] | None:
        """The values the accessory accepts for `key`, when Homecast says."""
        device = self.device
        if device is None:
            return None
        options = device.state.get("_options")
        if isinstance(options, dict) and isinstance(options.get(key), list):
            return options[key]
        return None

    @property
    def available(self) -> bool:
        """Return True if the device is available."""
        return super().available and self.device is not None

    async def _async_set_state(self, props: dict[str, Any]) -> None:
        """Send a state update for this device."""
        device = self.device
        if device is None:
            return
        await self.coordinator.async_set_state(
            {
                device.home_key: {
                    device.room_key: {
                        device.accessory_key: props,
                    },
                },
            }
        )
