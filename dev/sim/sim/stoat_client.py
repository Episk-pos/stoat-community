"""Async HTTP client for the Stoat (Delta) REST API."""

from __future__ import annotations

import httpx


class StoatClient:
    """Thin wrapper around the Stoat REST API."""

    def __init__(self, base_url: str = "http://delta:14702"):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.AsyncClient(base_url=self.base_url, timeout=30.0)

    async def close(self):
        await self._http.aclose()

    # -- helpers --

    async def _req(self, method: str, path: str, token: str | None = None, json: dict | None = None) -> dict | None:
        headers = {"Content-Type": "application/json"}
        if token:
            headers["x-session-token"] = token
        resp = await self._http.request(method, path, headers=headers, json=json)
        if resp.status_code == 409:
            return None  # already exists (idempotent)
        resp.raise_for_status()
        if not resp.content:
            return {}
        return resp.json()

    # -- auth --

    async def login(self, email: str, password: str) -> str:
        """Login and return session token."""
        resp = await self._req("POST", "/auth/session/login", json={
            "email": email,
            "password": password,
        })
        return resp["token"]

    async def check_onboarding(self, token: str) -> bool:
        """Return True if onboarding is needed."""
        resp = await self._req("GET", "/onboard/hello", token=token)
        return resp.get("onboarding", False) if resp else False

    async def complete_onboarding(self, token: str, username: str):
        await self._req("POST", "/onboard/complete", token=token, json={
            "username": username,
        })

    async def set_display_name(self, token: str, display_name: str):
        await self._req("PATCH", "/users/@me", token=token, json={
            "display_name": display_name,
        })

    # -- servers & channels --

    async def create_server(self, token: str, name: str, description: str = "") -> dict:
        return await self._req("POST", "/servers/create", token=token, json={
            "name": name,
            "description": description,
        })

    async def create_channel(self, token: str, server_id: str, name: str) -> dict | None:
        return await self._req("POST", f"/servers/{server_id}/channels", token=token, json={
            "type": "Text",
            "name": name,
        })

    async def create_invite(self, token: str, channel_id: str) -> str | None:
        resp = await self._req("POST", f"/channels/{channel_id}/invites", token=token)
        return resp["_id"] if resp else None

    async def join_invite(self, token: str, code: str):
        try:
            await self._req("POST", f"/invites/{code}", token=token)
        except httpx.HTTPStatusError:
            pass  # already a member

    # -- messages --

    async def send_message(self, token: str, channel_id: str, content: str) -> dict | None:
        return await self._req("POST", f"/channels/{channel_id}/messages", token=token, json={
            "content": content,
        })

    async def get_messages(self, token: str, channel_id: str, limit: int = 20) -> list[dict]:
        resp = await self._http.get(
            f"/channels/{channel_id}/messages",
            params={"limit": limit},
            headers={"x-session-token": token},
        )
        resp.raise_for_status()
        return resp.json()

    async def react(self, token: str, channel_id: str, message_id: str, emoji: str):
        await self._req("PUT", f"/channels/{channel_id}/messages/{message_id}/reactions/{emoji}", token=token)

    # -- health --

    async def health_check(self) -> bool:
        try:
            await self._http.get("/")
            return True
        except (httpx.HTTPError, httpx.ConnectError):
            return False
