"""Climate platform for Homecast.

HomeKit has two climate services and they are driven differently:

- **Heater-Cooler** (air conditioners, most radiators and underfloor heating
  bridged to HomeKit). Power is `active`; the mode is `hvac_mode`
  (auto/heat/cool) and is kept while the unit is off; the setpoints are
  `heat_target` and `cool_target`. Which modes a unit has is in
  `_options.hvac_mode` — a radiator offers only `heat`.
- **Thermostat**. No power switch: off is a mode. The mode is
  `heating_cooling_target` (0 off, 1 heat, 2 cool, 3 auto) and the setpoint is
  `target_temp`.
"""

from __future__ import annotations

from typing import Any

from homeassistant.components.climate import (
    ATTR_HVAC_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    SWING_OFF,
    SWING_ON,
    ClimateEntity,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.const import ATTR_TEMPERATURE, UnitOfTemperature
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity

# Heater-Cooler: Homecast's words, and HomeKit's integers (older Community relays)
_HC_MODES: dict[str, HVACMode] = {
    "auto": HVACMode.HEAT_COOL,
    "heat": HVACMode.HEAT,
    "cool": HVACMode.COOL,
}
_HC_MODE_WORD: dict[HVACMode, str] = {v: k for k, v in _HC_MODES.items()}
_HC_MODE_INT: dict[int, str] = {0: "auto", 1: "heat", 2: "cool"}

_HC_ACTIONS: dict[str, HVACAction] = {
    "inactive": HVACAction.OFF,
    "idle": HVACAction.IDLE,
    "heating": HVACAction.HEATING,
    "cooling": HVACAction.COOLING,
}
_HC_ACTION_INT: dict[int, str] = {0: "inactive", 1: "idle", 2: "heating", 3: "cooling"}

# Thermostat: HomeKit's TargetHeatingCoolingState / CurrentHeatingCoolingState
_TS_MODES: dict[int, HVACMode] = {
    0: HVACMode.OFF,
    1: HVACMode.HEAT,
    2: HVACMode.COOL,
    3: HVACMode.HEAT_COOL,
}
_TS_MODE_INT: dict[HVACMode, int] = {v: k for k, v in _TS_MODES.items()}
_TS_ACTIONS: dict[int, HVACAction] = {
    1: HVACAction.HEATING,
    2: HVACAction.COOLING,
}

_MODE_ORDER = [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL]


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast climate entities."""
    coordinator = entry.runtime_data.coordinator

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
    _attr_target_temperature_step = 0.5
    _attr_swing_modes = [SWING_OFF, SWING_ON]

    # --- which service this is -------------------------------------------

    @property
    def _is_thermostat(self) -> bool:
        device = self.device
        if device is None:
            return False
        state = device.state
        return "heating_cooling_target" in state or (
            "target_temp" in state
            and "hvac_mode" not in state
            and "target_heater_cooler_state" not in state
            and "active" not in state
        )

    def _hc_mode_word(self) -> str | None:
        """The heater-cooler's mode as a word, whatever the relay reported."""
        word = self.state_value("hvac_mode")
        if word is None:
            raw = self.state_value("target_heater_cooler_state")
            word = _HC_MODE_INT.get(raw) if isinstance(raw, int) else None
        return str(word) if word is not None else None

    def _hc_underlying_mode(self) -> HVACMode | None:
        """Heat, cool or auto — the mode the unit is in, or returns to when on."""
        word = self._hc_mode_word()
        if word in _HC_MODES:
            return _HC_MODES[word]
        # No mode characteristic: a unit that only heats or only cools.
        has_heat = self.state_value("heat_target") is not None
        has_cool = self.state_value("cool_target") is not None
        if has_heat and not has_cool:
            return HVACMode.HEAT
        if has_cool and not has_heat:
            return HVACMode.COOL
        return HVACMode.HEAT_COOL if has_heat else None

    def _ts_mode(self) -> HVACMode | None:
        raw = self.state_value("heating_cooling_target")
        return _TS_MODES.get(raw) if isinstance(raw, int) else None

    def _target_mode(self) -> HVACMode | None:
        """The mode whose setpoint(s) the entity shows."""
        if self._is_thermostat:
            return self._ts_mode()
        return self._hc_underlying_mode()

    # --- modes ------------------------------------------------------------

    @property
    def hvac_modes(self) -> list[HVACMode]:
        modes: set[HVACMode] = set()
        if self._is_thermostat:
            options = self.valid_options("heating_cooling_target")
            if options is not None:
                modes = {_TS_MODES[v] for v in options if v in _TS_MODES}
            elif self.settable("heating_cooling_target"):
                modes = set(_TS_MODES.values())
            current = self._ts_mode()
            if current is not None:
                modes.add(current)
        else:
            modes.add(HVACMode.OFF)
            options = self.valid_options("hvac_mode")
            if options is not None:
                modes |= {_HC_MODES[v] for v in options if v in _HC_MODES}
            elif self.settable("hvac_mode", "target_heater_cooler_state"):
                modes |= {HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL}
            current = self._hc_underlying_mode()
            if current is not None:
                modes.add(current)
        return [m for m in _MODE_ORDER if m in modes] or [HVACMode.OFF]

    @property
    def hvac_mode(self) -> HVACMode | None:
        if self.device is None:
            return None
        if self._is_thermostat:
            return self._ts_mode()
        if self.state_value("active") is False:
            return HVACMode.OFF
        return self._hc_underlying_mode() or HVACMode.HEAT_COOL

    @property
    def hvac_action(self) -> HVACAction | None:
        if self.device is None:
            return None
        if self._is_thermostat:
            raw = self.state_value("heating_cooling_current")
            if not isinstance(raw, int):
                return None
            if raw in _TS_ACTIONS:
                return _TS_ACTIONS[raw]
            return HVACAction.OFF if self._ts_mode() == HVACMode.OFF else HVACAction.IDLE
        if self.state_value("active") is False:
            return HVACAction.OFF
        word = self.state_value("hvac_state")
        if word is None:
            raw = self.state_value("current_heater_cooler_state")
            word = _HC_ACTION_INT.get(raw) if isinstance(raw, int) else None
        return _HC_ACTIONS.get(str(word)) if word is not None else None

    # --- temperatures -----------------------------------------------------

    @property
    def current_temperature(self) -> float | None:
        return self.state_value("current_temp")

    @property
    def current_humidity(self) -> float | None:
        return self.state_value("relative_humidity")

    def _single_target_key(self) -> str | None:
        """The one setpoint the entity shows, or None when it shows a range."""
        mode = self._target_mode()
        if self._is_thermostat:
            if mode == HVACMode.HEAT_COOL and self._has_range():
                return None
            return "target_temp"
        if mode == HVACMode.HEAT:
            return "heat_target"
        if mode == HVACMode.COOL:
            return "cool_target"
        if self._has_range():
            return None
        return "heat_target" if self.state_value("heat_target") is not None else "cool_target"

    def _has_range(self) -> bool:
        return (
            self.state_value("heat_target") is not None
            and self.state_value("cool_target") is not None
        )

    @property
    def target_temperature(self) -> float | None:
        key = self._single_target_key()
        return self.state_value(key) if key else None

    @property
    def target_temperature_high(self) -> float | None:
        if self._single_target_key() is not None:
            return None
        return self.state_value("cool_target")

    @property
    def target_temperature_low(self) -> float | None:
        if self._single_target_key() is not None:
            return None
        return self.state_value("heat_target")

    # --- features ---------------------------------------------------------

    @property
    def supported_features(self) -> ClimateEntityFeature:
        features = ClimateEntityFeature(0)
        if self.device is None:
            return features
        key = self._single_target_key()
        if key is not None:
            if self.settable(key):
                features |= ClimateEntityFeature.TARGET_TEMPERATURE
        elif self.settable("heat_target") or self.settable("cool_target"):
            features |= ClimateEntityFeature.TARGET_TEMPERATURE_RANGE
        modes = self.hvac_modes
        if HVACMode.OFF in modes and len(modes) > 1:
            if self._is_thermostat or self.settable("active"):
                features |= ClimateEntityFeature.TURN_ON | ClimateEntityFeature.TURN_OFF
        if self.settable("swing_mode"):
            features |= ClimateEntityFeature.SWING_MODE
        return features

    @property
    def swing_mode(self) -> str | None:
        raw = self.state_value("swing_mode")
        if raw is None:
            return None
        return SWING_ON if raw else SWING_OFF

    # --- writes -----------------------------------------------------------

    def _mode_payload(self, hvac_mode: HVACMode) -> dict[str, Any]:
        if self._is_thermostat:
            return {"heating_cooling_target": _TS_MODE_INT[hvac_mode]}
        if hvac_mode == HVACMode.OFF:
            return {"active": False}
        payload: dict[str, Any] = {"active": True}
        word = _HC_MODE_WORD.get(hvac_mode)
        if word and self.settable("hvac_mode", "target_heater_cooler_state"):
            payload["hvac_mode"] = word
        return payload

    async def async_set_hvac_mode(self, hvac_mode: HVACMode) -> None:
        await self._async_set_state(self._mode_payload(hvac_mode))

    async def async_turn_on(self) -> None:
        if not self._is_thermostat:
            await self._async_set_state({"active": True})
            return
        for mode in (HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL):
            if mode in self.hvac_modes:
                await self.async_set_hvac_mode(mode)
                return

    async def async_turn_off(self) -> None:
        await self.async_set_hvac_mode(HVACMode.OFF)

    async def async_set_temperature(self, **kwargs: Any) -> None:
        payload: dict[str, Any] = {}
        if (mode := kwargs.get(ATTR_HVAC_MODE)) is not None:
            payload.update(self._mode_payload(mode))
        if ATTR_TEMPERATURE in kwargs:
            key = self._single_target_key()
            if self._is_thermostat:
                key = "target_temp"
            elif mode in (HVACMode.HEAT, HVACMode.COOL):
                key = "heat_target" if mode == HVACMode.HEAT else "cool_target"
            if key is not None:
                payload[key] = kwargs[ATTR_TEMPERATURE]
        if ATTR_TARGET_TEMP_LOW in kwargs:
            payload["heat_target"] = kwargs[ATTR_TARGET_TEMP_LOW]
        if ATTR_TARGET_TEMP_HIGH in kwargs:
            payload["cool_target"] = kwargs[ATTR_TARGET_TEMP_HIGH]
        if payload:
            await self._async_set_state(payload)

    async def async_set_swing_mode(self, swing_mode: str) -> None:
        await self._async_set_state({"swing_mode": 1 if swing_mode == SWING_ON else 0})
