"""Tests for the Anima service (3-tier narration)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    from cohezion.api.services.anima import anima_router

    app = FastAPI()
    app.include_router(anima_router, prefix="/api/anima")
    return TestClient(app)


class TestAnimaStatus:
    def test_status_returns_current_tier(self, client: TestClient) -> None:
        resp = client.get("/api/anima/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] in ("template", "mcp", "voice")
        assert "online" in data


class TestAnimaNarrate:
    def test_narrate_returns_text(self, client: TestClient) -> None:
        resp = client.post("/api/anima/narrate")
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "HIHO" in data["text"]
        assert data["tier"] == "template"


class TestAnimaAsk:
    def test_ask_returns_answer(self, client: TestClient) -> None:
        resp = client.post("/api/anima/ask", json={"question": "What is HIHO?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
