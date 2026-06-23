"""Deterministic 8-journey backfill for the universe corpus.

Exports consumed by tests/api/test_journey_corpus_seeder.py.
"""

from __future__ import annotations

import hashlib
import json
import math
import random
from pathlib import Path

# Dimension constants matching the test assertions
INITIAL_AXIOMATIC_DIM: int = 12
FINAL_AXIOMATIC_DIM: int = 12
LATENT_EMBEDDING_DIM: int = 2048
TRAJECTORY_STEPS: int = 20
FLUME_Z_DIM: int = 256

# Storage paths — universe dir at <repo>/data/universe
_REPO_ROOT = Path(__file__).resolve().parents[4]
UNIVERSE_DIR: Path = _REPO_ROOT / "data" / "universe"
SEED_FLAG_FILE: Path = UNIVERSE_DIR / "seed.flag"


def _gauss_hiho(rng: random.Random, dim: int) -> list[float]:
    """Draw from N(0.5, 0.1) clamped to [0,1] — the HIHO kernel band."""
    return [max(0.0, min(1.0, rng.gauss(0.5, 0.1))) for _ in range(dim)]


def _uniform_norm(rng: random.Random, dim: int) -> list[float]:
    """Draw from U(0,1)."""
    return [rng.random() for _ in range(dim)]


def _make_journey(journey_index: int, seed: int) -> tuple[str, dict]:
    rng = random.Random(seed + journey_index * 997)

    jid = "journey_" + hashlib.sha1(f"seed{seed}-idx{journey_index}".encode()).hexdigest()[:12]

    trajectory = []
    for step in range(TRAJECTORY_STEPS):
        coherence = max(0.0, min(1.0, rng.gauss(0.5 + step * 0.01, 0.05)))
        trajectory.append(
            {
                "step": step,
                "state_12d": _gauss_hiho(rng, INITIAL_AXIOMATIC_DIM),
                "z_256": _gauss_hiho(rng, FLUME_Z_DIM),
                "coherence": round(coherence, 4),
                "timestamp": f"2026-06-22T00:{step:02d}:00Z",
            }
        )

    final_coherence = round(sum(s["coherence"] for s in trajectory) / TRAJECTORY_STEPS, 4)
    phi = round(math.sin(final_coherence * math.pi) * 0.8 + 0.1, 4)

    data = {
        "id": jid,
        "initial_axiomatic": _gauss_hiho(rng, INITIAL_AXIOMATIC_DIM),
        "initial_latent_embedding": _uniform_norm(rng, LATENT_EMBEDDING_DIM),
        "flume_z": _gauss_hiho(rng, FLUME_Z_DIM),
        "trajectory": trajectory,
        "final_coherence": final_coherence,
        "final_phi_score": phi,
        "summary": f"Stub journey {journey_index}: coherence {final_coherence:.3f}",
        "precipitation_type": "synthetic_hiho",
        "status": "complete",
    }
    return jid, data


def seed_stub_corpus(
    *,
    n: int = 8,
    seed: int = 42,
    force: bool = False,
) -> list[str]:
    """Seed *n* deterministic stub journeys into UNIVERSE_DIR.

    Idempotent: returns [] without writing when seed.flag exists and
    force=False.  Returns the list of journey IDs written.
    """
    UNIVERSE_DIR.mkdir(parents=True, exist_ok=True)

    if SEED_FLAG_FILE.exists() and not force:
        return []

    # Remove prior journeys when force=True
    if force:
        for p in UNIVERSE_DIR.glob("journey_*.json"):
            p.unlink()

    ids = []
    for i in range(n):
        jid, data = _make_journey(i, seed)
        (UNIVERSE_DIR / f"{jid}.json").write_text(json.dumps(data, indent=2))
        ids.append(jid)

    SEED_FLAG_FILE.write_text(f"seed={seed} n={n}\n")
    return ids
