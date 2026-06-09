"""Discriminating tests for novelty_density (backlog item 95, 2026-06-08).

`novelty_density(items, corpus, *, encoder, novelty_threshold)` = the fraction of items whose MAX
geometric correspondence to the corpus is BELOW the threshold (geometrically novel) vs at/above
(routine — the loop near-duplicating). A self-monitor over the loop's own output. Report-only, pure
over an injected encoder.

Each test fails a plausible wrong impl:
  - an impl that flips the split (>= novel) → test_duplicate_batch_low / test_distinct_batch_high,
  - an impl that miscounts an item already in the corpus → test_item_in_corpus_is_routine,
  - an impl that ZeroDivisions on empty items → test_empty_items_zero,
  - an impl with the wrong threshold comparison → test_threshold_split.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.geometric_correspondence import novelty_density


def _by_first_char(text: str) -> np.ndarray:
    # 'a*' → [1,0]; 'b*' → [0,1] (orthogonal groups: a-vs-a cosine 1, a-vs-b cosine 0).
    return np.array([1.0, 0.0]) if text.startswith("a") else np.array([0.0, 1.0])


_CORPUS = [{"text": "a_prior", "ref": "r1"}]  # the corpus lives in group 'a'


def test_duplicate_batch_low_novelty() -> None:
    # Items all in group 'a' (≈ corpus) → correspondence ≈ 1.0 ≥ 0.5 → routine → density 0.0.
    out = novelty_density(
        ["a1", "a2", "a3"], _CORPUS, encoder=_by_first_char, novelty_threshold=0.5
    )
    assert out == 0.0


def test_distinct_batch_high_novelty() -> None:
    # Items in group 'b' (orthogonal to corpus 'a') → correspondence 0.0 < 0.5 → novel → density 1.0.
    out = novelty_density(["b1", "b2"], _CORPUS, encoder=_by_first_char, novelty_threshold=0.5)
    assert out == 1.0


def test_mixed_batch_half() -> None:
    out = novelty_density(["a1", "b1"], _CORPUS, encoder=_by_first_char, novelty_threshold=0.5)
    assert out == 0.5  # one routine ('a'), one novel ('b')


def test_item_in_corpus_is_routine() -> None:
    # DISCRIMINATING: an item whose text IS a corpus text → correspondence ≈ 1.0 ≥ threshold →
    # counted ROUTINE, not novel. An impl that flips the split would call it novel.
    out = novelty_density(["a_prior"], _CORPUS, encoder=_by_first_char, novelty_threshold=0.5)
    assert out == 0.0


def test_threshold_split() -> None:
    # DISCRIMINATING: a partial encoder gives max correspondence 0.8 (cos([1,0.5],[0.5,1])). With
    # threshold 0.7 → 0.8 >= 0.7 → routine (density 0); with 0.9 → 0.8 < 0.9 → novel (density 1).
    def _partial(text: str) -> np.ndarray:
        return np.array([1.0, 0.5]) if text.startswith("a") else np.array([0.5, 1.0])

    corpus = [{"text": "a_prior", "ref": "r"}]
    assert novelty_density(["b1"], corpus, encoder=_partial, novelty_threshold=0.7) == 0.0
    assert novelty_density(["b1"], corpus, encoder=_partial, novelty_threshold=0.9) == 1.0


def test_empty_items_zero() -> None:
    assert novelty_density([], _CORPUS, encoder=_by_first_char, novelty_threshold=0.5) == 0.0


def test_empty_corpus_all_novel() -> None:
    # No prior work → nothing to resemble → every item novel → density 1.0.
    out = novelty_density(["a1", "b1"], [], encoder=_by_first_char, novelty_threshold=0.5)
    assert out == 1.0


def test_corpus_generator_not_exhausted() -> None:
    # DISCRIMINATING: corpus may be a one-shot generator reused across items. An impl that does not
    # materialize it would see an empty corpus for items 2+ → wrong (all novel).
    gen = (c for c in [{"text": "a_prior", "ref": "r"}])
    out = novelty_density(["a1", "a2"], gen, encoder=_by_first_char, novelty_threshold=0.5)
    assert out == 0.0  # both routine — corpus seen for BOTH items
