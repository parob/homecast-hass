"""Constants for the Homecast integration."""

DOMAIN = "homecast"

API_BASE_URL = "https://api.homecast.cloud"
OAUTH_AUTHORIZE_URL = f"{API_BASE_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{API_BASE_URL}/oauth/token"

# Pre-registered OAuth client for Home Assistant
OAUTH_CLIENT_ID = "6091cff0-a357-40f2-b9bc-babc60c338e6"
OAUTH_CLIENT_SECRET = "0c7Rw4h5q-rUTAuYMUuCzuE3qV1ubLGht8SKgA9OAu0"

SCOPES = "mcp:read mcp:write"

UPDATE_INTERVAL = 30
UPDATE_INTERVAL_WS = 300  # Safety-net polling when WebSocket is connected
