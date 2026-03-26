"""Sensor platform for Homecast."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import PERCENTAGE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity
from .models import HomecastDevice

# Device types that are dedicated sensors
_SENSOR_TYPES = {"temperature", "light_sensor"}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast sensors."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities: list[SensorEntity] = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            # Dedicated sensor devices
            if device.device_type == "temperature":
                entities.append(HomecastTemperatureSensor(coordinator, device))
            elif device.device_type == "light_sensor":
                entities.append(HomecastLightSensor(coordinator, device))

            # Battery level from any device that has it
            if "battery" in device.state:
                entities.append(HomecastBatterySensor(coordinator, device))

    async_add_entities(entities)


class HomecastTemperatureSensor(HomecastEntity, SensorEntity):
    """Temperature sensor."""

    _attr_name = None
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    @property
    def native_value(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("current_temp")


class HomecastLightSensor(HomecastEntity, SensorEntity):
    """Ambient light sensor."""

    _attr_name = None
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = "lx"

    @property
    def native_value(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("ambient_light")


class HomecastBatterySensor(HomecastEntity, SensorEntity):
    """Battery level sensor (companion to any device)."""

    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = "diagnostic"

    def __init__(
        self,
        coordinator: HomecastCoordinator,
        device: HomecastDevice,
    ) -> None:
        super().__init__(coordinator, device)
        # Override unique_id to avoid collision with the main entity
        self._attr_unique_id = f"{device.unique_id}_battery"
        self._attr_name = "Battery"

    @property
    def native_value(self) -> int | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("battery")
