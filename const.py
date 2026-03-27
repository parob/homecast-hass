"""Constants for the Homecast integration."""

DOMAIN = "homecast"

API_BASE_URL = "https://api.homecast.cloud"
OAUTH_AUTHORIZE_URL = f"{API_BASE_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{API_BASE_URL}/oauth/token"

SCOPES = "mcp:read mcp:write"

UPDATE_INTERVAL = 30
