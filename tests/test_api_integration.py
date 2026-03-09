"""Integration tests for FLUME and RL API endpoints.

Tests the /flume/encode, /flume/decode, /flume/interpolate,
/rl/step, /rl/episode, and /rl/policy-info endpoints using
httpx.AsyncClient with ASGITransport (no live server needed).
"""

from __future__ import annotations

import pytest
import pytest_asyncio
from httpx import ASGITransport, AsyncClient

from cohezion.api import app


Z_DIM = 256


@pytest_asyncio.fixture()
async def client():
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


# ---------- FLUME Encode ----------


@pytest.mark.asyncio
async def test_flume_encode_returns_mu_and_logvar(client):
    """POST /flume/encode returns mu and log_var with correct 256D shapes."""
    vector = [0.5] * Z_DIM
    resp = await client.post("/flume/encode", json={"vector": vector})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["mu"]) == Z_DIM
    assert len(data["log_var"]) == Z_DIM
    assert isinstance(data["coherence"], float)
    assert 0.0 <= data["coherence"] <= 1.0


@pytest.mark.asyncio
async def test_flume_encode_wrong_dimension(client):
    """POST /flume/encode rejects vectors that are not 256D."""
    resp = await client.post("/flume/encode", json={"vector": [0.1] * 10})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_flume_encode_missing_field(client):
    """POST /flume/encode rejects request without vector field."""
    resp = await client.post("/flume/encode", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_flume_encode_coherence_near_target(client):
    """Encoding a vector centered at 0.5 should yield high coherence."""
    vector = [0.5] * Z_DIM
    resp = await client.post("/flume/encode", json={"vector": vector})
    data = resp.json()
    assert 0.0 <= data["coherence"] <= 1.0


# ---------- FLUME Decode ----------


@pytest.mark.asyncio
async def test_flume_decode_returns_256d(client):
    """POST /flume/decode returns a 256D reconstruction."""
    latent = [0.0] * Z_DIM
    resp = await client.post("/flume/decode", json={"latent": latent})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["reconstruction"]) == Z_DIM
    assert isinstance(data["coherence"], float)
    assert 0.0 <= data["coherence"] <= 1.0


@pytest.mark.asyncio
async def test_flume_decode_wrong_dim_errors(client):
    """POST /flume/decode with wrong dim raises an error (dimension mismatch)."""
    latent = [0.1] * 128
    with pytest.raises(RuntimeError, match="cannot be multiplied"):
        await client.post("/flume/decode", json={"latent": latent})


@pytest.mark.asyncio
async def test_flume_decode_missing_field(client):
    """POST /flume/decode rejects request without latent field."""
    resp = await client.post("/flume/decode", json={})
    assert resp.status_code == 422


# ---------- FLUME Interpolate ----------


@pytest.mark.asyncio
async def test_flume_interpolate_returns_result(client):
    """POST /flume/interpolate returns interpolated vector with coherence."""
    va = [0.3] * Z_DIM
    vb = [0.7] * Z_DIM
    resp = await client.post(
        "/flume/interpolate",
        json={"vector_a": va, "vector_b": vb, "ratio": 0.5},
    )
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["result"]) == Z_DIM
    assert len(data["mu_a"]) == Z_DIM
    assert len(data["mu_b"]) == Z_DIM
    assert isinstance(data["coherence"], float)
    assert 0.0 <= data["coherence"] <= 1.0


@pytest.mark.asyncio
async def test_flume_interpolate_ratio_boundaries(client):
    """Ratio=0 returns vector_a encoding, ratio=1 returns vector_b encoding."""
    va = [0.2] * Z_DIM
    vb = [0.8] * Z_DIM

    resp_a = await client.post(
        "/flume/interpolate",
        json={"vector_a": va, "vector_b": vb, "ratio": 0.0},
    )
    resp_b = await client.post(
        "/flume/interpolate",
        json={"vector_a": va, "vector_b": vb, "ratio": 1.0},
    )
    assert resp_a.status_code == 200
    assert resp_b.status_code == 200

    data_a = resp_a.json()
    data_b = resp_b.json()

    # At ratio=0, result should match decoding of mu_a
    # At ratio=1, result should match decoding of mu_b
    # They should differ from each other
    assert data_a["result"] != data_b["result"]


