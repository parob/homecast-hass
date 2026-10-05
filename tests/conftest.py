"""Fixtures: a Homecast config entry set up against a recorded GET /rest/state."""

from __future__ import annotations

from collections.abc import Callable, Coroutine
import json
from pathlib import Path
import time
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from pyhomecast import HomecastState
from pytest_homeassistant_custom_component.common import MockConfigEntry

from homeassistant.core import HomeAssistant

from custom_components.homecast.const import CONF_MODE, DOMAIN, MODE_CLOUD

FIXTURES = Path(__file__).parent / "fixtures"


@pytest.fixture(autouse=True)
def auto_enable_custom_integrations(enable_custom_integrations):
    """Load custom_components/ in every test."""
    yield


def load_payload(name: str) -> dict[str, Any]:
    return json.loads((FIXTURES / name).read_text())


@pytest.fixture
def setup_homecast(
    hass: HomeAssistant,
) -> Callable[[str], Coroutine[Any, Any, MagicMock]]:
    """Set the integration up against a fixture; returns the mocked client.

    Only the transport is faked: pyhomecast's own parser turns the recorded
    payload into devices, and every platform builds its entities from them as
    it would against the real API.
    """

    async def _setup(fixture: str) -> MagicMock:
        payload = load_payload(fixture)
        entry = MockConfigEntry(
            domain=DOMAIN,
            data={
                "auth_implementation": DOMAIN,
                CONF_MODE: MODE_CLOUD,
                "token": {
                    "access_token": "test-token",
                    "refresh_token": "test-refresh",
                    "expires_at": time.time() + 3600,
                    "token_type": "Bearer",
                },
            },
            unique_id="A1B2C3D4-0000-5000-8000-00000000BCAB",
        )
        entry.add_to_hass(hass)

        client = MagicMock()
        # A fresh parse per poll, as the real client does
        client.get_state = AsyncMock(
            side_effect=lambda: HomecastState.from_api_response(json.loads(json.dumps(payload)))
        )
        client.set_state = AsyncMock(return_value={"updated": 1, "failed": 0})

        session = MagicMock()
        session.async_ensure_token_valid = AsyncMock()
        session.token = entry.data["token"]

        ws = MagicMock()
        ws.connect = AsyncMock()
        ws.subscribe = AsyncMock()
        ws.disconnect = AsyncMock()
        ws.connected = True

        with (
            patch(
                "custom_components.homecast.async_get_config_entry_implementation",
                AsyncMock(return_value=MagicMock()),
            ),
            patch("custom_components.homecast.OAuth2Session", return_value=session),
            patch("custom_components.homecast.HomecastClient", return_value=client),
            patch("custom_components.homecast.HomecastWebSocket", return_value=ws),
        ):
            assert await hass.config_entries.async_setup(entry.entry_id)
            await hass.async_block_till_done()
        client.entry = entry
        return client

    return _setup
