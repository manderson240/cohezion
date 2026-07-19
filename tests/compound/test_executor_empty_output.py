"""Discriminating tests: empty local-inference output must NOT be scored as success (E1-S1).

The fleet's known failure mode is local inference silently emitting empty output. Before the
E1-S1 fix, ``CompoundExecutor.execute_task`` set ``success = True`` unconditionally on the happy
path; only a guardrail ``BLOCK`` ever flipped it, so an ``execute_fn`` returning ``("", {})`` was
scored as a healthy success and fed to anomaly/quality scoring as if nothing was wrong.

These tests exercise the real ``execute_task`` production path (not a hand-built stand-in) and are
discriminating: the wrong-but-plausible impl (unconditional ``success=True``) fails the empty and
whitespace cases, while an over-aggressive impl that flags everything degraded fails the positive
control.
"""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor


@pytest.fixture
def executor():
    """Minimal CompoundExecutor with vault logging patched out (matches existing suite)."""
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(MagicMock())


def _run(executor, output):
    """Drive execute_task with an execute_fn returning ``output`` and stubbed vault logging."""
    with (
        patch.object(
            executor.logger, "get_experience_guidance", return_value={"context": "test"}
        ),
        patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
        patch.object(executor.logger, "log_execution_result"),
        patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
    ):
        return executor.execute_task(
            task_description="t",
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda _guidance: (output, {}),
        )


def test_empty_output_is_not_scored_success(executor):
    """Empty output → success False and metrics['degraded'] True."""
    result = _run(executor, "")
    assert result.success is False
    assert result.metrics.get("degraded") is True


def test_whitespace_only_output_is_not_scored_success(executor):
    """Whitespace-only output is also degraded, not success."""
    result = _run(executor, "   \n\t ")
    assert result.success is False
    assert result.metrics.get("degraded") is True


def test_nonempty_output_still_scored_success(executor):
    """Positive control: real output remains a success with no degraded marker."""
    result = _run(executor, "real output")
    assert result.success is True
    assert result.metrics.get("degraded") is not True
