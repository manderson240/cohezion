"""Item 90: LocalInferenceAgent — self-improving local-inference sub-agent (TDD red→green).

Each test fails a plausible wrong implementation:
  - one that calls cloud instead of local → test_execute_fn_called_with_task
  - one that deposits even rejected outputs → test_rejected_output_not_deposited
  - one that skips deposit on accepted outputs → test_accepted_output_is_deposited
  - one that deposits multiple times for one run → test_deposit_called_exactly_once_per_accepted
  - one that passes wrong key to Outcome → test_deposited_outcome_key_matches_task
  - one that stores real graph under pytest → all tests use injected deposit_fn (never writes)
"""

from __future__ import annotations

from cohezion.agents.local_inference_agent import AgentResult, LocalInferenceAgent
from cohezion.governance.experiential_closure import Outcome


# ---------------------------------------------------------------------------
# Helpers — deterministic stubs (pure callables, no live services)
# ---------------------------------------------------------------------------


def _always_accept(output: str, task: str) -> bool:
    """Stub evaluate_fn: every non-empty output is accepted."""
    return bool(output.strip())


def _always_reject(output: str, task: str) -> bool:
    """Stub evaluate_fn: every output is rejected."""
    return False


def _local_fn(task: str) -> str:
    """Stub execute_fn simulating a local-tier response."""
    return f"local answer for: {task}"


# ---------------------------------------------------------------------------
# T_routing: execute_fn is called with the correct task string
# Fails: an impl that ignores execute_fn and calls cloud directly.
# ---------------------------------------------------------------------------


def test_execute_fn_called_with_task() -> None:
    """The injected execute_fn receives the task string (local routing verified by injection)."""
    received: list[str] = []

    def capture_fn(task: str) -> str:
        received.append(task)
        return "ok"

    agent = LocalInferenceAgent(
        execute_fn=capture_fn,
        evaluate_fn=_always_reject,
        deposit_fn=lambda _o: None,
    )
    agent.run("classify this document")
    assert received == ["classify this document"]


# ---------------------------------------------------------------------------
# T_accepted: accepted output → deposit_fn called once
# Fails: an impl that never calls deposit_fn.
# ---------------------------------------------------------------------------


def test_accepted_output_is_deposited() -> None:
    """An accepted outcome is forwarded to deposit_fn exactly once."""
    deposited: list[Outcome] = []
    agent = LocalInferenceAgent(
        execute_fn=_local_fn,
        evaluate_fn=_always_accept,
        deposit_fn=deposited.append,
    )
    agent.run("some task")
    assert len(deposited) == 1, "deposit_fn must be called once for an accepted outcome"


# ---------------------------------------------------------------------------
# T_rejected: rejected output → deposit_fn never called
# Fails: an impl that deposits every outcome regardless of verdict.
# ---------------------------------------------------------------------------


def test_rejected_output_not_deposited() -> None:
    """A rejected outcome does NOT reach deposit_fn — AUTODQA I6 spirit."""
    deposited: list[Outcome] = []
    agent = LocalInferenceAgent(
        execute_fn=_local_fn,
        evaluate_fn=_always_reject,
        deposit_fn=deposited.append,
    )
    agent.run("some task")
    assert deposited == [], "deposit_fn must NOT be called for a rejected outcome"


# ---------------------------------------------------------------------------
# T_exactly_once: one run → at most one deposit call, even for accepted
# Fails: an impl with a loop that calls deposit_fn twice.
# ---------------------------------------------------------------------------


def test_deposit_called_exactly_once_per_accepted() -> None:
    """One agent.run() call → exactly one deposit_fn invocation when accepted."""
    call_count = 0

    def counting_deposit(outcome: Outcome) -> None:
        nonlocal call_count
        call_count += 1

    agent = LocalInferenceAgent(
        execute_fn=_local_fn,
        evaluate_fn=_always_accept,
        deposit_fn=counting_deposit,
    )
    agent.run("task X")
    assert call_count == 1


# ---------------------------------------------------------------------------
# T_outcome_key: deposited Outcome.key matches the task string
# Fails: an impl that deposits with the wrong key (e.g. the output text).
# ---------------------------------------------------------------------------


def test_deposited_outcome_key_matches_task() -> None:
    """The deposited Outcome carries key=task (not key=output or key='')."""
    deposited: list[Outcome] = []
    task = "rerank candidate documents"
    agent = LocalInferenceAgent(
        execute_fn=_local_fn,
        evaluate_fn=_always_accept,
        deposit_fn=deposited.append,
    )
    agent.run(task)
    assert len(deposited) == 1
    assert deposited[0].key == task, f"Outcome.key={deposited[0].key!r} must equal task={task!r}"


# ---------------------------------------------------------------------------
# T_outcome_accepted_flag: deposited Outcome.accepted is True
# Fails: an impl that deposits Outcome(accepted=False).
# ---------------------------------------------------------------------------


def test_deposited_outcome_has_accepted_true() -> None:
    """The deposited Outcome always carries accepted=True (I6 spirit — rejects excluded)."""
    deposited: list[Outcome] = []
    agent = LocalInferenceAgent(
        execute_fn=_local_fn,
        evaluate_fn=_always_accept,
        deposit_fn=deposited.append,
    )
    agent.run("task Y")
    assert deposited[0].accepted is True


# ---------------------------------------------------------------------------
# T_result: run() returns AgentResult with task/output/accepted populated
# Fails: an impl that returns None or a wrong type.
# ---------------------------------------------------------------------------


def test_run_returns_agent_result() -> None:
    """agent.run() returns an AgentResult with task, output, and accepted populated."""
    agent = LocalInferenceAgent(
        execute_fn=lambda t: "good output",
        evaluate_fn=_always_accept,
        deposit_fn=lambda _o: None,
    )
    result = agent.run("my task")
    assert isinstance(result, AgentResult)
    assert result.task == "my task"
    assert result.output == "good output"
    assert result.accepted is True


def test_run_returns_agent_result_rejected() -> None:
    """AgentResult.accepted=False when evaluate_fn returns False."""
    agent = LocalInferenceAgent(
        execute_fn=lambda _t: "rejected output",
        evaluate_fn=_always_reject,
        deposit_fn=lambda _o: None,
    )
    result = agent.run("my task")
    assert isinstance(result, AgentResult)
    assert result.accepted is False
