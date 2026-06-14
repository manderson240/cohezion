"""Item 90 — LocalInferenceAgent: self-improving local-inference sub-agent.

Closes the experiential loop for the local-inference tier:

  1. Runs a task via the injected ``execute_fn`` (default: Triune NPU→iGPU→CPU via
     ``make_local_execute_fn`` — never cloud) and produces a text output.
  2. Evaluates the output with the injected ``evaluate_fn`` (default: AutoDQA).
  3. If ACCEPTED: deposits the outcome as a neuron via the injected ``deposit_fn``
     (default: real ``experiential_learning_hook`` deposit — gated by item-88 closure).
     Rejected outputs are NEVER deposited (AUTODQA I6 spirit; no sycophantic backdoor).
  4. Returns an ``AgentResult`` summarising the run.

All three callables are injectable (``execute_fn``, ``evaluate_fn``, ``deposit_fn``), which means
pytest never writes the real graph: tests supply deterministic stubs.  The production defaults
wire Triune local routing + AutoDQA + real neuron deposit — the behaviour-change from item 90.

Gate: only accepted outcomes reach ``deposit_fn``; the item-88 ``experiential_closure_report``
is used by callers to audit whether the deposit actually closed the loop (open-gap detection).
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cohezion.governance.experiential_closure import Outcome


@dataclass(frozen=True)
class AgentResult:
    """Summary of one LocalInferenceAgent.run() call.

    Attributes
    ----------
    task:
        The task string passed to the agent.
    output:
        The text produced by ``execute_fn``.
    accepted:
        ``True`` if ``evaluate_fn`` accepted the output; ``False`` if rejected.
    """

    task: str
    output: str
    accepted: bool


def _default_execute_fn(task: str) -> str:
    """Production default: route the task through the local Triune orchestrator.

    Lazy-imported to avoid loading heavy inference deps at module import time
    (required for fast pytest collection — CLAUDE.md import-time-error rule).
    """
    try:
        from cohezion.compound.local_inference import make_local_execute_fn

        fn = make_local_execute_fn(task)
        import asyncio

        return asyncio.run(fn(task))
    except Exception:  # pragma: no cover — only fires when lemonade is offline
        return ""


def _default_evaluate_fn(output: str, task: str) -> bool:
    """Production default: AutoDQA evaluation (HIHO-calibrated quality gate)."""
    try:
        from cohezion.compound.autodqa import AutoDQA

        dqa = AutoDQA(persist=False, notify_on_reject=False)
        result = dqa.evaluate(output, task)
        return result.verdict.accept
    except Exception:  # pragma: no cover — AutoDQA import failure → reject (safe default)
        return False


def _default_deposit_fn(outcome: Outcome) -> None:  # pragma: no cover
    """Production default: deposit accepted outcome via the experiential learning hook.

    No-op in tests (never called for rejected outcomes; callers inject stubs).
    The real implementation writes to SurrealDB via the experiential_learning_hook.
    This is the gated behaviour-change from item 90 — it only runs in production
    when the caller doesn't override ``deposit_fn``.
    """
    try:
        from cohezion.skills.experiential_learning_hook import deposit_outcome

        deposit_outcome(outcome.key, accepted=outcome.accepted)
    except (ImportError, AttributeError, RuntimeError):
        pass  # hook not yet wired — silently skip (additive-first: no crash on missing hook)


class LocalInferenceAgent:
    """Self-improving local-inference sub-agent (item 90).

    Runs a task through the local Triune tier, evaluates with AutoDQA, and deposits
    ACCEPTED outcomes as neurons (closing the experiential loop). Rejected outcomes
    are NEVER deposited (AUTODQA I6 spirit).

    All three production seams are injectable for testing:

    Parameters
    ----------
    execute_fn:
        ``(task: str) -> str`` — produces the output to evaluate.
        Default: ``make_local_execute_fn`` (Triune NPU→iGPU→CPU, never cloud).
    evaluate_fn:
        ``(output: str, task: str) -> bool`` — True = accepted, False = rejected.
        Default: AutoDQA HIHO-calibrated quality gate.
    deposit_fn:
        ``(outcome: Outcome) -> None`` — persists an ACCEPTED outcome as a neuron.
        Default: real experiential_learning_hook deposit (gated behaviour-change).
        Pytest callers pass a ``list.append`` or no-op lambda — never writes real graph.
    """

    def __init__(
        self,
        *,
        execute_fn: Callable[[str], str] | None = None,
        evaluate_fn: Callable[[str, str], bool] | None = None,
        deposit_fn: Callable[[Outcome], None] | None = None,
    ) -> None:
        self._execute_fn = execute_fn or _default_execute_fn
        self._evaluate_fn = evaluate_fn or _default_evaluate_fn
        self._deposit_fn = deposit_fn or _default_deposit_fn

    def run(self, task: str) -> AgentResult:
        """Execute the task through the local tier and deposit if accepted.

        Args:
            task: The task description string (becomes ``Outcome.key`` if accepted).

        Returns:
            :class:`AgentResult` with task, output, and verdict.
        """
        output = self._execute_fn(task)
        accepted = self._evaluate_fn(output, task)

        if accepted:
            # Deposit the accepted outcome — I6 spirit: only accepted outcomes may become neurons.
            outcome = Outcome(key=task, accepted=True)
            self._deposit_fn(outcome)

        return AgentResult(task=task, output=output, accepted=accepted)
