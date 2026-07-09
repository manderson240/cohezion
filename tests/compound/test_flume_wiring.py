"""TDD tests for SkillStateEncoder wiring in CompoundExecutor (Task #25).

V-Model level: AD (Architecture Design) — integration between CompoundExecutor
post-execution path and SkillStateEncoder FLUME encoding.

V-Model contracts:
  AD1: CompoundExecutor instantiates _skill_state_encoder on __init__
  AD2: _skill_state_encoder is a SkillStateEncoder (or None when import fails)
  AD3: CompoundExecutor exposes _flume_encode_skill_state() helper
  AD4: _flume_encode_skill_state returns np.ndarray(256,) float32 when encoder present
  AD5: _flume_encode_skill_state returns None when _skill_state_encoder is None
  AD6: _flume_encode_skill_state is fail-open (exceptions → None, no raise)
  AD7: with verdict kwarg, _flume_encode_skill_state routes to encode_rubric_verdict
  AD8: without verdict kwarg, routes to encode_skill
"""

from __future__ import annotations

from unittest.mock import MagicMock

import numpy as np
import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.rubric_middleware import RubricVerdict
from cohezion.flume.skill_state_encoder import SkillStateEncoder


def _make_executor() -> CompoundExecutor:
    return CompoundExecutor(
        mcp_client=None,
        skill_refiner=MagicMock(),
        enable_skill_refinement=False,
        enable_guardrails=False,
    )


# ── AD1/AD2: _skill_state_encoder attribute ───────────────────────────────────


def test_executor_has_skill_state_encoder_attribute():
    ex = _make_executor()
    assert hasattr(ex, "_skill_state_encoder"), "_skill_state_encoder attribute missing"


def test_executor_skill_state_encoder_is_encoder_instance():
    ex = _make_executor()
    assert ex._skill_state_encoder is None or isinstance(
        ex._skill_state_encoder, SkillStateEncoder
    ), "_skill_state_encoder must be SkillStateEncoder or None"


# ── AD3: method exists ────────────────────────────────────────────────────────


def test_executor_has_flume_encode_skill_state_method():
    ex = _make_executor()
    assert hasattr(ex, "_flume_encode_skill_state"), "_flume_encode_skill_state missing"
    assert callable(ex._flume_encode_skill_state)


# ── AD4: returns 256D float32 when encoder is present ────────────────────────


def test_flume_encode_skill_state_returns_256d_float32():
    ex = _make_executor()
    if ex._skill_state_encoder is None:
        pytest.skip("SkillStateEncoder not available")
    result = ex._flume_encode_skill_state("test_skill", mgpo_weight=0.8, success_rate=0.5)
    assert isinstance(result, np.ndarray), "Must return np.ndarray"
    assert result.shape == (256,), f"Must be 256D, got {result.shape}"
    assert result.dtype == np.float32, f"Must be float32, got {result.dtype}"


# ── AD5: returns None when encoder is absent ─────────────────────────────────


def test_flume_encode_skill_state_returns_none_when_no_encoder():
    ex = _make_executor()
    ex._skill_state_encoder = None
    result = ex._flume_encode_skill_state("test_skill", mgpo_weight=0.8, success_rate=0.5)
    assert result is None


# ── AD6: fail-open ────────────────────────────────────────────────────────────


def test_flume_encode_skill_state_is_fail_open():
    ex = _make_executor()
    broken_encoder = MagicMock()
    broken_encoder.encode_skill.side_effect = RuntimeError("encoding exploded")
    ex._skill_state_encoder = broken_encoder
    result = ex._flume_encode_skill_state("test_skill", mgpo_weight=0.5, success_rate=0.5)
    assert result is None, "Must return None on exception (fail-open)"


# ── AD7/AD8: verdict routing ──────────────────────────────────────────────────


def test_with_verdict_routes_to_encode_rubric_verdict():
    ex = _make_executor()
    mock_encoder = MagicMock(spec=SkillStateEncoder)
    mock_encoder.encode_rubric_verdict.return_value = np.zeros(256, dtype=np.float32)
    ex._skill_state_encoder = mock_encoder

    verdict = RubricVerdict(passed=True, reason="ok")
    ex._flume_encode_skill_state("skill", mgpo_weight=0.5, success_rate=0.5, verdict=verdict)

    mock_encoder.encode_rubric_verdict.assert_called_once()
    mock_encoder.encode_skill.assert_not_called()


def test_without_verdict_routes_to_encode_skill():
    ex = _make_executor()
    mock_encoder = MagicMock(spec=SkillStateEncoder)
    mock_encoder.encode_skill.return_value = np.zeros(256, dtype=np.float32)
    ex._skill_state_encoder = mock_encoder

    ex._flume_encode_skill_state("skill", mgpo_weight=0.5, success_rate=0.5)

    mock_encoder.encode_skill.assert_called_once()
    mock_encoder.encode_rubric_verdict.assert_not_called()


# ── AD9: ExecutorFactory-produced executor has _skill_state_encoder set ────────


def test_executor_factory_produces_executor_with_skill_state_encoder():
    """Structural check: ExecutorFactory.create() executor has _skill_state_encoder wired.

    SkillStateEncoder is auto-created inside CompoundExecutor.__init__ (try/import),
    so the factory inherits it transitively without needing to pass it as a kwarg.
    This test verifies the end-to-end wiring is intact.
    """
    from unittest.mock import MagicMock

    from cohezion.compound.executor_factory import ExecutorFactory

    ex = ExecutorFactory.create(
        mcp_client=None,
        skill_refiner=MagicMock(),
        enable_skill_refinement=False,
        enable_guardrails=False,
    )
    assert hasattr(ex, "_skill_state_encoder"), (
        "ExecutorFactory-produced executor must have _skill_state_encoder attribute"
    )
    assert ex._skill_state_encoder is None or isinstance(
        ex._skill_state_encoder, SkillStateEncoder
    ), "_skill_state_encoder must be SkillStateEncoder or None (import guard)"
