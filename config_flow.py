"""Config flow for Homecast."""

from __future__ import annotations

from collections.abc import Mapping
import logging
from typing import Any

from pyhomecast import HomecastAuthError, HomecastClient, HomecastConnectionError
import voluptuous as vol

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
    async_import_client_credential,
)
from homeassistant.config_entries import SOURCE_REAUTH, ConfigFlowResult
from homeassistant.const import CONF_ACCESS_TOKEN, CONF_TOKEN
from homeassistant.helpers.aiohttp_client import async_get_clientsession
from homeassistant.helpers.config_entry_oauth2_flow import AbstractOAuth2FlowHandler

from .application_credentials import authorization_server_context
from .const import (
    API_BASE_URL,
    CONF_API_URL,
    CONF_MODE,
    CONF_OAUTH_AUTHORIZE_URL,
    CONF_OAUTH_TOKEN_URL,
    DOMAIN,
    MODE_CLOUD,
    MODE_COMMUNITY,
    OAUTH_AUTHORIZE_URL,
    OAUTH_CLIENT_ID,
    OAUTH_CLIENT_SECRET,
    OAUTH_TOKEN_URL,
    SCOPES,
)

_LOGGER = logging.getLogger(__name__)

_REDIRECT_URI = "https://my.home-assistant.io/redirect/oauth"


class HomecastFlowHandler(AbstractOAuth2FlowHandler, domain=DOMAIN):
    """Handle a config flow for Homecast."""

    DOMAIN = DOMAIN

    def __init__(self) -> None:
        """Initialize the flow handler."""
        super().__init__()
        self._community_data: dict[str, Any] | None = None

    @property
    def logger(self) -> logging.Logger:
        """Return logger."""
        return _LOGGER

    @property
    def extra_authorize_data(self) -> dict[str, Any]:
        """Extra data to include in the authorize URL."""
        return {"scope": SCOPES}

    async def async_step_user(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Handle a flow start — choose cloud or community."""
        return self.async_show_menu(
            step_id="user",
            menu_options=["cloud", "community"],
        )

    async def async_step_cloud(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Cloud mode — OAuth flow with pre-registered credentials."""
        await async_import_client_credential(
            self.hass,
            DOMAIN,
            ClientCredential(OAUTH_CLIENT_ID, OAUTH_CLIENT_SECRET),
        )
        return await super().async_step_user(user_input)

    async def async_step_community(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Community mode — enter server URL, then OAuth."""
        errors: dict[str, str] = {}

        if user_input is not None:
            api_url = user_input[CONF_API_URL].rstrip("/")

            # Dynamically register an OAuth client with the community server
            client = HomecastClient(
                session=async_get_clientsession(self.hass), api_url=api_url
            )
            try:
                result = await client.register_client(redirect_uri=_REDIRECT_URI)
            except (HomecastConnectionError, HomecastAuthError) as err:
                _LOGGER.error("Failed to register with community server: %s", err)
                errors["base"] = "cannot_connect"
            except Exception:
                _LOGGER.exception("Unexpected error registering with community server")
                errors["base"] = "unknown"
            else:
                # Import the dynamically obtained credentials
                await async_import_client_credential(
                    self.hass,
                    DOMAIN,
                    ClientCredential(
                        result["client_id"],
                        result.get("client_secret", ""),
                    ),
                )

                # Store community data for later steps
                self._community_data = {
                    CONF_MODE: MODE_COMMUNITY,
                    CONF_API_URL: api_url,
                    CONF_OAUTH_AUTHORIZE_URL: f"{api_url}/oauth/authorize",
                    CONF_OAUTH_TOKEN_URL: f"{api_url}/oauth/token",
                }

                # Kick off the OAuth flow against the community server
                return await self.async_step_pick_implementation()

        return self.async_show_form(
            step_id="community",
            data_schema=vol.Schema(
                {
                    vol.Required(
                        CONF_API_URL, default="http://localhost:5656"
                    ): str,
                }
            ),
            errors=errors,
        )

    async def async_step_pick_implementation(
        self, user_input: dict[str, Any] | None = None
    ) -> ConfigFlowResult:
        """Override to set authorization server context for community mode."""
        if self._community_data:
            with authorization_server_context(
                AuthorizationServer(
                    authorize_url=self._community_data[CONF_OAUTH_AUTHORIZE_URL],
                    token_url=self._community_data[CONF_OAUTH_TOKEN_URL],
                )
            ):
                return await super().async_step_pick_implementation(user_input)
        return await super().async_step_pick_implementation(user_input)

    async def async_step_reauth(
        self, entry_data: Mapping[str, Any]
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

    async def async_oauth_create_entry(self, data: dict[str, Any]) -> ConfigFlowResult:
        """Create an entry after OAuth flow completes."""
        # Determine mode and API URL
        if self._community_data:
            api_url = self._community_data[CONF_API_URL]
            mode = MODE_COMMUNITY
        else:
            api_url = API_BASE_URL
            mode = MODE_CLOUD

        token = data[CONF_TOKEN][CONF_ACCESS_TOKEN]
        client = HomecastClient(
            session=async_get_clientsession(self.hass), api_url=api_url
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

        unique_id = f"{DOMAIN}_community" if mode == MODE_COMMUNITY else DOMAIN
        await self.async_set_unique_id(unique_id)

        if self.source == SOURCE_REAUTH:
            return self.async_update_reload_and_abort(
                self._get_reauth_entry(), data_updates=data
            )

        self._abort_if_unique_id_configured()

        # Merge community data (api_url, oauth URLs) into the entry
        data[CONF_MODE] = mode
        if self._community_data:
            data.update(self._community_data)

        title = "Homecast (Community)" if mode == MODE_COMMUNITY else "Homecast"
        return self.async_create_entry(title=title, data=data)
