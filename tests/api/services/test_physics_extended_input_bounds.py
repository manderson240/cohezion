"""Input bounds on the stateful/stateless /api/physics endpoints (adversarial review 2026-10-07).

Before: NaN was accepted and poisoned an agent's running LENR mean, a malformed or zero-geometry
dielectric request returned 500 or a ~1e10 force, and any client-chosen agent_id (even 5 MB)
grew process-global registries without limit.
"""

from __future__ import annotations

from collections import OrderedDict

import pytest
from fastapi.testclient import TestClient

from cohezion.api import app
from cohezion.api.services import physics_extended as pe


client = TestClient(app)


@pytest.fixture(autouse=True)
def _fresh_registries(monkeypatch):
    monkeypatch.setattr(pe, "_ionic_cluster_agents", OrderedDict())
    monkeypatch.setattr(pe, "_lenr_agents", OrderedDict())


@pytest.mark.parametrize(
    ("method", "path", "body"),
    [
        ("GET", "/api/physics/lenr/simulate?coherence=nan", None),
        ("GET", "/api/physics/sarfatti/backaction?coherence=inf", None),
        ("GET", "/api/physics/qgp/status?temperature_mev=-1", None),
        ("GET", "/api/physics/dielectric/polarization?electrode_separation=0", None),
        ("GET", "/api/physics/dielectric/polarization?permittivity_diagonal=a,b,c", None),
        ("GET", "/api/physics/dielectric/polarization?permittivity_diagonal=1,2", None),
        ("GET", "/api/physics/dielectric/polarization?permittivity_diagonal=", None),
        ("GET", "/api/physics/ionic-cluster/status?cluster_size=-5", None),
        ("GET", "/api/physics/ionic-cluster/status?agent_id=" + "x" * 65, None),
        ("GET", "/api/physics/ionic-cluster/status?agent_id=a%20b", None),
        ("POST", "/api/physics/lenr/event", '{"coherence": NaN, "agent_id": "a"}'),
        ("POST", "/api/physics/ionic-cluster/step", '{"delta": Infinity, "agent_id": "a"}'),
    ],
)
def test_invalid_input_is_rejected_with_422_not_500(method, path, body) -> None:
    resp = client.request(method, path, content=body, headers={"content-type": "application/json"})
    assert resp.status_code == 422, resp.text


def test_nan_cannot_poison_an_agents_running_mean() -> None:
    for c in (0.8, 0.8):
        client.post("/api/physics/lenr/event", json={"coherence": c, "agent_id": "lenr-a"})
    before = client.post(
        "/api/physics/lenr/event", json={"coherence": 0.8, "agent_id": "lenr-a"}
    ).json()["mean_rate"]
    client.post(
        "/api/physics/lenr/event",
        content='{"coherence": NaN, "agent_id": "lenr-a"}',
        headers={"content-type": "application/json"},
    )
    after = client.post(
        "/api/physics/lenr/event", json={"coherence": 0.8, "agent_id": "lenr-a"}
    ).json()
    assert after["mean_rate"] == pytest.approx(before) and after["event_count"] == 4


def test_agent_registry_is_bounded_lru(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_MAX_AGENTS", 3)
    for i in range(5):
        assert client.get(f"/api/physics/ionic-cluster/status?agent_id=a{i}").status_code == 200
    assert list(pe._ionic_cluster_agents) == ["a2", "a3", "a4"]
    client.get("/api/physics/ionic-cluster/status?agent_id=a2")  # touch: most recently used
    client.get("/api/physics/ionic-cluster/status?agent_id=a5")
    assert list(pe._ionic_cluster_agents) == ["a4", "a2", "a5"]


def test_lenr_event_history_is_a_bounded_window(monkeypatch) -> None:
    monkeypatch.setattr(pe, "_MAX_LENR_EVENTS", 3)
    body: dict = {}
    for _ in range(5):
        body = client.post(
            "/api/physics/lenr/event", json={"coherence": 0.5, "agent_id": "w"}
        ).json()
    assert body["event_count"] == 3


def test_valid_out_of_range_coherence_is_still_clamped_by_the_physics() -> None:
    # Finite values outside [0, 1] are the domain's to clamp, not the API's to reject.
    assert client.get("/api/physics/lenr/simulate?coherence=1.7").status_code == 200
