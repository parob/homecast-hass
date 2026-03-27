"""Config flow for Homecast."""

from __future__ import annotations

import logging
from typing import Any

from pyhomecast import HomecastAuthError, HomecastClient, HomecastConnectionError

from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .const import API_BASE_URL, DOMAIN, SCOPES

_LOGGER = logging.getLogger(__name__)


class HomecastFlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for Homecast."""

    DOMAIN = DOMAIN

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to include in the authorize URL."""
        return {"scope": SCOPES}

    async def async_step_reauth(
        self, entry_data: dict[str, Any]
    ) -> ConfigFlowResult:
        """Handle re-authentication."""
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
        """Create an entry after OAuth flow completes."""
        token = data[CONF_TOKEN][CONF_ACCESS_TOKEN]
        client = HomecastClient(
            session=async_get_clientsession(self.hass), api_url=API_BASE_URL
        )
        client.authenticate(token)

        try:
            state = await client.get_state()
        except HomecastAuthError:
            return self.async_abort(reason="invalid_auth")
        except HomecastConnectionError:
            return self.async_abort(reason="cannot_connect")
        except Exception:
            _LOGGER.exception("Unexpected error during Homecast setup")
            return self.async_abort(reason="unknown")

        _LOGGER.info("Homecast connected: found %d home(s)", len(state.homes))

        await self.async_set_unique_id(DOMAIN)

        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data_updates=data
            )

        self._abort_if_unique_id_configured()
        return self.async_create_entry(title="Homecast", data=data)