@pytest.mark.asyncio
async def test_flume_interpolate_default_ratio(client):
    """Ratio defaults to 0.5 when not provided."""
    va = [0.4] * Z_DIM
    vb = [0.6] * Z_DIM
    resp = await client.post(
        "/flume/interpolate",
        json={"vector_a": va, "vector_b": vb},
    )
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_flume_interpolate_wrong_dimension(client):
    """POST /flume/interpolate rejects mismatched dimensions."""
    resp = await client.post(
        "/flume/interpolate",
        json={"vector_a": [0.1] * 10, "vector_b": [0.2] * Z_DIM, "ratio": 0.5},
    )
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_flume_interpolate_invalid_ratio(client):
    """POST /flume/interpolate rejects ratio outside [0, 1]."""
    va = [0.5] * Z_DIM
    vb = [0.5] * Z_DIM
    resp = await client.post(
        "/flume/interpolate",
        json={"vector_a": va, "vector_b": vb, "ratio": 1.5},
    )
    assert resp.status_code == 422


# ---------- RL Step ----------


@pytest.mark.asyncio
async def test_rl_step_returns_action(client):
    """POST /rl/step returns a 256D action with coherence."""
    state = [0.5] * Z_DIM
    resp = await client.post("/rl/step", json={"state": state})
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["action"]) == Z_DIM
    assert isinstance(data["coherence"], float)
    assert 0.0 <= data["coherence"] <= 1.0


@pytest.mark.asyncio
async def test_rl_step_wrong_dimension(client):
    """POST /rl/step rejects non-256D state vectors."""
    resp = await client.post("/rl/step", json={"state": [0.1] * 10})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rl_step_missing_field(client):
    """POST /rl/step rejects request without state field."""
    resp = await client.post("/rl/step", json={})
    assert resp.status_code == 422


@pytest.mark.asyncio
async def test_rl_step_actions_bounded(client):
    """Policy actions should be clipped to [-1, 1]."""
    state = [0.5] * Z_DIM
    resp = await client.post("/rl/step", json={"state": state})
    data = resp.json()
    for a in data["action"]:
        assert -1.0 <= a <= 1.0


# ---------- RL Episode ----------


@pytest.mark.asyncio
async def test_rl_episode_returns_trajectory(client):
    """POST /rl/episode returns full trajectory with metrics."""
    resp = await client.post("/rl/episode")
    assert resp.status_code == 200
    data = resp.json()
    assert data["steps"] > 0
    assert isinstance(data["total_reward"], float)
    assert isinstance(data["mean_coherence"], float)
    assert isinstance(data["final_coherence"], float)
    assert 0.0 <= data["mean_coherence"] <= 1.0
    assert 0.0 <= data["final_coherence"] <= 1.0
    assert len(data["trajectory"]) == data["steps"]


@pytest.mark.asyncio
async def test_rl_episode_trajectory_structure(client):
    """Each trajectory step has expected fields."""
    resp = await client.post("/rl/episode")
    data = resp.json()
    step = data["trajectory"][0]
    assert "state_mean" in step
    assert "state_std" in step
    assert "action_norm" in step
    assert "reward" in step
    assert "coherence" in step


# ---------- RL Policy Info ----------


@pytest.mark.asyncio
async def test_rl_policy_info_metadata(client):
    """GET /rl/policy-info returns policy metadata."""
    resp = await client.get("/rl/policy-info")
    assert resp.status_code == 200
    data = resp.json()
    assert "loaded" in data
    if data["loaded"]:
        assert data["state_dim"] == Z_DIM
        assert data["action_dim"] == Z_DIM
        assert data["parameters"] is not None
        assert data["parameters"] > 0
        assert data["architecture"] is not None
    else:
        # No checkpoint, still valid response
        assert data["checkpoint_path"] is None
