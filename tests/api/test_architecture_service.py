"""Tests for the Architecture Graph API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    from cohezion.api.services.architecture import architecture_router

    app = FastAPI()
    app.include_router(architecture_router, prefix="/api/architecture")
    return TestClient(app)


class TestArchitectureGraph:
    def test_graph_returns_nodes_and_edges(self, client: TestClient) -> None:
        resp = client.get("/api/architecture/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0
