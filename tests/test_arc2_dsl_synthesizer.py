"""Unit tests for ARC-AGI-2 Neuro-Symbolic DSL Program Synthesizer."""

import pytest
from cohezion.agi.arc2_dsl_synthesizer import ARCDSLSynthesizer


def test_d4_rotation_synthesis():
    synth = ARCDSLSynthesizer()
    train_pairs = [
        ([[1, 2], [3, 4]], [[3, 1], [4, 2]]),  # 90 deg rotation clockwise
        ([[5, 6], [7, 8]], [[7, 5], [8, 6]]),
    ]
    prog = synth.synthesize(train_pairs)
    assert prog is not None
    test_in = [[9, 0], [1, 2]]
    expected = [[1, 9], [2, 0]]
    assert prog(test_in) == expected


def test_color_substitution_synthesis():
    synth = ARCDSLSynthesizer()
    train_pairs = [
        ([[1, 2], [2, 1]], [[3, 4], [4, 3]]),  # 1->3, 2->4
        ([[2, 1], [1, 2]], [[4, 3], [3, 4]]),
    ]
    prog = synth.synthesize(train_pairs)
    assert prog is not None
    test_in = [[1, 1], [2, 2]]
    expected = [[3, 3], [4, 4]]
    assert prog(test_in) == expected


def test_bounding_box_cropping():
    synth = ARCDSLSynthesizer()
    train_pairs = [
        ([[0, 0, 0], [0, 1, 0], [0, 0, 0]], [[1]]),
        ([[0, 2, 2], [0, 2, 2], [0, 0, 0]], [[2, 2], [2, 2]]),
    ]
    prog = synth.synthesize(train_pairs)
    assert prog is not None
    test_in = [[0, 0, 0, 0], [0, 3, 3, 0], [0, 3, 3, 0], [0, 0, 0, 0]]
    expected = [[3, 3], [3, 3]]
    assert prog(test_in) == expected


def test_scaling_synthesis():
    synth = ARCDSLSynthesizer()
    train_pairs = [
        ([[1, 2], [3, 4]], [[1, 1, 2, 2], [1, 1, 2, 2], [3, 3, 4, 4], [3, 3, 4, 4]]),
    ]
    prog = synth.synthesize(train_pairs)
    assert prog is not None
    test_in = [[5]]
    expected = [[5, 5], [5, 5]]
    assert prog(test_in) == expected


def test_unsolvable_returns_none():
    synth = ARCDSLSynthesizer()
    # Inconsistent random mapping
    train_pairs = [
        ([[1]], [[2]]),
        ([[1]], [[3]]),
    ]
    prog = synth.synthesize(train_pairs)
    assert prog is None
