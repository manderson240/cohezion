r"""Unit tests for Kaggle AGI AutoHarness Synthesis Engine (arXiv:2603.03329v1)"""

from __future__ import annotations

import time

from cohezion.agi.kaggle_autoharness import (
    AIMOProofState,
    ARCGridInvariant,
    KaggleAutoHarness,
)


def test_arc_transformation_verification_pass():
    harness = KaggleAutoHarness()
    input_grid = [[1, 0], [0, 1]]
    output_grid = [[0, 1], [1, 0]]

    result = harness.verify_arc_transformation(input_grid, output_grid)
    assert result.valid is True
    assert result.bypassed_llm is True
    assert result.verification_score == 1.0
    assert result.execution_time_ms < 1.0


def test_arc_transformation_color_violation():
    harness = KaggleAutoHarness()
    input_grid = [[1, 0], [0, 1]]
    output_grid = [[0, 7], [1, 0]]  # Color 7 is not in input grid

    result = harness.verify_arc_transformation(input_grid, output_grid)
    assert result.valid is False
    assert result.bypassed_llm is True
    assert "Color preservation violation" in result.reason


def test_arc_transformation_dimension_exceeded():
    harness = KaggleAutoHarness()
    input_grid = [[1, 0], [0, 1]]
    output_grid = [[0] * 35 for _ in range(35)]  # Exceeds max dim 30

    spec = ARCGridInvariant(max_grid_dim=30)
    result = harness.verify_arc_transformation(input_grid, output_grid, spec=spec)
    assert result.valid is False
    assert "exceed max limit" in result.reason


def test_aimo_proof_state_verification_pass():
    harness = KaggleAutoHarness()
    state = AIMOProofState(value=500, min_bound=0, max_bound=999, modulo_base=10, modulo_target=0)

    result = harness.verify_aimo_proof_state(state)
    assert result.valid is True
    assert result.bypassed_llm is True
    assert result.verification_score == 1.0


def test_aimo_proof_state_out_of_range():
    harness = KaggleAutoHarness()
    state = AIMOProofState(value=1050, min_bound=0, max_bound=999)

    result = harness.verify_aimo_proof_state(state)
    assert result.valid is False
    assert "Range bounds violation" in result.reason


def test_aimo_proof_state_integer_sanity_fractional_float():
    harness = KaggleAutoHarness()
    state = AIMOProofState(value=42.7, require_integer=True)

    result = harness.verify_aimo_proof_state(state)
    assert result.valid is False
    assert "Integer sanity failure" in result.reason


def test_aimo_proof_state_modulo_violation():
    harness = KaggleAutoHarness()
    state = AIMOProofState(value=105, modulo_base=10, modulo_target=2)

    result = harness.verify_aimo_proof_state(state)
    assert result.valid is False
    assert "Modulo constraint violation" in result.reason


def test_ast_bytecode_verifier_latency():
    harness = KaggleAutoHarness()
    verifier = harness.synthesize_ast_bytecode_verifier(
        "speed_test", "state['x'] >= 0 and state['x'] <= 999"
    )

    state = {"x": 42}
    t0 = time.perf_counter()
    for _ in range(100):
        assert verifier(state) is True
    dt_ms = (time.perf_counter() - t0) * 1000.0

    # 100 runs should take less than 1.0 ms total (< 10 us per run)
    assert dt_ms < 1.0
