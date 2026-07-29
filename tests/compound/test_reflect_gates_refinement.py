"""REFLECT must actually SUPPRESS a refinement — not merely be present (2026-07-29).

`test_reflect_wiring.py` proves a RetrospectionEngine is wired into a live executor. That is
necessary and NOT sufficient: it would still pass against an executor that computes
`should_refine` and never gates on it — a computed-but-unconsumed value, which is the exact
dormancy class this codebase keeps finding. These tests close that gap.

THE FAPO TRAP (why a failing task cannot be used):
`should_refine` gates ONLY the success path (executor.py:1511
`if success and self.skill_refiner and should_refine:`). On failure, the FAPO path at
executor.py:1546 calls `refine()` ANYWAY, deliberately and independently of `should_refine`.
So suppression MUST be demonstrated on a SUCCESSFUL execution. An existing test,
`test_retrospection_live.py::test_retrospection_gates_refinement_on_failure`, gets this wrong —
it asserts no-refine on failure, encoding the pre-FAPO contract, and is red for that reason.
Filed to the kanban as a CONTRACT decision, not a bug to green.

Authored by delegated review (glm-5.2 via Ollama Cloud) and verified against source here; the
delegated draft imported `src.compound.executor`, which does not exist.
"""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from cohezion.compound.executor import CompoundExecutor


class _StubRetrospectionEngine:
    """Retrospection engine whose verdict is fixed at construction.

    Stubbed rather than real so the test controls `should_refine` directly — a real engine's
    verdict depends on heuristics we are not testing here.
    """

    def __init__(self, should_refine: bool):
        self._should_refine = should_refine

    def analyze_execution_result(self, execution_result, skill_name=""):
        return {
            "should_refine": self._should_refine,
            "insights": ["stub insight"],
            "compound_score": 0.0,
        }


def _build(should_refine: bool):
    refiner = MagicMock()
    refiner.refine = MagicMock(return_value=None)
    executor = CompoundExecutor(
        MagicMock(),
        enable_guardrails=False,
        skill_refiner=refiner,
        enable_skill_refinement=True,
        retrospection_engine=_StubRetrospectionEngine(should_refine),
    )
    return executor, refiner


def _run(executor):
    return executor.execute_task(
        task_description="succeeds",
        skill_name="test",
        operation_type="generate",
        # MUST return a (output, metrics) TUPLE. execute_task does
        # `output, metrics = _call_execute_fn(...)` with no shape validation, so a bare
        # 2-character string like "ok" silently unpacks to output='o', metrics='k' and then
        # crashes 11 lines later at `metrics.update(...)` with
        # "'str' object has no attribute 'update'" — an error pointing nowhere near the cause.
        # Filed separately; do not "fix" it by loosening this test.
        execute_fn=lambda guidance: ("ok", {}),
    )


class TestReflectGatesRefinement:
    def test_should_refine_false_suppresses_refinement(self):
        """DISCRIMINATING: fails against an executor that computes should_refine but
        never gates on it. Execution SUCCEEDS, so the FAPO failure path is not involved."""
        executor, refiner = _build(should_refine=False)
        _run(executor)
        assert refiner.refine.call_count == 0, (
            "REFLECT returned should_refine=False on a SUCCESSFUL execution but refine() was "
            "still invoked — the gate value is computed and unconsumed."
        )

    def test_should_refine_true_permits_refinement(self):
        """POSITIVE CONTROL. Without this, the suppression test cannot distinguish
        'gating works' from 'refine never runs at all' — which would pass trivially."""
        executor, refiner = _build(should_refine=True)
        _run(executor)
        assert refiner.refine.call_count >= 1, (
            "Positive control failed: should_refine=True on a successful execution yet "
            "refine() was never invoked — the suppression test above proves nothing."
        )


if __name__ == "__main__":
    pytest.main([__file__, "-q"])
