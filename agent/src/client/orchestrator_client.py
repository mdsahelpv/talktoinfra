"""Client to connect to the orchestrator via HTTP/WebSocket."""

import asyncio
import json

import httpx


class OrchestratorClient:
    def __init__(self, url: str, agent_id: str, api_key: str = ""):
        self.url = url.rstrip("/")
        self.agent_id = agent_id or f"agent-{__import__('uuid').uuid4().hex[:8]}"
        self.api_key = api_key
        self.on_tool_call = None
        self._http = httpx.AsyncClient(timeout=30)
        self._connected = False

    async def connect(self):
        """Register with orchestrator and announce available actions."""
        try:
            resp = await self._http.post(
                f"{self.url}/api/v1/agents/register",
                json={
                    "agent_id": self.agent_id,
                    "version": "0.1.0",
                    "actions": self._get_declared_actions(),
                },
                headers=self._headers(),
            )
            if resp.status_code < 400:
                self._connected = True
                print(f"[client] Registered with orchestrator as {self.agent_id}")
            else:
                print(f"[client] Registration failed: {resp.text}")
        except httpx.ConnectError:
            print(f"[client] Cannot connect to orchestrator at {self.url}")
            self._connected = False

    async def heartbeat_loop(self, interval: int = 30):
        while True:
            await asyncio.sleep(interval)
            if self._connected:
                try:
                    resp = await self._http.post(
                        f"{self.url}/api/v1/agents/heartbeat",
                        json={"agent_id": self.agent_id},
                        headers=self._headers(),
                    )
                except httpx.ConnectError:
                    print("[client] Lost connection to orchestrator")
                    self._connected = False

    async def disconnect(self):
        self._connected = False
        await self._http.aclose()

    def _headers(self) -> dict:
        headers = {}
        if self.api_key:
            headers["x-api-key"] = self.api_key
        return headers

    def _get_declared_actions(self) -> list[str]:
        from src.catalog.registry import ActionCatalogRegistry
        return [a["name"] for a in ActionCatalogRegistry.list_all_actions()]
