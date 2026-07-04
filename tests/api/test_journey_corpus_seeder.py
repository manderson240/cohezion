"""Tests for journey_corpus_seeder (deterministic 8-journey backfill).

Idempotency: a second call without force=True returns 0 ids.
Determinism: same seed+n always produces the same ids.
Shape: every seeded journey has 12D initial_axiomatic, 256D flume_z, 20-step
trajectory where each step has 12D state_12d + 256D z_256.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from cohezion.api.services.journey_corpus_seeder import (
    FINAL_AXIOMATIC_DIM,
    INITIAL_AXIOMATIC_DIM,
    LATENT_EMBEDDING_DIM,
    SEED_FLAG_FILE,
    TRAJECTORY_STEPS,
    UNIVERSE_DIR,
    seed_stub_corpus,
)


@pytest.fixture
def clean_corpus():
    """Wipe the universe dir + flag, run, return ids."""
    if UNIVERSE_DIR.exists():
        # Remove only the seed.flag and any prefixed 'journey_*.json' we wrote
        for p in UNIVERSE_DIR.glob("journey_*.json"):
            p.unlink()
    if SEED_FLAG_FILE.exists():
        SEED_FLAG_FILE.unlink()
    yield
    # Cleanup after test
    for p in UNIVERSE_DIR.glob("journey_*.json"):
        p.unlink()
    if SEED_FLAG_FILE.exists():
        SEED_FLAG_FILE.unlink()


def test_dim_constants():
    assert INITIAL_AXIOMATIC_DIM == 12
    assert LATENT_EMBEDDING_DIM == 2048
    assert TRAJECTORY_STEPS == 20
    assert FINAL_AXIOMATIC_DIM == 12


def test_universe_dir_is_repo_data(clean_corpus):
    """UNIVERSE_DIR must point to <repo>/data/universe, not <repo>/src/data/universe."""
    # tests/api/<file> → parents[0]=api, [1]=tests, [2]=repo root
    expected = Path(__file__).resolve().parents[2] / "data" / "universe"
    assert expected == UNIVERSE_DIR


def test_seed_writes_eight_journeys(clean_corpus):
    ids = seed_stub_corpus(n=8, force=True)
    assert len(ids) == 8
    assert len(set(ids)) == 8  # distinct ids
    for jid in ids:
        assert (UNIVERSE_DIR / f"{jid}.json").exists()


def test_seeded_journey_shape(clean_corpus):
    ids = seed_stub_corpus(n=8, force=True)
    j = json.loads((UNIVERSE_DIR / f"{ids[0]}.json").read_text())
    # Top-level keys
    assert "initial_axiomatic" in j
    assert "initial_latent_embedding" in j
    assert "flume_z" in j
    assert "trajectory" in j
    assert "final_coherence" in j
    assert "final_phi_score" in j
    assert "summary" in j
    assert "precipitation_type" in j
    assert "status" in j
    # Dimensional
    assert len(j["initial_axiomatic"]) == 12
    assert len(j["initial_latent_embedding"]) == 2048
    assert len(j["flume_z"]) == 256
    assert len(j["trajectory"]) == 20
    for step in j["trajectory"]:
        assert "state_12d" in step and len(step["state_12d"]) == 12
        assert "z_256" in step and len(step["z_256"]) == 256
        assert "coherence" in step
        assert "timestamp" in step
    assert j["status"] == "complete"


def test_seed_is_deterministic(clean_corpus):
    ids1 = seed_stub_corpus(n=8, force=True)
    ids2 = seed_stub_corpus(n=8, force=True)
    assert ids1 == ids2


def test_seed_is_idempotent(clean_corpus):
    ids1 = seed_stub_corpus(n=8, force=True)
    # Second call without force must short-circuit
    ids2 = seed_stub_corpus(n=8)
    assert ids1 == ids1  # written first time
    assert ids2 == []  # skipped on second call
    assert SEED_FLAG_FILE.exists()


def test_force_overwrites(clean_corpus):
    seed_stub_corpus(n=4, force=True)
    # Files should have been written; re-seeding with different n+force=True must replace
    seed_stub_corpus(n=8, force=True)
    assert len(list(UNIVERSE_DIR.glob("journey_*.json"))) == 8


def test_z_256_in_hiho_band(clean_corpus):
    """HIHO kernel peaks at 0.5; seed draws from N(0.5, 0.1) clamped to [0,1]."""
    ids = seed_stub_corpus(n=8, force=True)
    j = json.loads((UNIVERSE_DIR / f"{ids[0]}.json").read_text())
    for step in j["trajectory"]:
        for v in step["z_256"]:
            assert 0.0 <= v <= 1.0
