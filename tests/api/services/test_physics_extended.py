"""Tests for api/services/physics_extended.py.

Covers all bioelectric, natural-capital, cosmogony, Hamiltonian, triune,
phonon, morphospace, LCSP, emergence, LENR, ionic-cluster, dielectric,
Sarfatti, QGP, BEC, Mercury, COLIBRE, MHD, Bismuth, Toroidal, and
tensor-metric endpoints.
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cohezion.api import app


@pytest_asyncio.fixture()
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_bioelectric(client):
    """Should simulate bioelectric network."""
    resp = await client.get("/api/physics/bioelectric?n_cells=8&conductance=0.5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["n_cells"] == 8
    assert "v_mem" in data
    assert "coherence" in data


@pytest.mark.asyncio
async def test_natural_capital(client):
    """Should evaluate natural capital metrics."""
    resp = await client.get("/api/physics/natural-capital?coherence=0.6")
    assert resp.status_code == 200
    data = resp.json()
    assert "total_natural_capital" in data
    assert "habitat_quality" in data


@pytest.mark.asyncio
async def test_cosmogony_full_chain(client):
    """Should return full cosmogony chain status."""
    resp = await client.get("/api/physics/cosmogony/full-chain")
    assert resp.status_code == 200
    data = resp.json()
    assert data["total_steps"] == 10
    assert "fisher_eigenvalue_max" in data


@pytest.mark.asyncio
async def test_hamiltonian_simulate(client):
    """Should run Hamiltonian trajectory simulation."""
    resp = await client.get("/api/physics/hamiltonian/simulate?epochs=10&n_agents=2")
    assert resp.status_code == 200
    data = resp.json()
    assert data["epochs"] == 10
    assert "initial_energy" in data
    assert "final_energy" in data


@pytest.mark.asyncio
async def test_triune_state(client):
    """Should return Triune state metrics."""
    resp = await client.get("/api/physics/triune/state")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["doer"]) == 12
    assert "hiho_coherence" in data


@pytest.mark.asyncio
async def test_phonon_state(client):
    """Should return phonon dynamics state."""
    resp = await client.get("/api/physics/phonons/state")
    assert resp.status_code == 200
    data = resp.json()
    assert "expansion_rate" in data
    assert "coherence_gain" in data


@pytest.mark.asyncio
async def test_morphospace_wells(client):
    """Should return morphospace stability wells."""
    resp = await client.get("/api/physics/morphospace/wells")
    assert resp.status_code == 200
    data = resp.json()
    assert "wells" in data


@pytest.mark.asyncio
async def test_lcsp_predict(client):
    """Should predict next 12D state using LCSP."""
    state_str = ",".join(["0.5"] * 12)
    resp = await client.get(f"/api/physics/lcsp/predict?state={state_str}")
    assert resp.status_code == 200
    data = resp.json()
    assert "next_state" in data
    assert "hiho_stability" in data


@pytest.mark.asyncio
async def test_emergence_detect(client):
    """Should detect emergence in synthetic data."""
    resp = await client.get("/api/physics/emergence/detect?n_agents=4&n_cycles=30")
    assert resp.status_code == 200
    data = resp.json()
    assert "complexity_score" in data
    assert "events" in data


@pytest.mark.asyncio
async def test_lenr_simulate(client):
    """Should simulate LENR Hamiltonian dynamics."""
    resp = await client.get("/api/physics/lenr/simulate?coherence=0.7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coherence"] == 0.7
    assert "reaction_rate" in data


@pytest.mark.asyncio
async def test_lenr_event(client):
    """Should post LENR event and return response."""
    payload = {"coherence": 0.8, "agent_id": "test-agent"}
    resp = await client.post("/api/physics/lenr/event", json=payload)
    assert resp.status_code == 200
    data = resp.json()
    assert data["coherence"] == 0.8
    assert "mean_rate" in data


@pytest.mark.asyncio
async def test_ionic_cluster_status_and_step(client):
    """Should get ionic cluster status and perform step."""
    agent_id = "test-ionic-agent"
    resp = await client.get(f"/api/physics/ionic-cluster/status?agent_id={agent_id}")
    assert resp.status_code == 200
    data = resp.json()
    assert "plasma_density" in data

    # Step
    payload = {"delta": 0.1, "agent_id": agent_id}
    resp2 = await client.post("/api/physics/ionic-cluster/step", json=payload)
    assert resp2.status_code == 200
    data2 = resp2.json()
    assert data2["plasma_density"] == pytest.approx(data["plasma_density"] + 0.1, rel=1e-5)


@pytest.mark.asyncio
async def test_dielectric_polarization(client):
    """Should return dielectric field metrics."""
    resp = await client.get("/api/physics/dielectric/polarization?voltage=12000")
    assert resp.status_code == 200
    data = resp.json()
    assert data["voltage"] == 12000
    assert "biefield_brown_force" in data


@pytest.mark.asyncio
async def test_sarfatti_backaction(client):
    """Should return Sarfatti back-action dynamics."""
    resp = await client.get("/api/physics/sarfatti/backaction?coherence=0.4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coherence"] == 0.4
    assert "back_action_amplitude" in data


@pytest.mark.asyncio
async def test_qgp_status(client):
    """Should return QGP crossover status."""
    resp = await client.get("/api/physics/qgp/status?quark_coherence=0.6")
    assert resp.status_code == 200
    data = resp.json()
    assert data["quark_coherence"] == 0.6
    assert "deconfinement_rate" in data


@pytest.mark.asyncio
async def test_bec_status(client):
    """Should return BEC status."""
    resp = await client.get("/api/physics/bec/status?condensate_fraction=0.8")
    assert resp.status_code == 200
    data = resp.json()
    assert data["condensate_fraction"] == 0.8
    assert "transition_rate" in data


@pytest.mark.asyncio
async def test_mercury_status(client):
    """Should return Mercury lattice superconductivity status."""
    resp = await client.get("/api/physics/mercury/status?coherence=0.7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coherence"] == 0.7
    assert "is_superconducting" in data


@pytest.mark.asyncio
async def test_colibre_status(client):
    """Should return COLIBRE cosmic status."""
    resp = await client.get("/api/physics/colibre/status?redshift=1.5")
    assert resp.status_code == 200
    data = resp.json()
    assert data["redshift"] == 1.5
    assert "colibre_coherence" in data


@pytest.mark.asyncio
async def test_mhd_status(client):
    """Should return MHD plasma status."""
    resp = await client.get("/api/physics/mhd/status?plasma_beta=0.4")
    assert resp.status_code == 200
    data = resp.json()
    assert data["plasma_beta"] == 0.4
    assert "alfven_coherence" in data


@pytest.mark.asyncio
async def test_bismuth_status(client):
    """Should return Bismuth levitation status."""
    resp = await client.get("/api/physics/bismuth/status?field_strength_tesla=5.0")
    assert resp.status_code == 200
    data = resp.json()
    assert data["field_strength_tesla"] == 5.0
    assert "hiho_levitation" in data


@pytest.mark.asyncio
async def test_toroidal_status(client):
    """Should return toroidal moment status."""
    resp = await client.get("/api/physics/toroidal/status?coherence=0.6")
    assert resp.status_code == 200
    data = resp.json()
    assert data["coherence"] == 0.6
    assert "toroidal_moment_magnitude" in data


@pytest.mark.asyncio
async def test_tensor_metric_status(client):
    """Should return tensor-metric engineering status."""
    resp = await client.get("/api/physics/tensor-metric/status?sarfatti_coherence=0.7")
    assert resp.status_code == 200
    data = resp.json()
    assert data["sarfatti_coherence"] == 0.7
    assert "metric_determinant" in data
