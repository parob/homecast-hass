"""Scene platform for Homecast.

Scenes are discovered by fetching state per-home. Since the multi-home
REST endpoint doesn't include scenes, this platform creates scene entities
from cached data and uses POST /rest/scene for activation.
"""

from __future__ import annotations

import logging
from typing import Any

from homeassistant.components.scene import Scene
from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers.entity_platform import AddEntitiesCallback

from .const import DOMAIN
from .coordinator import HomecastCoordinator

_LOGGER = logging.getLogger(__name__)


async def async_setup_entry(
    hass: HomeAssistant,
    entry: ConfigEntry,
    async_add_entities: AddEntitiesCallback,
) -> None:
    """Set up Homecast scenes.

    Scenes are not included in the multi-home GET /rest/state response,
    so this platform starts empty. Scene support will be added in a future
    version that queries scenes per-home via the GraphQL API.
    """
    # Scene discovery requires per-home API calls not yet implemented.
    # Placeholder for future enhancement.
    async_add_entities([])
