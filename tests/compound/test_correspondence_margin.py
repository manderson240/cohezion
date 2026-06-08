"""Discriminating tests for correspondence_margin (backlog item 117, 2026-06-08).

`correspondence_margin(corpus, encoder)` is the quantified dual of item-68's boolean: it returns
`mean_intra - mean_inter`, the calibration confidence of the FLUME geometric substrate. Composes
item-68's intra/inter pairwise computation. Report-only, pure over an injected encoder.

Each test fails a plausible wrong impl:
  - an impl that returns the BOOLEAN (item 68) not the margin → test_perfect/partial (a bool != a float),
  - an impl that returns mean_inter - mean_intra (sign flipped) → test_partial_margin_positive,
  - an impl that crashes / returns nonzero on a vacuous corpus → test_vacuous_* ,
  - an impl that does not compose the same intra/inter split → test_degenerate_zero_margin.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.geometric_correspondence import correspondence_margin


def _by_first_char(text: str) -> np.ndarray:
    # Perfect separator: every 'a*' text → [1,0]; every 'b*' text → [0,1] (orthogonal groups).
    return np.array([1.0, 0.0]) if text.startswith("a") else np.array([0.0, 1.0])


def _degenerate(_text: str) -> np.ndarray:
    # Maps EVERY text to the same vector → intra == inter.
    return np.array([1.0, 1.0])


def _partial(text: str) -> np.ndarray:
    # Group 'a' → [1, 0.5], group 'b' → [0.5, 1]: intra cos == 1, inter cos == 0.8 → margin 0.2.
    return np.array([1.0, 0.5]) if text.startswith("a") else np.array([0.5, 1.0])


def test_perfect_separation_margin_near_one() -> None:
    corpus = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
    margin = correspondence_margin(corpus, _by_first_char)
    assert abs(margin - 1.0) < 1e-9  # intra 1.0 - inter 0.0
    assert isinstance(margin, float)


def test_degenerate_zero_margin() -> None:
    # DISCRIMINATING: intra == inter (everything one vector) → margin exactly 0.0.
    corpus = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
    assert correspondence_margin(corpus, _degenerate) == 0.0


def test_partial_margin_between_zero_and_one() -> None:
    # DISCRIMINATING (sign + magnitude): partially-discriminating encoder → 0 < margin < 1, and the
    # SIGN is intra - inter (positive). An impl returning inter - intra would be negative.
    corpus = {"A": ["a1", "a2"], "B": ["b1", "b2"]}
    margin = correspondence_margin(corpus, _partial)
    assert 0.0 < margin < 1.0
    assert abs(margin - 0.2) < 1e-9  # 1.0 - 0.8


def test_vacuous_single_item() -> None:
    assert correspondence_margin({"A": ["a1"]}, _by_first_char) == 0.0


def test_vacuous_single_group_no_inter() -> None:
    # Two items but ONE group → no cross pair → no inter → vacuous → 0.0.
    assert correspondence_margin({"A": ["a1", "a2"]}, _by_first_char) == 0.0


def test_vacuous_all_singletons_no_intra() -> None:
    # Each group has exactly one item → no within-group pair → no intra → vacuous → 0.0.
    assert correspondence_margin({"A": ["a1"], "B": ["b1"]}, _by_first_char) == 0.0


def test_empty_corpus() -> None:
    assert correspondence_margin({}, _by_first_char) == 0.0
