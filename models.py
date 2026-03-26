"""Data models for Homecast devices."""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any


def _key_to_name(key: str) -> str:
    """Convert a slug key like 'ceiling_light_a1b2' to 'Ceiling Light'.

    Strips the trailing 4-char UUID suffix and converts underscores to spaces.
    """
    # Remove the trailing _xxxx (4-char hex suffix)
    name = re.sub(r"_[0-9a-f]{4}$", "", key)
    return name.replace("_", " ").title()


@dataclass
class HomecastDevice:
    """Represents a single Homecast accessory or service group."""

    unique_id: str
    """Fully qualified ID: home_key.room_key.accessory_key"""

    name: str
    """Human-readable name derived from the accessory key."""

    room_name: str
    """Human-readable room name."""

    home_key: str
    """Home slug key, e.g. 'my_home_0bf8'."""

    home_name: str
    """Human-readable home name."""

    room_key: str
    """Room slug key, e.g. 'living_room_a1b2'."""

    accessory_key: str
    """Accessory slug key, e.g. 'ceiling_light_c3d4'."""

    device_type: str
    """Simplified type: light, switch, outlet, climate, lock, alarm, fan, blind, etc."""

    state: dict[str, Any] = field(default_factory=dict)
    """Current state values, e.g. {"on": True, "brightness": 80}."""

    settable: list[str] = field(default_factory=list)
    """Properties that can be written, e.g. ["on", "brightness"]."""

    is_group: bool = False
    """True if this is a service group (controls multiple accessories)."""


@dataclass
class HomecastData:
    """Parsed state from the Homecast REST API."""

    devices: dict[str, HomecastDevice]
    """All devices keyed by unique_id."""

    homes: dict[str, str]
    """home_key -> home_name mapping."""


def parse_state_response(raw: dict[str, Any]) -> HomecastData:
    """Parse the GET /rest/state response into HomecastData.

    The response structure is:
    {
        "home_key": {
            "room_key": {
                "accessory_key": {
                    "type": "light",
                    "on": true,
                    "brightness": 80,
                    "_settable": ["on", "brightness"],
                    "name": "home_key.room_key.accessory_key"
                }
            }
        },
        "_meta": {"fetched_at": "...", "message": "..."}
    }
    """
    devices: dict[str, HomecastDevice] = {}
    homes: dict[str, str] = {}

    for home_key, home_data in raw.items():
        if home_key.startswith("_") or not isinstance(home_data, dict):
            continue

        home_name = _key_to_name(home_key)
        homes[home_key] = home_name

        for room_key, room_data in home_data.items():
            if room_key.startswith("_") or not isinstance(room_data, dict):
                continue

            room_name = _key_to_name(room_key)

            for accessory_key, acc_data in room_data.items():
                if accessory_key.startswith("_") or not isinstance(acc_data, dict):
                    continue

                unique_id = f"{home_key}.{room_key}.{accessory_key}"
                device_type = acc_data.get("type", "other")
                settable = acc_data.get("_settable", [])
                is_group = acc_data.get("group", False)

                # Extract state (everything except metadata keys)
                state = {
                    k: v
                    for k, v in acc_data.items()
                    if k not in ("type", "_settable", "name", "group", "accessories")
                }

                device = HomecastDevice(
                    unique_id=unique_id,
                    name=_key_to_name(accessory_key),
                    room_name=room_name,
                    home_key=home_key,
                    home_name=home_name,
                    room_key=room_key,
                    accessory_key=accessory_key,
                    device_type=device_type,
                    state=state,
                    settable=settable,
                    is_group=is_group,
                )
                devices[unique_id] = device

    return HomecastData(devices=devices, homes=homes)
