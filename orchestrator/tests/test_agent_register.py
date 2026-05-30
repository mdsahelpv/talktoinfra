"""Tests for the agent registration endpoint."""

from fastapi.testclient import TestClient
from src.main import app

client = TestClient(app)


def test_register_agent():
    resp = client.post("/api/v1/agents/register", json={
        "agent_id": "test-agent-1",
        "version": "0.1.0",
        "actions": ["k8s_get_pods", "dns_lookup"],
    })
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "registered"


def test_heartbeat():
    resp = client.post("/api/v1/agents/heartbeat", json={"agent_id": "test-agent-1"})
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


def test_list_agents():
    resp = client.get("/api/v1/agents")
    assert resp.status_code == 200
    data = resp.json()
    assert "agents" in data
