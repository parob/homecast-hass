"""Homecast REST API client."""

import logging
from typing import Any

import aiohttp

from .const import API_BASE_URL

_LOGGER = logging.getLogger(__name__)


class HomecastApiError(Exception):
    """Raised when the Homecast API returns an error."""

    def __init__(self, message: str, status: int | None = None) -> None:
        super().__init__(message)
        self.status = status


class HomecastApiClient:
    """Async client for the Homecast REST API."""

    def __init__(self, session: aiohttp.ClientSession, token: str) -> None:
        self._session = session
        self._token = token

    def set_token(self, token: str) -> None:
        """Update the access token (after refresh)."""
        self._token = token

    @property
    def _headers(self) -> dict[str, str]:
        return {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }

    async def get_state(
        self,
        home: str | None = None,
        room: str | None = None,
        device_type: str | None = None,
        name: str | None = None,
    ) -> dict[str, Any]:
        """Fetch current state of all homes/accessories.

        GET /rest/state
        """
        params: dict[str, str] = {}
        if home:
            params["home"] = home
        if room:
            params["room"] = room
        if device_type:
            params["type"] = device_type
        if name:
            params["name"] = name

        async with self._session.get(
            f"{API_BASE_URL}/rest/state",
            headers=self._headers,
            params=params,
        ) as resp:
            if resp.status == 401:
                raise HomecastApiError("Authentication failed", status=401)
            if resp.status != 200:
                text = await resp.text()
                raise HomecastApiError(
                    f"API error {resp.status}: {text}", status=resp.status
                )
            return await resp.json()

    async def set_state(self, updates: dict[str, Any]) -> dict[str, Any]:
        """Set state of one or more accessories.

        POST /rest/state
        Body: {home_key: {room_key: {accessory_key: {prop: value}}}}
        """
        async with self._session.post(
            f"{API_BASE_URL}/rest/state",
            headers=self._headers,
            json=updates,
        ) as resp:
            if resp.status == 401:
                raise HomecastApiError("Authentication failed", status=401)
            if resp.status != 200:
                text = await resp.text()
                raise HomecastApiError(
                    f"API error {resp.status}: {text}", status=resp.status
                )
            return await resp.json()

    async def run_scene(self, home: str, name: str) -> dict[str, Any]:
        """Execute a scene by name.

        POST /rest/scene
        Body: {"home": home_key, "name": scene_name}
        """
        async with self._session.post(
            f"{API_BASE_URL}/rest/scene",
            headers=self._headers,
            json={"home": home, "name": name},
        ) as resp:
            if resp.status == 401:
                raise HomecastApiError("Authentication failed", status=401)
            if resp.status != 200:
                text = await resp.text()
                raise HomecastApiError(
                    f"API error {resp.status}: {text}", status=resp.status
                )
            return await resp.json()

    async def register_client(
        self,
        redirect_uri: str,
        client_name: str = "Home Assistant",
    ) -> dict[str, Any]:
        """Dynamically register an OAuth client (RFC 7591).

        POST /oauth/register
        Returns: {"client_id": ..., "client_secret": ..., ...}
        """
        async with self._session.post(
            f"{API_BASE_URL}/oauth/register",
            json={
                "redirect_uris": [redirect_uri],
                "client_name": client_name,
                "grant_types": ["authorization_code", "refresh_token"],
                "response_types": ["code"],
                "scope": "mcp:read mcp:write",
                "token_endpoint_auth_method": "client_secret_post",
            },
        ) as resp:
            if resp.status != 201:
                text = await resp.text()
                raise HomecastApiError(
                    f"Client registration failed ({resp.status}): {text}",
                    status=resp.status,
                )
            return await resp.json()
