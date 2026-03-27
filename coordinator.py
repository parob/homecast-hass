"""DataUpdateCoordinator for Homecast."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import logging
from datetime import timedelta
from typing import Any

from pyhomecast import HomecastAuthError, HomecastClient, HomecastConnectionError, HomecastState

from homeassistant.core import HomeAssistant
from homeassistant.exceptions import ConfigEntryAuthFailed
from homeassistant.helpers.update_coordinator import DataUpdateCoordinator, UpdateFailed

from .const import DOMAIN, UPDATE_INTERVAL

_LOGGER = logging.getLogger(__name__)


class HomecastCoordinator(DataUpdateCoordinator[HomecastState]):
    """Coordinator that polls the Homecast REST API for device state."""

    def __init__(
        self,
        hass: HomeAssistant,
        client: HomecastClient,
        refresh_token: Callable[[], Coroutine[Any, Any, None]],
    ) -> None:
        """Initialize the coordinator."""
        super().__init__(
            hass,
            _LOGGER,
            name=DOMAIN,
            update_interval=timedelta(seconds=UPDATE_INTERVAL),
        )
        self.client = client
        self._refresh_token = refresh_token

    async def _async_update_data(self) -> HomecastState:
        """Fetch state from the Homecast API."""
        try:
            await self._refresh_token()
            return await self.client.get_state()
        except HomecastAuthError as err:
            raise ConfigEntryAuthFailed from err
        except HomecastConnectionError as err:
            raise UpdateFailed(f"Error communicating with Homecast: {err}") from err

    async def async_set_state(self, updates: dict[str, Any]) -> None:
        """Send a state update and request a refresh."""
        await self._refresh_token()
        await self.client.set_state(updates)
        await self.async_request_refresh()
