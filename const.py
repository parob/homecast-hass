"""Constants for the Homecast integration."""

DOMAIN = "homecast"

API_BASE_URL = "https://api.homecast.cloud"
OAUTH_AUTHORIZE_URL = f"{API_BASE_URL}/oauth/authorize"
OAUTH_TOKEN_URL = f"{API_BASE_URL}/oauth/token"
OAUTH_REGISTER_URL = f"{API_BASE_URL}/oauth/register"

SCOPES = "mcp:read mcp:write"

# Polling interval in seconds
UPDATE_INTERVAL = 30

# Homecast device type -> HA platform(s)
DEVICE_TYPE_TO_PLATFORM: dict[str, str] = {
    "light": "light",
    "switch": "switch",
    "outlet": "switch",
    "climate": "climate",
    "lock": "lock",
    "alarm": "alarm_control_panel",
    "fan": "fan",
    "blind": "cover",
    "motion": "binary_sensor",
    "contact": "binary_sensor",
    "temperature": "sensor",
    "light_sensor": "sensor",
    "doorbell": "binary_sensor",
    "speaker": "sensor",
    "button": "sensor",
    "other": "sensor",
}

PLATFORMS: list[str] = [
    "light",
    "switch",
    "climate",
    "lock",
    "alarm_control_panel",
    "fan",
    "cover",
    "sensor",
    "binary_sensor",
    "scene",
]
