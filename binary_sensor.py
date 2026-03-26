"""Binary sensor platform for Homecast."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity
from .models import HomecastDevice


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast binary sensors."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[BinarySensorEntity] = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            # Dedicated binary sensor devices
            if device.device_type == "motion":
                entities.append(HomecastMotionSensor(coordinator, device))
            elif device.device_type == "contact":
                entities.append(HomecastContactSensor(coordinator, device))
            elif device.device_type == "doorbell":
                entities.append(HomecastDoorbellSensor(coordinator, device))

            # Low battery from any device that has it
            if "low_battery" in device.state:
                entities.append(HomecastLowBatterySensor(coordinator, device))

    async_add_entities(entities)


class HomecastMotionSensor(HomecastEntity, BinarySensorEntity):
    """Motion sensor."""

    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.MOTION

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("motion")


class HomecastContactSensor(HomecastEntity, BinarySensorEntity):
    """Contact sensor (door/window)."""

    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.DOOR

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        # HomeKit: 0 = detected (closed), 1 = not detected (open)
        # HA: True = open, False = closed
        contact = device.state.get("contact")
        if contact is None:
            return None
        return bool(contact)


class HomecastDoorbellSensor(HomecastEntity, BinarySensorEntity):
    """Doorbell sensor."""

    _attr_name = None
    _attr_device_class = BinarySensorDeviceClass.OCCUPANCY

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("programmable_switch_event") is not None


class HomecastLowBatterySensor(HomecastEntity, BinarySensorEntity):
    """Low battery binary sensor (companion to any device)."""

    _attr_device_class = BinarySensorDeviceClass.BATTERY
    _attr_entity_category = "diagnostic"

    def __init__(
        self,
        coordinator: HomecastCoordinator,
        device: HomecastDevice,
    ) -> None:
        super().__init__(coordinator, device)
        self._attr_unique_id = f"{device.unique_id}_low_battery"
        self._attr_name = "Battery low"

    @property
    def is_on(self) -> bool | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("low_battery")
