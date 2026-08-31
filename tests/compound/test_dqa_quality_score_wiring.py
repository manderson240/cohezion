"""DQ1-DQ8: the output quality gate must actually reach DegradationDetector.

Dormancy this closes (found 2026-08-30 via `scripts/ci/dormancy_scan.py`, which
reports `quality_eval.evaluate` as "dormant ON THE PRODUCTION PATH"):

`DegradationDetector` owns a fully-written quality_score branch --
`MetricBaseline("quality_score", value_bounds=(0.0, 1.0))` at line 360, an
`add_sample` at 760, and a CRITICAL alert at 705 gated on `is_established`.
None of it can ever fire in production, because the chain is broken TWICE:

  1. NO PRODUCER. `make_local_execute_fn` -- the production `execute_fn` --
     returns 12 metric keys and `quality_score` is not one of them. Nothing else
     on the path writes it. `AutoDQA`, the only component in the tree that
     computes an output quality score, is never constructed by `make_executor`
     or `ExecutorFactory.create`.
  2. NO FORWARDING. Even a producer would not help: `executor.py:1661` builds
     `degradation_metrics` as a FRESH dict of 5 hardcoded keys and never merges
     `metrics` into it, so `quality_score` could not reach `check_degradation`.

A consumer-grep alone says "wired" here, because `DegradationDetector` really
does read `metrics["quality_score"]`. Only tracing the dict that is ACTUALLY
PASSED reveals the gap -- hence DQ4/DQ3 below assert on the passed dict and on
observable detector state, not on the presence of a symbol.

Design note pinned by DQ8: the gate is OBSERVABILITY + damping, never a hard
fail. Measured 2026-08-30 against the real `AutoDQA`: the correct answer "Paris"
to "What is the capital of France?" is REJECTED (`short_answer: too short (5
chars)`). Wiring rejection to `success = False` would fail correct work -- the
same defect AG1 records for the input guardrail, which blocked 4 of 7 legitimate
engineering tasks. `DegradationDetector` compares against a ROLLING baseline
(a drop to 80% of trend), so a systematically strict gate is still a valid
signal: it establishes a baseline at whatever absolute level and alerts on
RELATIVE degradation.
"""

from __future__ import annotations

import contextlib
import inspect
from typing import Any
from unittest.mock import MagicMock

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.executor import CompoundExecutor


# A code answer the real AutoDQA accepts with score 1.0 ("code: valid Python AST"),
# and a task description the classifier routes to output_type "code".
_GOOD_CODE = "def add(a, b):\n    return a + b"
_CODE_TASK = "Write a python function that adds two numbers"

# Same task type, unparseable -- real AutoDQA rejects with score 0.0.
_BAD_CODE = "def add(a b) return"


class _StubVerdict:
    def __init__(self, score: float, accept: bool) -> None:
        self.score = score
        self.accept = accept
        self.reason = "stub"


class _StubResult:
    def __init__(self, score: float, accept: bool) -> None:
        self.verdict = _StubVerdict(score, accept)
        self.quality_band = "ABOVE_HIHO" if score > 0.55 else "BELOW_HIHO"


class _StubGate:
    """Duck-typed AutoDQA returning a fixed verdict, recording its calls."""

    def __init__(self, score: float = 0.9, accept: bool = True) -> None:
        self._score = score
        self._accept = accept
        self.calls: list[tuple[str, str]] = []

    def evaluate(self, output: str, task_description: str, peer_outputs: Any = None) -> _StubResult:
        self.calls.append((output, task_description))
        return _StubResult(self._score, self._accept)


class _ExplodingGate:
    def evaluate(self, output: str, task_description: str, peer_outputs: Any = None) -> _StubResult:
        raise RuntimeError("simulated DQA failure")


def _executor(**kw: Any) -> CompoundExecutor:
    kw.setdefault("enable_guardrails", False)
    kw.setdefault("enable_skill_refinement", False)
    kw.setdefault("enable_alignment_analysis", False)
    return CompoundExecutor(mcp_client=MagicMock(), **kw)


def _run(executor: CompoundExecutor, task: str = _CODE_TASK, output: str = _GOOD_CODE) -> Any:
    from unittest.mock import patch

    def _fn(guidance: Any) -> tuple[str, dict[str, Any]]:
        return (output, {"coherence": 0.5})

    with (
        patch.object(executor.logger, "log_execution_start", return_value=""),
        patch.object(executor.logger, "log_execution_result"),
    ):
        return executor.execute_task(
            task_description=task,
            skill_name="test_skill",
            operation_type="generate",
            execute_fn=_fn,
        )


class TestDQ1Structural:
    def test_executor_accepts_dqa_gate_kwarg(self) -> None:
        assert "dqa_gate" in inspect.signature(CompoundExecutor.__init__).parameters

    def test_factory_accepts_dqa_gate_kwarg(self) -> None:
        from cohezion.compound.executor_factory import ExecutorFactory

        assert "dqa_gate" in inspect.signature(ExecutorFactory.create).parameters


