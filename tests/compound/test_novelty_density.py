"""Discriminating tests for loop novelty-density (item 95, 2026-06-07).

`novelty_density(items, corpus, *, encoder, novelty_threshold)` returns the fraction of
`items` whose max cosine similarity to `corpus` is BELOW `novelty_threshold` (= novel/dense).
Items at or above the threshold are ROUTINE (near-duplicates).

Each test fails a plausible wrong impl:
  - reports 1.0 for exact duplicates of corpus → test_near_duplicates_low_density,
  - uses > instead of >= for the boundary → test_exact_threshold_is_routine,
  - divides by len(corpus) instead of len(items) → test_denominator_is_items_not_corpus,
  - no empty-items guard → test_empty_items_zero,
  - treats empty corpus as routine (max_score=0 ≥ threshold) → test_empty_corpus_all_novel,
  - wrong threshold direction → test_distinct_items_high_density.

Uses stub encoders: no model load under pytest.
"""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.compound.geometric_correspondence import novelty_density

# ---------------------------------------------------------------------------
# Stub encoders — deterministic, zero model weight
# ---------------------------------------------------------------------------


def _identity_encoder(text: str) -> np.ndarray:
    """All texts map to the SAME unit vector → cosine=1 with everything."""
    return np.array([1.0, 0.0, 0.0])


def _orthogonal_encoder(text: str) -> np.ndarray:
    """Each text maps to a unique orthogonal vector by hash → cosine≈0 between different texts."""
    # Simple hash → unique direction: bucket into one of N axes
    idx = hash(text) % 64
    v = np.zeros(64)
    v[idx] = 1.0
    return v


def _constant_low_encoder(text: str) -> np.ndarray:
    """All texts map to a vector that is near-orthogonal to the corpus vector."""
    # item texts → [0,1,0], corpus texts → [1,0,0] → cosine=0
    if text.startswith("corpus"):
        return np.array([1.0, 0.0, 0.0])
    return np.array([0.0, 1.0, 0.0])


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _corpus(*texts: str) -> list[dict]:
    return [{"text": t, "ref": f"ref-{i}"} for i, t in enumerate(texts)]


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_near_duplicates_low_density() -> None:
    """Items identical to corpus → max_score=1.0 ≥ threshold → ALL routine → density=0.0."""
    corp = _corpus("alpha", "beta", "gamma")
    items = ["alpha", "beta"]  # exact corpus text; identity encoder → cosine=1 with all
    # ANY encoder where these items score ≥ threshold with corpus → routine
    result = novelty_density(items, corp, encoder=_identity_encoder, novelty_threshold=0.5)
    assert result == 0.0, f"expected 0.0, got {result}"


def test_distinct_items_high_density() -> None:
    """Items orthogonal to corpus → max_score≈0 < threshold → ALL novel → density=1.0."""
    corp = _corpus("corpus_a", "corpus_b")
    items = ["item_x", "item_y"]  # orthogonal to corpus texts by _orthogonal_encoder
    result = novelty_density(items, corp, encoder=_orthogonal_encoder, novelty_threshold=0.5)
    assert result == 1.0, f"expected 1.0, got {result}"


def test_exact_threshold_is_routine() -> None:
    """A max_score == threshold is ROUTINE (not novel): the cut is strictly BELOW threshold.

    Kills an impl that uses `max_score <= novelty_threshold` (novel would include threshold).
    """
    # _identity_encoder → cosine=1 between any two texts; threshold=1.0 exactly
    corp = _corpus("anything")
    items = ["anything"]
    result = novelty_density(items, corp, encoder=_identity_encoder, novelty_threshold=1.0)
    assert result == 0.0, f"threshold=1.0 with cosine=1 → routine, not novel, got {result}"


def test_threshold_zero_all_novel_unless_corpus_empty() -> None:
    """threshold=0.0 → every score (including 0) is NOT below the threshold → all routine.

    Kills an impl where 'novel' means >= threshold instead of < threshold.
    """
    corp = _corpus("corpus_item")
    items = ["something_orthogonal"]
    # _orthogonal_encoder gives cosine=0 for these distinct texts; 0 is NOT < 0.0 → routine
    result = novelty_density(items, corp, encoder=_orthogonal_encoder, novelty_threshold=0.0)
    assert result == 0.0, f"threshold=0 → score=0 is not strictly below → routine, got {result}"


def test_empty_items_zero() -> None:
    """Empty items → 0.0 (no ZeroDivision)."""
    corp = _corpus("alpha", "beta")
    result = novelty_density([], corp, encoder=_identity_encoder)
    assert result == 0.0


def test_empty_corpus_all_novel() -> None:
    """Empty corpus → max_score=0.0 for all items → all NOVEL (no prior matches exist)."""
    # With threshold=0.5 and max_score=0, 0 < 0.5 → novel
    result = novelty_density(["a", "b", "c"], [], encoder=_identity_encoder, novelty_threshold=0.5)
    assert result == 1.0, f"empty corpus → all novel, got {result}"


def test_denominator_is_items_not_corpus() -> None:
    """novelty_density denominator is len(items), NOT len(corpus).

    Kills an impl that divides by corpus size.
    """
    corp = _corpus("corpus_a", "corpus_b", "corpus_c", "corpus_d", "corpus_e")  # 5 corpus
    items = ["item_x", "item_y"]  # 2 items, both novel (orthogonal encoder)
    result = novelty_density(items, corp, encoder=_orthogonal_encoder, novelty_threshold=0.5)
    # 2 novel / 2 items = 1.0; wrong impl: 2 / 5 = 0.4
    assert result == 1.0, f"denominator must be items (2), not corpus (5); got {result}"


def test_mixed_novel_and_routine() -> None:
    """Half novel, half routine → density=0.5."""
    corp = _corpus("corpus_item")
    items = ["corpus_item", "novel_item"]
    # _constant_low_encoder: corpus_item → [1,0,0], novel_item → [0,1,0]
    # cosine(corpus_item, corpus_item) = 1.0 → routine (≥0.5)
    # cosine(novel_item, corpus_item) = 0.0 → novel (<0.5)
    result = novelty_density(items, corp, encoder=_constant_low_encoder, novelty_threshold=0.5)
    assert result == pytest.approx(0.5), f"expected 0.5, got {result}"
