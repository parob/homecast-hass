"""Climate platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.config_entries import ConfigEntry
from homeassistant.const import UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomecastCoordinator
from .entity import HomecastEntity

# Homecast HVAC mode strings -> HA HVACMode
_HVAC_MODE_MAP: dict[str, HVACMode] = {
    "auto": HVACMode.HEAT_COOL,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
}
_HVAC_MODE_REVERSE: dict[HVACMode, str] = {v: k for k, v in _HVAC_MODE_MAP.items()}

# Homecast HVAC state strings -> HA HVACAction
_HVAC_ACTION_MAP: dict[str, HVACAction] = {
    "inactive": HVACAction.OFF,
    "idle": HVACAction.IDLE,
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast climate entities."""
    coordinator: HomecastCoordinator = hass.data[DOMAIN][entry.entry_id]["coordinator"]

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "climate":
                entities.append(HomecastClimate(coordinator, device))
    async_add_entities(entities)


class HomecastClimate(HomecastEntity, ClimateEntity):
    """Represents a Homecast thermostat / heater-cooler."""

    _attr_name = None
    _attr_temperature_unit = UnitOfTemperature.CELSIUS
    _enable_turn_on_off_backwards_compat = False

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes = [HVACMode.OFF]
        device = self.device
        if device and "hvac_mode" in device.settable:
            modes.extend([HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL])
        elif device and "active" in device.settable:
            modes.append(HVACMode.HEAT_COOL)
        return modes

    @property
    def hvac_mode(self) -> HVACMode | None:
        device = self.device
        if device is None:
            return None
        # Check if actively off
        active = device.state.get("active")
        if active is False:
            return HVACMode.OFF
        mode_str = device.state.get("hvac_mode")
        if mode_str:
            return _HVAC_MODE_MAP.get(str(mode_str), HVACMode.HEAT_COOL)
        return HVACMode.HEAT_COOL

    @property
    def hvac_action(self) -> HVACAction | None:
        device = self.device
        if device is None:
            return None
        state_str = device.state.get("hvac_state")
        if state_str:
            return _HVAC_ACTION_MAP.get(str(state_str))
        return None

    @property
    def current_temperature(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("current_temp")

    @property
    def target_temperature(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("target_temp")

    @property
    def target_temperature_high(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("cool_target")

    @property
    def target_temperature_low(self) -> float | None:
        device = self.device
        if device is None:
            return None
        return device.state.get("heat_target")

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature(0)
        device = self.device
        if device is None:
            return features
        settable = device.settable
        if "target_temp" in settable:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE
        if "heat_target" in settable or "cool_target" in settable:
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        if "active" in settable:
            features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        return features

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        if hvac_mode == HVACMode.OFF:
            await self._async_set_state({"active": False})
        else:
            payload: dict[str, Any] = {"active": True}
            homecast_mode = _HVAC_MODE_REVERSE.get(hvac_mode)
            if homecast_mode:
                payload["hvac_mode"] = homecast_mode
            await self._async_set_state(payload)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        payload: dict[str, Any] = {}
        if "temperature" in kwargs:
            payload["target_temp"] = kwargs["temperature"]
        if "target_temp_high" in kwargs:
            payload["cool_target"] = kwargs["target_temp_high"]
        if "target_temp_low" in kwargs:
            payload["heat_target"] = kwargs["target_temp_low"]
        if payload:
            await self._async_set_state(payload)
