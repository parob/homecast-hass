"""What each HomeKit accessory becomes in Home Assistant, and what it can do.

Run against two payloads: the shape GET /rest/state returns with the
vocabulary fix (state_current.json), and a real production answer recorded
before it (state_production_2026_10_05.json), which an older Community relay
keeps returning until its Mac app is updated.
"""

from __future__ import annotations

from typing import Any

import pytest

from homeassistant.components.climate import (
    ATTR_CURRENT_HUMIDITY,
    ATTR_HVAC_ACTION,
    ATTR_HVAC_MODES,
    ATTR_SWING_MODE,
    ATTR_TARGET_TEMP_HIGH,
    ATTR_TARGET_TEMP_LOW,
    ClimateEntityFeature,
    HVACAction,
    HVACMode,
)
from homeassistant.components.cover import ATTR_CURRENT_POSITION, CoverEntityFeature
from homeassistant.components.fan import ATTR_PERCENTAGE, FanEntityFeature
from homeassistant.const import ATTR_SUPPORTED_FEATURES, ATTR_TEMPERATURE
from homeassistant.core import HomeAssistant
from homeassistant.helpers import entity_registry as er

HOME = "my_home_bcab"
AC = f"{HOME}.kitchen_9c55.kitchen_air_conditioner_6428"
UNDERFLOOR = f"{HOME}.kitchen_9c55.kitchen_underfloor_heating_e05e"
ANNEX_AC = f"{HOME}.annex_4e44.annex_air_conditioner_f9a9"
THERMOSTAT = f"{HOME}.hallway_7a10.hallway_thermostat_c0de"
BLIND = f"{HOME}.living_room_4b2d.eve_motionblinds_0b7e"
FAN = f"{HOME}.living_room_4b2d.ceiling_fan_f00d"
CONTACT = f"{HOME}.living_room_4b2d.front_door_sensor_91ae"
HUE_MOTION = f"{HOME}.garden_6055.hue_outdoor_motion_sensor_6d19"
OCCUPANCY = f"{HOME}.bathroom_1_3110.bathroom_1_motion_sensor_893f"
LOCK = f"{HOME}.front_door_19b2.aqara_smart_lock_u200_21de"


def eid(hass: HomeAssistant, domain: str, unique_id: str) -> str:
    entity_id = er.async_get(hass).async_get_entity_id(domain, "homecast", unique_id)
    assert entity_id, f"no {domain} entity for {unique_id}"
    return entity_id


def sent(client) -> dict[str, Any]:
    """The props of the last POST /rest/state, for its one accessory."""
    body = client.set_state.await_args.args[0]
    [rooms] = body.values()
    [accessories] = rooms.values()
    [props] = accessories.values()
    return props


async def call(hass, domain, service, entity_id, **data):
    await hass.services.async_call(
        domain, service, {"entity_id": entity_id, **data}, blocking=True
    )


# --- current payload -----------------------------------------------------------


async def test_blind_is_a_controllable_cover(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "cover", BLIND)
    state = hass.states.get(entity_id)
    assert state.state == "open"
    assert state.attributes[ATTR_CURRENT_POSITION] == 40
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & CoverEntityFeature.SET_POSITION

    await call(hass, "cover", "set_cover_position", entity_id, position=25)
    assert sent(client) == {"target": 25}
    await call(hass, "cover", "close_cover", entity_id)
    assert sent(client) == {"target": 0}


async def test_air_conditioner_modes_setpoint_and_swing(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "climate", AC)
    state = hass.states.get(entity_id)
    assert state.state == HVACMode.COOL
    assert state.attributes[ATTR_HVAC_MODES] == [
        HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL,
    ]
    # In cool mode the setpoint is the cooling threshold
    assert state.attributes[ATTR_TEMPERATURE] == 26
    features = state.attributes[ATTR_SUPPORTED_FEATURES]
    assert features & ClimateEntityFeature.TARGET_TEMPERATURE
    assert features & ClimateEntityFeature.TURN_OFF

    await call(hass, "climate", "set_temperature", entity_id, temperature=23)
    assert sent(client) == {"cool_target": 23}
    await call(hass, "climate", "set_hvac_mode", entity_id, hvac_mode=HVACMode.HEAT)
    assert sent(client) == {"active": True, "hvac_mode": "heat"}
    await call(hass, "climate", "set_hvac_mode", entity_id, hvac_mode=HVACMode.OFF)
    assert sent(client) == {"active": False}


