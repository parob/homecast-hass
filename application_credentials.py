"""OAuth application credentials for Homecast."""

from __future__ import annotations

from homeassistant.components.application_credentials import (
    AuthorizationServer,
    ClientCredential,
)
from homeassistant.core import HomeAssistant
from homeassistant.helpers.config_entry_oauth2_flow import (
    LocalOAuth2ImplementationWithPkce,
)

from .const import OAUTH_AUTHORIZE_URL, OAUTH_TOKEN_URL, SCOPES


async def async_get_authorization_server(hass: HomeAssistant) -> AuthorizationServer:
    """Return the Homecast authorization server."""
    return AuthorizationServer(
        authorize_url=OAUTH_AUTHORIZE_URL,
        token_url=OAUTH_TOKEN_URL,
    )


async def async_get_auth_implementation(
    hass: HomeAssistant, auth_domain: str, credential: ClientCredential
) -> HomecastOAuth2Implementation:
    """Return a custom auth implementation with PKCE."""
    return HomecastOAuth2Implementation(
        hass,
        auth_domain,
        credential.client_id,
        OAUTH_AUTHORIZE_URL,
        OAUTH_TOKEN_URL,
        credential.client_secret,
    )


class HomecastOAuth2Implementation(LocalOAuth2ImplementationWithPkce):
    """Homecast OAuth2 implementation with PKCE (S256)."""

    @property
    def extra_authorize_data(self) -> dict:
        """Extra data that needs to be appended to the authorize url."""
        return super().extra_authorize_data | {
            "scope": SCOPES,
        }
