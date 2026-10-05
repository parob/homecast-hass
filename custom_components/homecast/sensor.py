"""Sensor platform for Homecast."""

from __future__ import annotations

from homeassistant.components.sensor import (
    SensorDeviceClass,
    SensorEntity,
    SensorStateClass,
)
from homeassistant.const import (
    LIGHT_LUX,
    PERCENTAGE,
    EntityCategory,
    UnitOfTemperature,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from pyhomecast import HomecastDevice

from . import HomecastConfigEntry
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity

# Readings an accessory can carry besides its main function. HomeKit groups an
# accessory's services together, so a Hue motion sensor is also a thermometer
# and a light meter; Homecast reports every reading on the one accessory, and
# each becomes its own sensor here. Device types listed are the ones whose own
# entity already shows that reading.
_TEMPERATURE = "current_temp"
_ILLUMINANCE = "current_ambient_light_level"
_HUMIDITY = "relative_humidity"


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast sensors."""
    coordinator = entry.runtime_data.coordinator

    entities: list[SensorEntity] = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            state = device.state
            kind = device.device_type

            # The accessory's own reading is its main entity...
            if kind == "temperature":
                entities.append(HomecastTemperatureSensor(coordinator, device))
            elif kind == "light_sensor":
                entities.append(HomecastLightSensor(coordinator, device))

            # A service group repeats its first member's state, so companions
            # on it would duplicate that member's.
            if device.is_group:
                continue

            # ...and the others it carries are companions on the same device.
            if _TEMPERATURE in state and kind not in ("temperature", "climate"):
                entities.append(HomecastTemperatureSensor(coordinator, device, companion=True))
            if _ILLUMINANCE in state and kind != "light_sensor":
                entities.append(HomecastLightSensor(coordinator, device, companion=True))
            if _HUMIDITY in state and kind != "climate":
                entities.append(HomecastHumiditySensor(coordinator, device))
            if "battery" in state:
                entities.append(HomecastBatterySensor(coordinator, device))

    async_add_entities(entities)


class _HomecastSensor(HomecastEntity, SensorEntity):
    """A sensor reading one key of an accessory's state."""

    _key: str
    _suffix: str

    def __init__(
        self,
        coordinator: HomecastCoordinator,
        device: HomecastDevice,
        companion: bool = True,
    ) -> None:
        super().__init__(coordinator, device)
        if companion:
            # Avoid colliding with the accessory's main entity
            self._attr_unique_id = f"{device.unique_id}_{self._suffix}"
        else:
            self._attr_name = None

    @property
    def native_value(self) -> float | None:
        return self.state_value(self._key)


class HomecastTemperatureSensor(_HomecastSensor):
    """Temperature sensor."""

    _key = _TEMPERATURE
    _suffix = "temperature"
    _attr_device_class = SensorDeviceClass.TEMPERATURE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = UnitOfTemperature.CELSIUS

    def __init__(self, coordinator, device, companion: bool = False) -> None:
        super().__init__(coordinator, device, companion)


class HomecastLightSensor(_HomecastSensor):
    """Ambient light sensor."""

    _key = _ILLUMINANCE
    _suffix = "illuminance"
    _attr_device_class = SensorDeviceClass.ILLUMINANCE
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = LIGHT_LUX

    def __init__(self, coordinator, device, companion: bool = False) -> None:
        super().__init__(coordinator, device, companion)


class HomecastHumiditySensor(_HomecastSensor):
    """Relative humidity reading."""

    _key = _HUMIDITY
    _suffix = "humidity"
    _attr_device_class = SensorDeviceClass.HUMIDITY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE


class HomecastBatterySensor(_HomecastSensor):
    """Battery level sensor (companion to any device)."""

    _key = "battery"
    _suffix = "battery"
    _attr_device_class = SensorDeviceClass.BATTERY
    _attr_state_class = SensorStateClass.MEASUREMENT
    _attr_native_unit_of_measurement = PERCENTAGE
    _attr_entity_category = EntityCategory.DIAGNOSTIC
