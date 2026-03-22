"""Tests for persistent homology data in reports."""

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.universe import universe_router


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(universe_router, prefix="/api/universe")
    return TestClient(app)


class TestTopologyInReport:
    def test_report_includes_topology(self, client: TestClient) -> None:
        for _ in range(10):
            client.post("/api/universe/tick")
        resp = client.get("/api/universe/report")
        data = resp.json()
        assert "topology" in data
        assert "persistence_pairs" in data["topology"]
        assert "entropy" in data["topology"]
