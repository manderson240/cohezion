"""Unit and Integration Tests for the Cohezion Observability HUD API Service."""

from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.observability_hud_service import app


@pytest.fixture
def client():
    return TestClient(app)


def test_hud_health_endpoint(client):
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "HEALTHY"
    assert data["service"] == "cohezion-topological-hud"


def test_hud_live_telemetry_endpoint(client):
    res = client.get("/api/telemetry/live")
    assert res.status_code == 200
    data = res.json()
    assert "memory" in data and data["memory"]["total_gb"] > 0
    assert "geometry" in data and data["geometry"]["poincare_norm"] < 1.0
    assert "sheaf_cohomology" in data and "dim_h0_consensus" in data["sheaf_cohomology"]
    assert "hiho_sonification" in data and data["hiho_sonification"]["fundamental_hz"] == 432.0


def test_hud_mcp_tools_catalog_endpoint(client):
    res = client.get("/api/mcp/tools")
    assert res.status_code == 200
    tools = res.json()
    assert isinstance(tools, list) and len(tools) >= 6
    tool_names = [t["name"] for t in tools]
    assert "cohezion_autoharness_verify" in tool_names
    assert "cohezion_sheaf_cohomology_gate" in tool_names


def test_hud_sheaf_evaluation_endpoint(client):
    claims = {
        "agent_a": [0.1] * 12,
        "agent_b": [0.1] * 12,
        "agent_c": [0.1] * 12,
    }
    res = client.post("/api/sheaf/evaluate", json={"agent_claims": claims})
    assert res.status_code == 200
    data = res.json()
    assert data["is_consistent"] is True
    assert data["dim_h1_obstructions"] == 0


def test_hud_sandbox_execute_endpoint(client):
    code = "def add(a: int, b: int) -> int:\n    return a + b\nassert add(1, 2) == 3\n"
    res = client.post("/api/sandbox/execute", json={"code": code})
    assert res.status_code == 200
    data = res.json()
    assert data["passed"] is True
    assert data["static_ast_verified"] is True
