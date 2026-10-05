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

Homecast is not in the HACS default list yet, so add it as a custom repository first:

1. Open **HACS** in your Home Assistant sidebar
2. Click the **⋮** menu in the top right corner and choose **Custom repositories**
3. Enter `https://github.com/parob/homecast-hass` as the repository and choose **Integration** as the type, then click **Add**
4. Search HACS for **Homecast**, open it and click **Download**
5. Restart Home Assistant

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

| HomeKit service | Home Assistant entity | What you get |
|---|---|---|
| Lightbulb | Light | On/off, brightness, colour (hue/saturation), colour temperature |
| Switch | Switch | On/off |
| Outlet | Switch (outlet) | On/off |
| Heater-Cooler (air conditioners, most radiators and underfloor heating) | Climate | Off plus the modes the unit supports (heat/cool/auto, from HomeKit), the setpoint for the current mode or a heat–cool range in auto, current temperature and humidity, heating/cooling/idle action, swing on/off |
| Thermostat | Climate | The modes the thermostat supports (off/heat/cool/auto), target temperature, current temperature, heating/cooling action |
| Lock | Lock | Lock / unlock |
| Window Covering | Cover (blind) | Position 0–100 %, open/close, opening/closing |
| Fan and Fan v2 | Fan | On/off, speed percentage |
| Security System | Alarm control panel | Arm home/away/night (whichever the system supports), disarm |
| Motion Sensor | Binary sensor (motion) | Motion detected |
| Contact Sensor | Binary sensor (door) | Open/closed |
| Occupancy, Leak, Smoke, Carbon Monoxide sensors | Binary sensor | Detected / clear |
| Temperature Sensor | Sensor | Temperature (°C) |
| Light Sensor | Sensor | Illuminance (lx) |
| Humidity reading | Sensor | Relative humidity (%) |
| Battery (any accessory) | Sensor + binary sensor (diagnostic) | Battery level (%) and battery low |
| Service groups (e.g. a room's lights) | The group's type | Controls every member at once |

An accessory that combines several sensors keeps all of their readings: a Hue motion sensor becomes a motion sensor with temperature, illuminance and battery entities on the same device.

Not supported yet: garage door openers, air purifiers, humidifiers, valves and irrigation, speakers and TVs, cameras and doorbells, HomeKit scenes, and fan speed on an air conditioner.

## How devices appear

- Each HomeKit accessory (and each HomeKit service group) becomes a **device** in the Home Assistant device registry
- Devices are placed in the **area** matching their HomeKit room when they are first added. With more than one home, the area is named `Home - Room`
- Names are derived from the accessory's Homecast key, so capitalisation and punctuation are not preserved (`TV` becomes `Tv`). Rename them in Home Assistant if that matters
- Accessories added to HomeKit later appear after reloading the integration

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

- State changes are pushed over a WebSocket
- A full refresh runs every 5 minutes as a safety net, and whenever a relay goes offline or comes back
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

### Tests

```bash
uv venv --python 3.14 .venv
uv pip install --python .venv/bin/python -r requirements_test.txt
.venv/bin/python -m pytest
```

The tests set the integration up against recorded `GET /rest/state` answers in `tests/fixtures/` and check what every entity reports and what each service call sends.

## License

MIT
