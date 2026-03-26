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

- A [Homecast](https://homecast.cloud) account
- The Homecast Mac or iOS app running on your home network as a relay
- Home Assistant 2024.1.0 or newer
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

1. Copy the `custom_components/homecast` directory to your Home Assistant `config/custom_components/` directory
2. Restart Home Assistant

## Setup

1. Go to **Settings** > **Devices & Services** > **Add Integration**
2. Search for **Homecast**
3. You'll be redirected to the Homecast OAuth consent screen
4. Log in to your Homecast account and authorize Home Assistant
5. Select which homes to share and the permission level (view or control)
6. Your HomeKit devices will appear in Home Assistant automatically, organized by room

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

The integration uses cloud polling to keep device state in sync. The default polling interval is **30 seconds**.

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

- State updates every 30 seconds via polling
- For immediate feedback after controlling a device, the integration triggers an extra refresh
- WebSocket push updates for real-time state are planned for a future release

### Re-authentication

If your OAuth token expires or is revoked, Home Assistant will prompt you to re-authenticate. Go to **Settings** > **Devices & Services** > **Homecast** and follow the re-auth flow.

## Development

This integration follows Home Assistant's [integration development guidelines](https://developers.home-assistant.io/docs/creating_component_index).

### Architecture

| File | Purpose |
|---|---|
| `__init__.py` | Integration setup, coordinator creation |
| `config_flow.py` | OAuth 2.1 config flow with PKCE |
| `coordinator.py` | DataUpdateCoordinator (polls REST API) |
| `api.py` | Async REST client for Homecast API |
| `models.py` | Data models and state parsing |
| `entity.py` | Base entity with shared device info and state commands |
| `light.py`, `switch.py`, etc. | Platform-specific entity implementations |

### API used

The integration communicates with Homecast via:

- **`GET /rest/state`** — Fetch all device state (polling)
- **`POST /rest/state`** — Send control commands
- **`POST /rest/scene`** — Execute scenes (future)
- **OAuth 2.1** — Authentication with PKCE and refresh tokens

## License

MIT
