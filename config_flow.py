"""Config flow for Homecast integration."""

import logging
from typing import Any

import aiohttp
import voluptuous as vol

from homeassistant.config_entries import ConfigFlowResult
from homeassistant.core import HomeAssistant
from homeassistant.helpers import config_entry_oauth2_flow
from homeassistant.helpers.aiohttp_client import async_get_clientsession

from .api import HomecastApiClient, HomecastApiError
from .const import DOMAIN, OAUTH_REGISTER_URL, SCOPES

_LOGGER = logging.getLogger(__name__)


class HomecastOAuth2FlowHandler(
    config_entry_oauth2_flow.AbstractOAuth2FlowHandler,
    domain=DOMAIN,
):
    """Handle a config flow for Homecast."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to include in the authorize URL."""
        return {"scope": SCOPES}

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication when token expires."""
        return await self.async_step_reauth_confirm()

    async def async_step_reauth_confirm(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Confirm re-authentication."""
        if user_input is None:
            return self.async_show_form(step_id="reauth_confirm")
        return await self.async_step_user()

    async def async_oauth_create_entry(
        self, data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Create an entry after the OAuth flow completes."""
        # Verify connectivity by fetching state
        try:
            token = data["token"]["access_token"]
            session = async_get_clientsession(self.hass)
            client = HomecastApiClient(session, token)
            state = await client.get_state()
        except HomecastApiError as err:
            _LOGGER.error("Failed to connect to Homecast: %s", err)
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error connecting to Homecast")
            return self.async_abort(reason="unknown")

        # Count homes discovered (keys that aren't _meta or scenes)
        home_count = sum(
            1
            for key in state
            if key not in ("_meta", "scenes") and isinstance(state[key], dict)
        )
        _LOGGER.info("Homecast connected: found %d home(s)", home_count)

        # Use a unique ID based on the token subject (if available) or just domain
        await self.async_set_unique_id(DOMAIN)
        self._abort_if_unique_id_configured()

        return self.async_create_entry(title="Homecast", data=data)
