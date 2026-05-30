"""REST API client for the orchestrator."""

import httpx


class APIClient:
    def __init__(self, base_url: str, api_key: str = ""):
        self.base_url = base_url.rstrip("/")
        self._http = httpx.Client(timeout=60)
        self._api_key = api_key

    def _headers(self) -> dict:
        h = {"Content-Type": "application/json"}
        if self._api_key:
            h["x-api-key"] = self._api_key
        return h

    def health(self) -> dict:
        resp = self._http.get(f"{self.base_url}/health", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def chat(self, message: str, session_id: str = "") -> dict:
        resp = self._http.post(
            f"{self.base_url}/api/v1/chat",
            json={"session_id": session_id, "message": message},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def approve(self, approval_id: str, approved: bool, note: str = "") -> dict:
        resp = self._http.post(
            f"{self.base_url}/api/v1/chat/approve",
            params={"approval_id": approval_id, "approved": str(approved).lower(), "note": note},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def list_sessions(self, limit: int = 20, offset: int = 0) -> dict:
        resp = self._http.get(
            f"{self.base_url}/api/v1/sessions",
            params={"limit": limit, "offset": offset},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def create_session(self, description: str = "") -> dict:
        resp = self._http.post(
            f"{self.base_url}/api/v1/sessions",
            params={"description": description},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()

    def list_tools(self) -> dict:
        resp = self._http.get(f"{self.base_url}/api/v1/tools", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def list_agents(self) -> dict:
        resp = self._http.get(f"{self.base_url}/api/v1/agents", headers=self._headers())
        resp.raise_for_status()
        return resp.json()

    def get_audit_log(self, session_id: str = "", limit: int = 50) -> dict:
        resp = self._http.get(
            f"{self.base_url}/api/v1/audit",
            params={"session_id": session_id, "limit": limit},
            headers=self._headers(),
        )
        resp.raise_for_status()
        return resp.json()
