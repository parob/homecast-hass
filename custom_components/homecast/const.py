"""Constants for the Homecast integration."""

DOMAIN = "homecast"

API_BASE_URL = "https://api.homecast.cloud"
OAUTH_AUTHORIZE_URL = f"{API_BASE_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{API_BASE_URL}/oauth/token"

SCOPES = "read write"

UPDATE_INTERVAL = 30
UPDATE_INTERVAL_WS = 300  # Safety-net polling when WebSocket is connected

# Community mode
CONF_MODE = "mode"
MODE_CLOUD = "cloud"
MODE_COMMUNITY = "community"
CONF_API_URL = "api_url"
CONF_OAUTH_AUTHORIZE_URL = "oauth_authorize_url"
CONF_OAUTH_TOKEN_URL = "oauth_token_url"
