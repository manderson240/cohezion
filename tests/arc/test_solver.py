"""Unit tests for ARC solver — V-Model Phase 6."""

import numpy as np

from cohezion.arc.solver import _score_chain, beam_search
from cohezion.arc.transforms import (
    apply_chain,
    flip_horizontal,
    gravity_fall,
    rotate_90,
    rotate_180,
)


def test_rotate_identity():
    g = np.array([[1, 2], [3, 4]])
    r = rotate_90(g)
    assert r is not None
    assert np.array_equal(rotate_90(r), rotate_180(g))


def test_flip_twice_identity():
    g = np.array([[1, 2], [3, 4]])
    assert np.array_equal(flip_horizontal(flip_horizontal(g)), g)


def test_gravity_simple():
    g = np.array([[1, 0], [0, 2]])
    out = gravity_fall(g)
    expected = np.array([[0, 0], [1, 2]])
    assert np.array_equal(out, expected), f"got {out}"


def test_chain_apply():
    g = np.array([[1, 2], [3, 4]])
    out = apply_chain(g, ["rotate_90", "flip_horizontal"])
    assert out is not None


def test_score_chain_perfect():
    # Use case where ONLY gravity_fall matches (rotate_90 does not)
    train = [{"input": np.array([[1, 0], [0, 2]]), "output": np.array([[0, 0], [1, 2]])}]
    score = _score_chain(["gravity_fall"], train)
    assert score == 1.0


def test_beam_finds_solution():
    train = [{"input": np.array([[1, 0], [0, 2]]), "output": np.array([[0, 0], [1, 2]])}]
    chain = beam_search(train, max_depth=1, beam_width=20, time_budget_sec=5.0)
    assert "gravity_fall" in chain
