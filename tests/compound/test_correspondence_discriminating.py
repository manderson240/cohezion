"""Discriminating tests for the correspondence self-check (item 68, 2026-06-06).

`correspondence_is_discriminating(corpus, encoder)` is a metacognitive calibration check on the FLUME
geometric substrate (validates item 66 is useful, not noise): True iff (a) every item's
self-correspondence ≈ 1.0 AND (b) related pairs (same group) score higher than unrelated pairs
(different group). `corpus` is a `dict[group -> list[str]]`.

Each test fails a plausible wrong impl:
  - a degenerate encoder (everything → one vector) passes → test_no_discrimination_is_false,
  - a real discriminating encoder fails → test_discriminating_encoder_is_true,
  - a zero-vector encoder (self-corr undefined) passes → test_zero_encoder_is_false,
  - empty/single corpus crashes instead of vacuous-True → test_vacuous_true.
"""

from __future__ import annotations

import numpy as np

from cohezion.compound.geometric_correspondence import correspondence_is_discriminating


_AXES = {"a": np.array([1.0, 0.0, 0.0]), "b": np.array([0.0, 1.0, 0.0])}


def _discriminating(text: str) -> np.ndarray:
    # "group:item" → the group's axis (same group → same direction; different → orthogonal).
    return _AXES[text.split(":")[0]]


def _degenerate(_text: str) -> np.ndarray:
    return np.array([1.0, 1.0, 1.0])  # everything → one vector: self≈1 but no discrimination


def _zero(_text: str) -> np.ndarray:
    return np.array([0.0, 0.0, 0.0])  # self-correspondence undefined → not ≈1.0


_CORPUS = {"a": ["a:1", "a:2"], "b": ["b:1", "b:2"]}


def test_discriminating_encoder_is_true() -> None:
    assert correspondence_is_discriminating(_CORPUS, _discriminating) is True


def test_no_discrimination_is_false() -> None:
    # self≈1 for all, but intra == inter == 1 → NOT discriminating.
    assert correspondence_is_discriminating(_CORPUS, _degenerate) is False


def test_zero_encoder_is_false() -> None:
    assert correspondence_is_discriminating(_CORPUS, _zero) is False


def test_vacuous_true() -> None:
    assert correspondence_is_discriminating({}, _discriminating) is True
    assert correspondence_is_discriminating({"a": ["a:1"]}, _discriminating) is True  # <2 items
