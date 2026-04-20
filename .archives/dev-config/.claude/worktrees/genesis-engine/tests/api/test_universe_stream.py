"""Tests for SSE universe stream (Master Clock)."""

import json

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.universe import (
    UniverseStateService,
    universe_router,
)


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(universe_router, prefix="/api/universe")
    return TestClient(app)


class TestUniverseHistory:
    def test_service_stores_tick_history(self) -> None:
        svc = UniverseStateService(num_evos=4)
        for _ in range(5):
            svc.tick()
        history = svc.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].tick == 5

    def test_history_bounded_to_max(self) -> None:
        from collections import deque

        svc = UniverseStateService(num_evos=2)
        svc._history = deque(maxlen=10)  # Override for test speed
        for _ in range(15):
            svc.tick()
        assert len(svc._history) == 10

    def test_history_endpoint_returns_json(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        client.post("/api/universe/tick")
        resp = client.get("/api/universe/history?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestSSEStream:
    def test_stream_endpoint_returns_sse(self, client: TestClient) -> None:
        """SSE endpoint returns event stream content type."""
        with client.stream("GET", "/api/universe/stream?max_ticks=3") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            events = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                if len(events) >= 3:
                    break
        assert len(events) >= 1
        assert "tick" in events[0]
        assert "coherence" in events[0]


class TestHistorySummary:
    def test_summary_returns_narrative_fields(self, client: TestClient) -> None:
        for _ in range(20):
            client.post("/api/universe/tick")
        resp = client.get("/api/universe/history/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticks_elapsed" in data
        assert "mean_coherence" in data
        assert "coherence_range" in data
        assert "alert_count" in data
        assert "narrative" in data
