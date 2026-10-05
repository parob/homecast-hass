"""Binary sensor platform for Homecast."""

from __future__ import annotations

from homeassistant.components.binary_sensor import (
    BinarySensorDeviceClass,
    BinarySensorEntity,
)
from homeassistant.const import EntityCategory
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity
from pyhomecast import HomecastDevice

# HomeKit detector characteristic -> HA device class. HomeKit reports each as
# 0 (not detected) or 1 (detected).
_DETECTORS: dict[str, BinarySensorDeviceClass] = {
    "occupancy_detected": BinarySensorDeviceClass.OCCUPANCY,
    "leak_detected": BinarySensorDeviceClass.MOISTURE,
    "smoke_detected": BinarySensorDeviceClass.SMOKE,
    "carbon_monoxide_detected": BinarySensorDeviceClass.CO,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast binary sensors."""
    coordinator = entry.runtime_data.coordinator

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

            # Detector readings an accessory carries, whatever its main type:
            # an occupancy sensor that also measures temperature is reported
            # as a temperature sensor, and a leak or smoke sensor has no type
            # of its own at all. Not on a service group, which repeats its
            # first member's state.
            if not device.is_group:
                for key, device_class in _DETECTORS.items():
                    if key in device.state:
                        entities.append(
                            HomecastDetectorSensor(coordinator, device, key, device_class)
                        )

            # Low battery from any device that has it. Not on a service group:
            # it repeats its first member's state, battery included.
            if "low_battery" in device.state and not device.is_group:
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
    _attr_entity_category = EntityCategory.DIAGNOSTIC

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


class HomecastDetectorSensor(HomecastEntity, BinarySensorEntity):
    """Occupancy, leak, smoke or carbon monoxide detector reading."""

    def __init__(
        self,
        coordinator: HomecastCoordinator,
        device: HomecastDevice,
        key: str,
        device_class: BinarySensorDeviceClass,
    ) -> None:
        super().__init__(coordinator, device)
        self._key = key
        self._attr_unique_id = f"{device.unique_id}_{key}"
        self._attr_device_class = device_class

    @property
    def is_on(self) -> bool | None:
        value = self.state_value(self._key)
        return None if value is None else bool(value)
