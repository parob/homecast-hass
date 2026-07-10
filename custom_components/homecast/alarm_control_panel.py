"""Alarm control panel platform for Homecast."""

from __future__ import annotations

from typing import Any

from homeassistant.components.alarm_control_panel import (
    AlarmControlPanelEntity,
    AlarmControlPanelEntityFeature,
    AlarmControlPanelState,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from . import HomecastConfigEntry
from .entity import HomecastEntity

# Homecast alarm_state -> HA state
_ALARM_STATE_MAP: dict[str, AlarmControlPanelState] = {
    "home": AlarmControlPanelState.ARMED_HOME,
    "away": AlarmControlPanelState.ARMED_AWAY,
    "night": AlarmControlPanelState.ARMED_NIGHT,
    "off": AlarmControlPanelState.DISARMED,
    "triggered": AlarmControlPanelState.TRIGGERED,
}


async def async_setup_entry(
    hass: HomeAssistant,
    entry: HomecastConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast alarm control panels."""
    coordinator = entry.runtime_data.coordinator

    entities = []
    if coordinator.data:
        for device in coordinator.data.devices.values():
            if device.device_type == "alarm":
                entities.append(HomecastAlarm(coordinator, device))
    async_add_entities(entities)


class HomecastAlarm(HomecastEntity, AlarmControlPanelEntity):
    """Represents a Homecast security system."""

    _attr_name = None
    _attr_code_arm_required = False

    @property
    def supported_features(self) -> AlarmControlPanelEntityFeature:
        return (
            AlarmControlPanelEntityFeature.ARM_HOME
            | AlarmControlPanelEntityFeature.ARM_AWAY
            | AlarmControlPanelEntityFeature.ARM_NIGHT
        )

    @property
    def alarm_state(self) -> AlarmControlPanelState | None:
        device = self.device
        if device is None:
            return None
        state_str = device.state.get("alarm_state")
        if state_str:
            return _ALARM_STATE_MAP.get(str(state_str))
        return None

    async def async_alarm_disarm(self, code: str | None = None) -> None:
        await self._async_set_state({"alarm_target": "off"})

    async def async_alarm_arm_home(self, code: str | None = None) -> None:
        await self._async_set_state({"alarm_target": "home"})

    async def async_alarm_arm_away(self, code: str | None = None) -> None:
        await self._async_set_state({"alarm_target": "away"})

    async def async_alarm_arm_night(self, code: str | None = None) -> None:
        await self._async_set_state({"alarm_target": "night"})
