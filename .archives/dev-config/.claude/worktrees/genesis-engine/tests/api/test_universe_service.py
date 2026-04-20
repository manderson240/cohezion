"""Tests for the Universe State API service.

Validates that the universe physics endpoints return real HIHO engine
data (coherence near 0.5, EVO states, CA grid) rather than random values.
"""

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.universe import (
    UniverseStateResponse,
    UniverseStateService,
    universe_router,
)


@pytest.fixture
def service() -> UniverseStateService:
    return UniverseStateService(num_evos=4)


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(universe_router, prefix="/api/universe")
    return TestClient(app)


class TestUniverseStateService:
    def test_initial_state_has_correct_structure(self, service: UniverseStateService) -> None:
        state = service.get_state()
        assert isinstance(state, UniverseStateResponse)
        assert isinstance(state.coherence, float)
        assert isinstance(state.tick, int)
        assert isinstance(state.ca_grid, list)
        assert len(state.ca_grid) == 256
        assert isinstance(state.evo_states, list)
        assert len(state.evo_states) == 4

    def test_initial_coherence_near_half(self, service: UniverseStateService) -> None:
        state = service.get_state()
        # EVOs initialize at 0.5 coherence (HIHO boundary)
        assert 0.3 <= state.coherence <= 0.7

    def test_tick_advances_state(self, service: UniverseStateService) -> None:
        state_before = service.get_state()
        service.tick()
        state_after = service.get_state()
        assert state_after.tick == state_before.tick + 1
        # CA grid should evolve (not stay identical)
        assert state_after.ca_grid != state_before.ca_grid

    def test_hiho_drives_coherence_toward_half(self, service: UniverseStateService) -> None:
        """After multiple ticks, coherence should stay near 0.5 due to HIHO restoring force."""
        for _ in range(20):
            service.tick()
        state = service.get_state()
        # HIHO Hooke's law drives coherence toward 0.5
        assert 0.2 <= state.coherence <= 0.8

    def test_evo_states_have_physics_fields(self, service: UniverseStateService) -> None:
        state = service.get_state()
        for evo in state.evo_states:
            assert "charge_density" in evo
            assert "magnetic_helicity" in evo
            assert "toroidal_moment" in evo
            assert "coherence" in evo


class TestUniverseAPIEndpoints:
    def test_get_state_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/universe/state")
        assert resp.status_code == 200
        data = resp.json()
        assert "coherence" in data
        assert "ca_grid" in data
        assert "evo_states" in data

    def test_post_tick_advances_and_returns_state(self, client: TestClient) -> None:
        resp = client.post("/api/universe/tick")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tick"] >= 1
        assert isinstance(data["coherence"], float)

    def test_multiple_ticks_produce_different_states(self, client: TestClient) -> None:
        resp1 = client.post("/api/universe/tick")
        resp2 = client.post("/api/universe/tick")
        data1 = resp1.json()
        data2 = resp2.json()
        assert data2["tick"] > data1["tick"]


class TestSynthesisReport:
    def test_report_returns_200(self, client: TestClient) -> None:
        # Tick a few times so there's something to report on
        for _ in range(5):
            client.post("/api/universe/tick")
        resp = client.get("/api/universe/report")
        assert resp.status_code == 200

    def test_report_has_required_sections(self, client: TestClient) -> None:
        for _ in range(3):
            client.post("/api/universe/tick")
        data = client.get("/api/universe/report").json()
        assert "hiho_status" in data
        assert "ca_analysis" in data
        assert "evo_health" in data
        assert "summary" in data

    def test_report_hiho_status_fields(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        data = client.get("/api/universe/report").json()
        hiho = data["hiho_status"]
        assert "mean_coherence" in hiho
        assert "stability" in hiho
        assert "deviation_from_target" in hiho
        assert hiho["stability"] in ("stable", "warning", "critical")

    def test_report_ca_analysis_fields(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        data = client.get("/api/universe/report").json()
        ca = data["ca_analysis"]
        assert "density" in ca
        assert "active_cells" in ca
        assert "total_cells" in ca
        assert isinstance(ca["density"], float)

    def test_report_evo_health_per_agent(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        data = client.get("/api/universe/report").json()
        assert len(data["evo_health"]) > 0
        for evo in data["evo_health"]:
            assert "id" in evo
            assert "coherence" in evo
            assert "charge_status" in evo


class TestPerturbations:
    def test_coherence_spike_shifts_coherence_up(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        before = client.get("/api/universe/state").json()["coherence"]
        resp = client.post(
            "/api/universe/perturb", json={"kind": "coherence_spike", "magnitude": 0.3}
        )
        assert resp.status_code == 200
        after = resp.json()["coherence"]
        assert after > before

    def test_coherence_collapse_shifts_coherence_down(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        before = client.get("/api/universe/state").json()["coherence"]
        resp = client.post(
            "/api/universe/perturb", json={"kind": "coherence_collapse", "magnitude": 0.3}
        )
        assert resp.status_code == 200
        after = resp.json()["coherence"]
        assert after < before

    def test_hiho_recovers_after_perturbation(self, client: TestClient) -> None:
        """HIHO restoring force should pull coherence back toward 0.5."""
        client.post("/api/universe/perturb", json={"kind": "coherence_spike", "magnitude": 0.4})
        spiked = client.get("/api/universe/state").json()["coherence"]
        # Tick 30 times to let HIHO recover
        for _ in range(30):
            client.post("/api/universe/tick")
        recovered = client.get("/api/universe/state").json()["coherence"]
        # Should be closer to 0.5 than the spike was
        assert abs(recovered - 0.5) < abs(spiked - 0.5)

    def test_charge_injection_boosts_charge(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        before_evos = client.get("/api/universe/state").json()["evo_states"]
        resp = client.post(
            "/api/universe/perturb", json={"kind": "charge_injection", "magnitude": 0.5}
        )
        assert resp.status_code == 200
        after_evos = resp.json()["evo_states"]
        # At least one EVO should have higher charge
        assert any(
            a["charge_density"] > b["charge_density"] for a, b in zip(after_evos, before_evos)
        )

    def test_ca_reset_clears_grid(self, client: TestClient) -> None:
        # Tick to grow the CA fabric
        for _ in range(10):
            client.post("/api/universe/tick")
        before_active = sum(client.get("/api/universe/state").json()["ca_grid"])
        assert before_active > 1
        resp = client.post("/api/universe/perturb", json={"kind": "ca_reset"})
        assert resp.status_code == 200
        after_active = sum(resp.json()["ca_grid"])
        # Should be back to single center impulse
        assert after_active == 1

    def test_invalid_perturbation_returns_422(self, client: TestClient) -> None:
        resp = client.post("/api/universe/perturb", json={"kind": "nonexistent"})
        assert resp.status_code == 422

    def test_magnitude_clamped_to_safe_range(self, client: TestClient) -> None:
        resp = client.post(
            "/api/universe/perturb", json={"kind": "coherence_spike", "magnitude": 999.0}
        )
        assert resp.status_code == 200
        # Coherence should never exceed 1.0
        for evo in resp.json()["evo_states"]:
            assert evo["coherence"] <= 1.0
