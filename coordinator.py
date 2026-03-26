"""DataUpdateCoordinator for Homecast."""

from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any

from homeassistant.core import HomeAssistant
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .api import HomecastApiClient, HomecastApiError
from .const import DOMAIN, UPDATE_INTERVAL
from .models import HomecastData, parse_state_response

_LOGGER = logging.getLogger(__name__)


class HomecastCoordinator(DataUpdateCoordinator[HomecastData]):
    """Coordinator that polls Homecast REST API for device state."""

    def __init__(self, hass: HomeAssistant, api: HomecastApiClient) -> None:
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.api = api

    async def _async_update_data(self) -> HomecastData:
        """Fetch state from Homecast API."""
        try:
            raw = await self.api.get_state()
        except HomecastApiError as err:
            raise UpdateFailed(f"Error communicating with Homecast: {err}") from err
        except Exception as err:
            raise UpdateFailed(f"Unexpected error: {err}") from err

        return parse_state_response(raw)

    async def async_set_state(self, updates: dict[str, Any]) -> None:
        """Send a state update and refresh."""
        try:
            await self.api.set_state(updates)
        except HomecastApiError as err:
            _LOGGER.error("Failed to set state: %s", err)
            raise
        # Refresh to get confirmed state
        await self.async_request_refresh()
