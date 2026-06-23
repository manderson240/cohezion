"""Deterministic 8-journey backfill for the universe corpus (stub).

Exports consumed by tests/api/test_journey_corpus_seeder.py.
"""

from __future__ import annotations

from pathlib import Path

# Dimension constants matching the test assertions
INITIAL_AXIOMATIC_DIM: int = 12
FINAL_AXIOMATIC_DIM: int = 12
LATENT_EMBEDDING_DIM: int = 2048
TRAJECTORY_STEPS: int = 20

# Storage paths — universe dir at <repo>/data/universe
_REPO_ROOT = Path(__file__).resolve().parents[4]
UNIVERSE_DIR: Path = _REPO_ROOT / "data" / "universe"
SEED_FLAG_FILE: Path = UNIVERSE_DIR / "seed.flag"


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
    raise NotImplementedError