async def test_air_conditioner_in_auto_shows_a_range(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "climate", ANNEX_AC)
    state = hass.states.get(entity_id)
    assert state.state == HVACMode.HEAT_COOL
    assert state.attributes[ATTR_TARGET_TEMP_LOW] == 20
    assert state.attributes[ATTR_TARGET_TEMP_HIGH] == 24
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.IDLE
    assert state.attributes[ATTR_SWING_MODE] == "on"

    await call(hass, "climate", "set_temperature", entity_id, target_temp_low=19, target_temp_high=25)
    assert sent(client) == {"heat_target": 19, "cool_target": 25}
    await call(hass, "climate", "set_swing_mode", entity_id, swing_mode="off")
    assert sent(client) == {"swing_mode": 0}


async def test_heat_only_radiator_is_not_offered_cool(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "climate", UNDERFLOOR)
    state = hass.states.get(entity_id)
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.HEAT]
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING
    assert state.attributes[ATTR_TEMPERATURE] == 21.5
    assert state.attributes[ATTR_CURRENT_HUMIDITY] == 65.19

    await call(hass, "climate", "set_temperature", entity_id, temperature=22)
    assert sent(client) == {"heat_target": 22}


async def test_thermostat_setpoint_and_modes(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "climate", THERMOSTAT)
    state = hass.states.get(entity_id)
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_HVAC_MODES] == [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.HEAT]
    assert state.attributes[ATTR_TEMPERATURE] == 20
    assert state.attributes[ATTR_HVAC_ACTION] == HVACAction.HEATING

    await call(hass, "climate", "set_temperature", entity_id, temperature=21.5)
    assert sent(client) == {"target_temp": 21.5}
    await call(hass, "climate", "set_hvac_mode", entity_id, hvac_mode=HVACMode.OFF)
    assert sent(client) == {"heating_cooling_target": 0}
    await call(hass, "climate", "turn_on", entity_id)
    assert sent(client) == {"heating_cooling_target": 3}


async def test_fan_v2_speed_and_power(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "fan", FAN)
    state = hass.states.get(entity_id)
    assert state.state == "on"
    assert state.attributes[ATTR_PERCENTAGE] == 60
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & FanEntityFeature.SET_SPEED

    await call(hass, "fan", "set_percentage", entity_id, percentage=30)
    assert sent(client) == {"speed": 30}
    await call(hass, "fan", "turn_off", entity_id)
    assert sent(client) == {"active": False}


async def test_battery_entities(hass, setup_homecast) -> None:
    await setup_homecast("state_current.json")
    assert hass.states.get(eid(hass, "sensor", f"{BLIND}_battery")).state == "87"
    assert hass.states.get(eid(hass, "sensor", f"{HUE_MOTION}_battery")).state == "9"
    assert hass.states.get(eid(hass, "binary_sensor", f"{HUE_MOTION}_low_battery")).state == "on"
    assert hass.states.get(eid(hass, "binary_sensor", f"{LOCK}_low_battery")).state == "off"


async def test_multi_sensor_accessory_keeps_every_reading(hass, setup_homecast) -> None:
    await setup_homecast("state_current.json")
    assert hass.states.get(eid(hass, "binary_sensor", HUE_MOTION)).state == "off"
    assert hass.states.get(eid(hass, "sensor", f"{HUE_MOTION}_temperature")).state == "15.8"
    assert hass.states.get(eid(hass, "sensor", f"{HUE_MOTION}_illuminance")).state == "984"
    # An occupancy sensor is typed "temperature"; its occupancy is still there
    assert hass.states.get(eid(hass, "sensor", OCCUPANCY)).state == "24.8"
    assert hass.states.get(eid(hass, "binary_sensor", f"{OCCUPANCY}_occupancy_detected")).state == "on"


