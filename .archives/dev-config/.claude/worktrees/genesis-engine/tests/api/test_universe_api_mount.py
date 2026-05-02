"""Tests verifying universe router is mounted in the main app with CORS."""

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_universe_state_endpoint_exists(client: TestClient) -> None:
    resp = client.get("/api/universe/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "coherence" in data
    assert "ca_grid" in data


def test_universe_tick_endpoint_exists(client: TestClient) -> None:
    resp = client.post("/api/universe/tick")
    assert resp.status_code == 200
    data = resp.json()
    assert data["tick"] >= 1


def test_cors_allows_localhost_3000(client: TestClient) -> None:
    resp = client.options(
        "/api/universe/state",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET",
        },
    )
    assert resp.status_code == 200
    assert "http://localhost:3000" in resp.headers.get("access-control-allow-origin", "")
