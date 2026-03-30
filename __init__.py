"""The Homecast integration."""

from __future__ import annotations

from dataclasses import dataclass
import logging

from pyhomecast import HomecastClient, HomecastWebSocket

from homeassistant.config_entries import ConfigEntry
from homeassistant.const import CONF_ACCESS_TOKEN, Platform
from homeassistant.core import HomeAssistant
from homeassistant.exceptions import (
    ConfigEntryAuthFailed,
    ConfigEntryNotReady,
    OAuth2TokenRequestError,
    OAuth2TokenRequestReauthError,
)
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import (
    OAuth2Session,
    async_get_config_entry_implementation,
)

from .const import API_BASE_URL, DOMAIN as DOMAIN
from .coordinator import HomecastCoordinator

_LOGGER = logging.getLogger(__name__)

PLATFORMS = [
    Platform.ALARM_CONTROL_PANEL,
    Platform.BINARY_SENSOR,
    Platform.CLIMATE,
    Platform.COVER,
    Platform.FAN,
    Platform.LIGHT,
    Platform.LOCK,
    Platform.SENSOR,
    Platform.SWITCH,
]


@dataclass
class HomecastData:
    """Runtime data for a Homecast config entry."""

    coordinator: HomecastCoordinator
    client: HomecastClient


type HomecastConfigEntry = ConfigEntry[HomecastData]


async def async_setup_entry(hass: HomeAssistant, entry: HomecastConfigEntry) -> bool:
    """Set up Homecast from a config entry."""
    implementation = await async_get_config_entry_implementation(hass, entry)
    session = OAuth2Session(hass, entry, implementation)

    try:
        await session.async_ensure_token_valid()
    except OAuth2TokenRequestReauthError as err:
        raise ConfigEntryAuthFailed from err
    except OAuth2TokenRequestError as err:
        raise ConfigEntryNotReady from err

    http_session = async_get_clientsession(hass)
    client = HomecastClient(session=http_session, api_url=API_BASE_URL)
    client.authenticate(session.token[CONF_ACCESS_TOKEN])

    # Create WebSocket client for push updates
    device_id = f"ha_{entry.entry_id[:12]}"
    ws = HomecastWebSocket(
        session=http_session, api_url=API_BASE_URL, device_id=device_id
    )

    async def _refresh_token() -> None:
        await session.async_ensure_token_valid()
        token = session.token[CONF_ACCESS_TOKEN]
        client.authenticate(token)
        ws.set_token(token)

    coordinator = HomecastCoordinator(hass, entry, client, _refresh_token, ws=ws)

    try:
        await coordinator.async_config_entry_first_refresh()
    except ConfigEntryAuthFailed:
        raise
    except Exception as err:
        raise ConfigEntryNotReady(
            f"Could not fetch initial state from Homecast: {err}"
        ) from err

    # Start WebSocket after initial state is available
    await coordinator.async_setup_websocket()

    entry.runtime_data = HomecastData(
        coordinator=coordinator,
        client=client,
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def async_unload_entry(hass: HomeAssistant, entry: HomecastConfigEntry) -> bool:
    """Unload a Homecast config entry."""
    return await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