async def test_lock_and_contact(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    entity_id = eid(hass, "lock", LOCK)
    assert hass.states.get(entity_id).state == "locked"
    await call(hass, "lock", "unlock", entity_id)
    assert sent(client) == {"lock_target": False}
    assert hass.states.get(eid(hass, "binary_sensor", CONTACT)).state == "off"


# --- pushed updates ----------------------------------------------------------


async def test_pushed_mode_change_reads_like_a_polled_one(hass, setup_homecast) -> None:
    client = await setup_homecast("state_current.json")
    coordinator = client.entry.runtime_data.coordinator
    coordinator._on_ws_message({
        "type": "characteristic_update",
        "homeId": "A1B2C3D4-0000-5000-8000-00000000BCAB",
        "accessoryId": "00000000-0000-0000-0000-000000006428",
        "characteristicType": "target_heater_cooler_state",
        "value": 1,
    })
    await hass.async_block_till_done()
    state = hass.states.get(eid(hass, "climate", AC))
    assert state.state == HVACMode.HEAT
    assert state.attributes[ATTR_TEMPERATURE] == 26  # heat_target

    coordinator._on_ws_message({
        "type": "characteristic_update",
        "homeId": "A1B2C3D4-0000-5000-8000-00000000BCAB",
        "accessoryId": "00000000-0000-0000-0000-000000000b7e",
        "characteristicType": "current_position",
        "value": 70,
    })
    await hass.async_block_till_done()
    assert hass.states.get(eid(hass, "cover", BLIND)).attributes[ATTR_CURRENT_POSITION] == 70


# --- the production payload recorded before the fix ---------------------------


async def test_unfixed_server_blind_still_moves(hass, setup_homecast) -> None:
    client = await setup_homecast("state_production_2026_10_05.json")
    entity_id = eid(hass, "cover", BLIND)
    state = hass.states.get(entity_id)
    assert state.state == "closed"
    assert state.attributes[ATTR_CURRENT_POSITION] == 0
    assert state.attributes[ATTR_SUPPORTED_FEATURES] & CoverEntityFeature.SET_POSITION
    await call(hass, "cover", "open_cover", entity_id)
    assert sent(client) == {"target": 100}


@pytest.mark.parametrize(
    ("unique_id", "mode", "modes"),
    [
        (AC, HVACMode.OFF, [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL]),
        (UNDERFLOOR, HVACMode.OFF, [HVACMode.OFF, HVACMode.HEAT_COOL, HVACMode.HEAT, HVACMode.COOL]),
    ],
)
async def test_unfixed_server_heater_cooler_modes(hass, setup_homecast, unique_id, mode, modes) -> None:
    await setup_homecast("state_production_2026_10_05.json")
    state = hass.states.get(eid(hass, "climate", unique_id))
    assert state.state == mode
    assert state.attributes[ATTR_HVAC_MODES] == modes


async def test_unfixed_server_off_heater_shows_its_heat_setpoint(hass, setup_homecast) -> None:
    client = await setup_homecast("state_production_2026_10_05.json")
    entity_id = eid(hass, "climate", UNDERFLOOR)
    # Off, but in heat mode underneath: the setpoint shown is the heating one
    assert hass.states.get(entity_id).attributes[ATTR_TEMPERATURE] == 7.5
    await call(hass, "climate", "set_hvac_mode", entity_id, hvac_mode=HVACMode.HEAT)
    assert sent(client) == {"active": True, "hvac_mode": "heat"}


async def test_unfixed_server_light_sensor_reads_lux(hass, setup_homecast) -> None:
    await setup_homecast("state_production_2026_10_05.json")
    assert hass.states.get(eid(hass, "sensor", f"{HUE_MOTION}_illuminance")).state == "984"
