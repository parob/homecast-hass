"""The Homecast integration."""

from __future__ import annotations

import logging

from homeassistant.config_entries import ConfigEntry
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.device_registry import DeviceInfo

from .api import HomecastApiClient
from .const import DOMAIN, PLATFORMS
from .coordinator import HomecastCoordinator

_LOGGER = logging.getLogger(__name__)

type HomecastConfigEntry = ConfigEntry


async def async_setup_entry(hass: HomeAssistant, entry: HomecastConfigEntry) -> bool:
    """Set up Homecast from a config entry."""
    implementation = await config_entry_oauth2_flow.async_get_config_entry_implementation(
        hass, entry
    )
    oauth_session = config_entry_oauth2_flow.OAuth2Session(hass, entry, implementation)

    # Ensure token is valid
    await oauth_session.async_ensure_token_valid()
    token = oauth_session.token["access_token"]

    session = async_get_clientsession(hass)
    api = HomecastApiClient(session, token)

    coordinator = HomecastCoordinator(hass, api)
    await coordinator.async_config_entry_first_refresh()

    # Register hub devices for each home
    device_registry = hass.helpers.device_registry.async_get(hass)
    if coordinator.data:
        for home_key, home_name in coordinator.data.homes.items():
            device_registry.async_get_or_create(
                config_entry_id=entry.entry_id,
                identifiers={(DOMAIN, home_key)},
                name=home_name,
                manufacturer="Homecast",
                model="HomeKit Bridge",
            )

    # Store coordinator and session for platforms and token refresh
    hass.data.setdefault(DOMAIN, {})[entry.entry_id] = {
        "coordinator": coordinator,
        "oauth_session": oauth_session,
        "api": api,
    }

    # Set up a listener to refresh the API token when it changes
    entry.async_on_unload(
        entry.add_update_listener(_async_update_listener)
    )

    await hass.config_entries.async_forward_entry_setups(entry, PLATFORMS)
    return True


async def _async_update_listener(
    hass: HomeAssistant, entry: HomecastConfigEntry
) -> None:
    """Handle config entry updates (token refresh)."""
    data = hass.data.get(DOMAIN, {}).get(entry.entry_id)
    if data:
        oauth_session: config_entry_oauth2_flow.OAuth2Session = data["oauth_session"]
        await oauth_session.async_ensure_token_valid()
        api: HomecastApiClient = data["api"]
        api.set_token(oauth_session.token["access_token"])


async def async_unload_entry(hass: HomeAssistant, entry: HomecastConfigEntry) -> bool:
    """Unload a Homecast config entry."""
    unload_ok = await hass.config_entries.async_unload_platforms(entry, PLATFORMS)
    if unload_ok:
        hass.data[DOMAIN].pop(entry.entry_id, None)
    return unload_ok
