"""Unit tests for Ollama Cloud Model Monadic Stack (OllamaCloudMonad)."""

from unittest.mock import MagicMock, patch
import pytest

from cohezion.agi.ollama_cloud_monad import (
    Either,
    KaggleTrackState,
    MonadTraceStep,
    OllamaCloudMonad,
    autoharness_contract_guard_monad,
    extract_code_blocks,
    run_monadic_keep_on_track_pipeline,
    verify_ast,
)


def test_either_monad_laws() -> None:
    """Validate Category Theory Monad laws for Either."""
    # 1. Left identity: return a >>= f == f a
    val = 10
    f = lambda x: Either.right(x * 2)
    assert Either.right(val).bind(f).value == f(val).value

    # 2. Right identity: m >>= return == m
    m = Either.right(20)
    assert m.bind(Either.right).value == m.value

    # 3. Associativity: (m >>= f) >>= g == m >>= (\x -> f x >>= g)
    g = lambda x: Either.right(x + 5)
    lhs = m.bind(f).bind(g)
    rhs = m.bind(lambda x: f(x).bind(g))
    assert lhs.value == rhs.value

    # 4. Fail-closed Left short circuit
    err = Either.left("Fatal Invariant Failure")
    never_run = False
    def _fail_fn(x):
        nonlocal never_run
        never_run = True
        return Either.right(x)

    res = err.bind(_fail_fn)
    assert res.is_right is False
    assert res.error == "Fatal Invariant Failure"
    assert never_run is False


def test_ollama_cloud_monad_unit_and_bind() -> None:
    """Validate OllamaCloudMonad transformer pipeline composition."""
    initial_state = KaggleTrackState(
        competition_slug="arc-prize-2026-arc-agi-2",
        current_score=31.81,
        baseline_score=31.81,
    )

    monad = (
        OllamaCloudMonad.unit(100)
        .map(lambda x: x + 50)
        .bind(lambda x: OllamaCloudMonad.unit(f"Score: {x}"))
    )

    either_res, logs = monad.run(initial_state)
    assert either_res.is_right is True
    val, state = either_res.value
    assert val == "Score: 150"
    assert state.competition_slug == "arc-prize-2026-arc-agi-2"


def test_autoharness_contract_guard_monad() -> None:
    """Validate AutoHarness contract guard fails closed on illegal AST syntax."""
    state = KaggleTrackState(
        competition_slug="arc-prize-2026-arc-agi-3",
        current_score=0.25,
        baseline_score=0.25,
    )

    valid_patch = "def solve_arc():\n    return 42\n"
    invalid_patch = "def broken_syntax(:\n    return\n"

    guard = autoharness_contract_guard_monad()

    # Valid patch succeeds
    res_valid, logs1 = guard([valid_patch]).run(state)
    assert res_valid.is_right is True
    assert res_valid.value[0] is True
    assert any(log.ast_verified for log in logs1)

    # Invalid patch fails closed
    res_invalid, logs2 = guard([invalid_patch]).run(state)
    assert res_invalid.is_right is False
    assert "AutoHarness AST Violation" in res_invalid.error
    assert any(not log.ast_verified for log in logs2)


def test_poincare_autocontext_state_transitions() -> None:
    """Validate continuous 2048D Poincaré state updates and conformal factor."""
    state = KaggleTrackState(
        competition_slug="enveda-CASMI26-molecule-id-mass-spectra",
        current_score=0.335,
        baseline_score=0.328,
    )
    assert state.step_count == 0
    assert state.conformal_factor >= 2.0

    state.update_poincare("action_1_formula_gating")
    assert state.step_count == 1
    assert len(state.poincare_point.coords) == 2048
    assert state.conformal_factor > 0.0


@patch("cohezion.agi.ollama_cloud_monad.query_ollama_cloud_model")
def test_monadic_keep_on_track_pipeline_mocked(mock_query) -> None:
    """Validate full end-to-end keep-on-track pipeline execution."""
    mock_query.return_value = (
        "Trajectory ON_TRACK.\n```python\ndef patch_invariant(x):\n    return x + 1\n```",
        "Deep reasoning chain...",
        12.5,
    )

    either_res, trace = run_monadic_keep_on_track_pipeline(
        competition_slug="arc-prize-2026-arc-agi-3",
        current_score=0.25,
        baseline_score=0.25,
    )

    assert either_res.is_right is True
    success, state = either_res.value
    assert success is True
    assert len(trace) >= 5
    assert state.step_count >= 3
    assert len(state.actionable_patches) >= 1
    assert any("patch_invariant" in p for p in state.actionable_patches)
