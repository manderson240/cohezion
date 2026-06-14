"""Item 111: local_storage_index(records, *, encoder) — TDD red→green.

Embeds arbitrary records via an injected encoder and returns the k nearest by cosine.
Encoder is INJECTED (a stub; no live :13305 / SurrealDB under pytest).

Discriminating tests — each kills a plausible wrong implementation:
  - most-similar record ranks first                → test_most_similar_ranks_first (MAIN DISC.)
  - absent record never retrieved                  → test_absent_record_not_retrieved
  - empty corpus → empty query result              → test_empty_corpus_empty_result
  - k=1 returns exactly 1 result                   → test_k_limits_results
  - k > corpus → clipped to corpus size            → test_k_larger_than_corpus
  - exact-match query returns the matched record   → test_exact_match_returns_record
  - score is cosine similarity in [-1, 1]          → test_score_is_cosine
  - top-k are sorted descending by score           → test_top_k_sorted_descending
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.local_storage_index import LocalStorageIndex

# ---------------------------------------------------------------------------
# Stub encoder — deterministic vectors for testing
# ---------------------------------------------------------------------------
# Word → unit vector in a small fixed dimension (3D).
_VECTORS: dict[str, list[float]] = {
    "cat": [1.0, 0.0, 0.0],
    "dog": [0.9, 0.4, 0.0],
    "fish": [0.0, 1.0, 0.0],
    "planet": [0.0, 0.0, 1.0],
    "sky": [0.1, 0.1, 0.9],
}


def _stub_encoder(text: str) -> np.ndarray:
    vec = np.array(_VECTORS.get(text.strip(), [1.0, 1.0, 1.0]), dtype=np.float32)
    return vec / np.linalg.norm(vec)


# ---------------------------------------------------------------------------
# Core correctness
# ---------------------------------------------------------------------------


def test_most_similar_ranks_first() -> None:
    """The record most similar to the query ranks first.

    PRIMARY DISCRIMINATOR: kills an impl that ignores cosine similarity or returns
    records in insertion order regardless of similarity.
    """
    records = ["cat", "fish", "planet"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=3)
    assert results[0].record == "cat", (
        f"'cat' query must return 'cat' as top hit; got {[r.record for r in results]}"
    )


def test_absent_record_not_retrieved() -> None:
    """A record not in the corpus is never retrieved (even if similar).

    Kills an impl that searches globally instead of only the indexed records.
    """
    records = ["fish", "planet"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=3)
    record_names = [r.record for r in results]
    assert "cat" not in record_names, (
        f"'cat' was NOT indexed; must not appear in results; got {record_names}"
    )


def test_empty_corpus_empty_result() -> None:
    """Empty corpus → query returns empty list. No crash."""
    idx = LocalStorageIndex([], encoder=_stub_encoder)
    results = idx.query("cat", k=5)
    assert results == []


def test_k_limits_results() -> None:
    """k=1 returns exactly 1 result even when corpus has more records."""
    records = ["cat", "dog", "fish", "planet"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=1)
    assert len(results) == 1


def test_k_larger_than_corpus() -> None:
    """k > corpus size → returns all corpus records (no IndexError)."""
    records = ["cat", "dog"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=100)
    assert len(results) == 2


def test_exact_match_returns_record() -> None:
    """Querying with the same text as an indexed record → cosine ≈ 1.0 for that record."""
    records = ["cat", "planet"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=2)
    top = results[0]
    assert top.record == "cat"
    assert top.score > 0.99, f"Exact-match cosine must be ≈1.0; got {top.score}"


def test_score_is_cosine() -> None:
    """Score is cosine similarity — ranges in [-1, 1] for normalised vectors."""
    records = ["cat", "fish"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=2)
    for r in results:
        assert -1.0 <= r.score <= 1.0 + 1e-6, (
            f"Score must be in [-1, 1]; got {r.score} for {r.record}"
        )


def test_top_k_sorted_descending() -> None:
    """Results are sorted by score descending (highest-similarity first).

    Kills an impl that returns results in a different or random order.
    """
    records = ["cat", "dog", "fish", "planet"]  # dog is close to cat; fish/planet far
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=4)
    scores = [r.score for r in results]
    assert scores == sorted(scores, reverse=True), (
        f"Results must be sorted by score descending; got scores={scores}"
    )


def test_second_closest_ranks_second() -> None:
    """The second-most-similar record ranks second.

    dog is closest to cat (angle ~ 24 deg), fish is orthogonal.
    Kills an impl that only correctly handles the top-1 case.
    """
    records = ["cat", "dog", "fish"]
    idx = LocalStorageIndex(records, encoder=_stub_encoder)
    results = idx.query("cat", k=2)
    record_names = [r.record for r in results]
    assert record_names[0] == "cat", f"top hit must be 'cat'; got {record_names}"
    assert record_names[1] == "dog", (
        f"second hit must be 'dog' (closest after cat); got {record_names}"
    )