class TestDQ2ScoreIsProduced:
    """The gate must be CALLED and its real score written to metrics."""

    def test_quality_score_present_when_gate_wired(self) -> None:
        gate = _StubGate(score=0.9)
        result = _run(_executor(dqa_gate=gate))
        assert gate.calls, "the wired gate was never invoked (accepted-but-not-called)"
        assert "quality_score" in result.metrics, (
            f"quality_score must be produced; got keys {sorted(result.metrics)}"
        )

    def test_score_tracks_the_gate_not_a_constant(self) -> None:
        """Discriminating: an impl writing a hardcoded default passes the test
        above but cannot make these two differ."""
        low = _run(_executor(dqa_gate=_StubGate(score=0.1))).metrics["quality_score"]
        high = _run(_executor(dqa_gate=_StubGate(score=0.9))).metrics["quality_score"]
        assert low < high, f"score must follow the gate's verdict, got {low} and {high}"

    def test_real_autodqa_discriminates_good_from_bad_output(self) -> None:
        """Same assertion against the REAL AutoDQA, not a stub.

        Test doubles camouflage dormancy -- a stub proves the plumbing carries a
        number, not that the number means anything.
        """
        from cohezion.compound.autodqa import AutoDQA

        good = _run(
            _executor(dqa_gate=AutoDQA(persist=False, notify_on_reject=False)),
            output=_GOOD_CODE,
        ).metrics["quality_score"]
        bad = _run(
            _executor(dqa_gate=AutoDQA(persist=False, notify_on_reject=False)),
            output=_BAD_CODE,
        ).metrics["quality_score"]
        assert good > bad, f"real AutoDQA must rank valid code above garbage: {good} vs {bad}"


class TestDQ3BaselineBecomesEstablished:
    """The strongest assertion: the detector's dead branch becomes reachable.

    Today `_baselines["quality_score"].is_established` is False forever, because
    nothing ever calls add_sample for it. min_samples is 5.
    """

    def test_quality_baseline_establishes_after_min_samples(self) -> None:
        detector = DegradationDetector()
        assert not detector._baselines["quality_score"].is_established, (
            "precondition: baseline starts unestablished"
        )

        executor = _executor(degradation_detector=detector, dqa_gate=_StubGate(score=0.8))
        for _ in range(6):
            with contextlib.suppress(Exception):
                _run(executor)

        assert detector._baselines["quality_score"].is_established, (
            "after 6 executions the quality_score baseline must be established -- "
            "otherwise the CRITICAL alert at degradation_detector.py:705 stays "
            "structurally unreachable in production"
        )


class TestDQ4ForwardedToDetector:
    def test_check_degradation_receives_quality_score(self) -> None:
        """Pins break #2: `degradation_metrics` is a fresh 5-key dict.

        Discriminating: an impl that writes metrics["quality_score"] but does not
        fold it into `degradation_metrics` passes DQ2 and fails here.
        """
        detector = MagicMock()
        detector.check_degradation.return_value = []
        with contextlib.suppress(Exception):
            _run(_executor(degradation_detector=detector, dqa_gate=_StubGate(score=0.7)))

        assert detector.check_degradation.called
        passed = detector.check_degradation.call_args[0][0]
        assert "quality_score" in passed, (
            f"quality_score must be folded into degradation_metrics; got {sorted(passed)}"
        )
        assert abs(passed["quality_score"] - 0.7) < 1e-9


class TestDQ5FailOpen:
    def test_gate_exception_does_not_break_the_task(self) -> None:
        result = _run(_executor(dqa_gate=_ExplodingGate()))
        assert result.success, "a failing DQA gate must never fail the task"
        assert result.output == _GOOD_CODE, "output must be untouched by a gate failure"


class TestDQ6BackwardCompatible:
    def test_no_gate_means_no_quality_score_key(self) -> None:
        """Existing callers must see byte-identical metrics.

        The prior revision is the oracle for the no-gate path
        (verification-depth.md): this change is claimed to be a pure addition, so
        the un-wired path must not gain a key.
        """
        result = _run(_executor())
        assert "quality_score" not in result.metrics


class TestDQ7FactoryAutoWires:
    def test_factory_auto_creates_a_gate(self) -> None:
        from cohezion.compound.executor_factory import ExecutorFactory

        executor = ExecutorFactory.create(
            mcp_client=MagicMock(),
            enable_guardrails=False,
            enable_skill_refinement=False,
        )
        assert getattr(executor, "_dqa_gate", None) is not None, (
            "ExecutorFactory.create must auto-create the DQA gate, mirroring the "
            "CB5 DegradationDetector auto-creation -- otherwise the production "
            "factory path stays dormant"
        )


class TestDQ8RejectionIsNonBlocking:
    """A reject must DAMP, never hard-fail. See the module docstring measurement."""

    def test_rejected_output_does_not_flip_success(self) -> None:
        result = _run(_executor(dqa_gate=_StubGate(score=0.0, accept=False)))
        assert result.success, (
            "a DQA rejection must not fail the task -- the real gate rejects the "
            "correct answer 'Paris' as too short, so hard-failing would break "
            "correct work (AG1 records the same defect for the input guardrail)"
        )
        assert result.output == _GOOD_CODE, "a rejection must not replace the output"

    def test_rejection_is_still_observable(self) -> None:
        """Non-blocking must not mean invisible -- the reject has to be recorded,
        or the gate is a no-op dressed as a gate."""
        result = _run(_executor(dqa_gate=_StubGate(score=0.0, accept=False)))
        assert result.metrics.get("dqa_rejected") is True
