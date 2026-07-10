# Homecast for Home Assistant

A [Home Assistant](https://www.home-assistant.io/) custom integration that connects your Apple HomeKit smart home devices to Home Assistant through [Homecast](https://homecast.cloud).

## How it works

```
Home Assistant                     Homecast Cloud                    Your Home
┌──────────────────┐          ┌──────────────────┐          ┌─────────────────┐
│                   │  REST    │                   │   WS     │  Mac/iOS Relay  │
│  homecast         │◄────────►│  api.homecast.    │◄────────►│                 │
│  integration      │  OAuth   │  cloud            │          │  HomeKit        │
│                   │          │                   │          │  Devices        │
│  Lights, Switches │          └──────────────────┘          └─────────────────┘
│  Thermostats,     │
│  Locks, Fans ...  │
└──────────────────┘
```

Homecast acts as a bridge between Apple HomeKit and open standards. The Homecast Mac/iOS app runs on your home network with HomeKit access and relays device state to the Homecast cloud. This integration connects Home Assistant to that cloud API, giving you full control of your HomeKit devices from HA dashboards, automations, and voice assistants.

## Prerequisites

- The Homecast Mac or iOS app running on your home network as a relay
- **Cloud mode:** a [Homecast](https://homecast.cloud) account, or
- **Community mode:** the Homecast app's local server enabled (no account needed)
- Home Assistant 2026.4.0 or newer
- [HACS](https://hacs.xyz/) (Home Assistant Community Store)

## Installation

### Via HACS (recommended)

1. Open HACS in your Home Assistant instance
2. Go to **Integrations** > **Custom repositories**
3. Add this repository URL: `https://github.com/parob/homecast-hass`
4. Select **Integration** as the category
5. Click **Add**, then find **Homecast** in the integration list and click **Download**
6. Restart Home Assistant

### Manual

1. Copy this repository's `custom_components/homecast/` directory into your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Homecast**
3. Choose **Cloud** (homecast.cloud account) or **Community** (local Homecast server on your network)
4. **Cloud:** log in and authorize Home Assistant on the consent screen, selecting which homes to share and the permission level (view or control). **Community:** enter your Homecast server URL (e.g. `http://your-mac.local:5656`)
5. Your HomeKit devices will appear in Home Assistant automatically, organized by room

No manual OAuth client registration is needed — the integration registers itself automatically.

## Supported devices

| HomeKit Device | Home Assistant Platform | Controls |
|---|---|---|
| Lightbulb | Light | On/off, brightness, color (HS), color temperature |
| Switch | Switch | On/off |
| Outlet | Switch | On/off |
| Thermostat / Heater-Cooler | Climate | HVAC mode, target temperature, temperature range |
| Lock | Lock | Lock / unlock |
| Window Covering / Blind | Cover | Position (0-100%), open/close |
| Fan | Fan | On/off, speed percentage |
| Security System | Alarm Control Panel | Arm home/away/night, disarm |
| Motion Sensor | Binary Sensor | Motion detected |
| Contact Sensor | Binary Sensor | Open/closed |
| Temperature Sensor | Sensor | Current temperature (Celsius) |
| Light Sensor | Sensor | Illuminance (lux) |
| Battery (any device) | Sensor | Battery level (%) |
| Low Battery (any device) | Binary Sensor | Battery low warning |

## How devices appear

- Each HomeKit accessory becomes a **device** in the Home Assistant device registry
- Devices are automatically placed in **areas** matching their HomeKit room names
- Each Homecast home appears as a hub device
- Device names and types are derived from the HomeKit data

## Configuration

State updates arrive in real time over a WebSocket connection. A safety-net poll every **5 minutes** keeps state in sync if the WebSocket is interrupted.

### View-only access

If you authorized Home Assistant with view-only permissions during OAuth setup, you'll be able to see device state but control commands will be rejected by the server.

## Troubleshooting

### Devices not appearing

- Make sure the Homecast relay app (Mac or iOS) is running and connected
- Check the Homecast web app to verify your devices are visible there
- The relay must be online for the API to return device state

### "Cannot connect" during setup

- Verify your Homecast account is active and the relay is online
- Check that Home Assistant can reach `api.homecast.cloud` (no firewall blocking)

### Stale state

- State changes are pushed over WebSocket within a few seconds
- A full refresh runs every 5 minutes as a safety net
- If state seems stuck, check that the relay app is online

### Re-authentication

If your OAuth token expires or is revoked, Home Assistant will prompt you to re-authenticate. Go to **Settings** > **Devices & Services** > **Homecast** and follow the re-auth flow.

## Development

This integration follows Home Assistant's [integration development guidelines](https://developers.home-assistant.io/docs/creating_component_index).

### Architecture

| File | Purpose |
|---|---|
| `__init__.py` | Integration setup, coordinator creation |
| `config_flow.py` | OAuth 2.1 config flow with PKCE |
| `coordinator.py` | DataUpdateCoordinator (WebSocket push + safety-net polling) |
| `entity.py` | Base entity with shared device info and state commands |
| `light.py`, `switch.py`, etc. | Platform-specific entity implementations |

### API used

The integration communicates with Homecast via:

- **`GET /rest/state`** — Fetch all device state (initial load + safety-net polling)
- **`POST /rest/state`** — Send control commands
- **WebSocket** — Real-time state push (`characteristic_update`, `service_group_update`)
- **`POST /rest/scene`** — Execute scenes (future)
- **OAuth 2.1** — Authentication with PKCE and refresh tokens

## License

MIT
