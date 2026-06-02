"""Tests for run_with_reflection — the live activation seam wiring worker run_task -> reflect.

The headline invariant (RETRO-2026-06-02c): the re-dispatch bound must survive the *stateless
worker boundary*. These tests force that architecture — the ledger is caller-held and external, and
the key test re-runs with a FRESH worker to prove the bound is not worker-state.

No LLM / no network: a duck-typed _StubAgent returns scripted ExecutionTraces.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.agent.error_loop import ReDispatchLedger, error_signature
from cohezion.agent.reflective_orchestrator import run_with_reflection
from cohezion.agent.unified_harness import ExecutionTrace, ToolCall


# -- scripted, network-free fixtures ------------------------------------------


def _clean_trace() -> ExecutionTrace:
    """A completed trace with no tool errors -> attribute_fault returns None -> commit."""
    return ExecutionTrace(task_id="t", start_time="now", completed=True)


def _fault_trace(reason: str, tool: str = "bash") -> ExecutionTrace:
    t = ExecutionTrace(task_id="t", start_time="now")
    t.tool_calls.append(ToolCall(tool_name=tool, arguments={}, error=reason))
    return t


_TRANSIENT = "connection timed out talking to fleet node"
_PERMANENT = "file not found: no such config"


class _StubAgent:
    """Duck-typed worker. Returns scripted traces; counts real dispatches. No state shared w/ ledger."""

    def __init__(self, traces: list[ExecutionTrace]):
        self._traces = list(traces)
        self.dispatches = 0

    async def run_task(self, task, env=None, timeout=1800) -> ExecutionTrace:
        i = min(self.dispatches, len(self._traces) - 1)
        self.dispatches += 1
        return self._traces[i]


# -- terminal-action routing ---------------------------------------------------


@pytest.mark.asyncio
async def test_clean_trace_commits_single_dispatch():
    agent = _StubAgent([_clean_trace()])
    L = ReDispatchLedger()
    out = await run_with_reflection(agent, "task", ledger=L)
    assert out["action"] == "commit"
    assert out["dispatches"] == 1 and agent.dispatches == 1


@pytest.mark.asyncio
async def test_permanent_fault_escalates_without_retry():
    agent = _StubAgent([_fault_trace(_PERMANENT)] * 5)
    L = ReDispatchLedger()
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=5)
    assert out["action"] == "escalate"  # PERMANENT budget == 0 -> orchestrator re-plans
    assert agent.dispatches == 1  # never self-corrects a permanent fault


# -- the livelock bound --------------------------------------------------------


@pytest.mark.asyncio
async def test_transient_fault_bounded_then_abandons():
    agent = _StubAgent([_fault_trace(_TRANSIENT)] * 10)
    L = ReDispatchLedger(max_per_signature=3)
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=9)
    assert out["action"] == "abandon"
    # 3 dispatches allowed by the ledger, then a PRE-dispatch abandon (within-call short-circuit):
    assert agent.dispatches == 3


@pytest.mark.asyncio
async def test_outer_cap_bounds_even_when_signature_evades_ledger():
    # Each dispatch yields a DIFFERENT signature (number masked away still differs by word) -> the
    # per-signature ledger never trips; only max_redispatch can stop it. Proves the absolute bound.
    traces = [_fault_trace(f"weird unique failure alpha{w}") for w in "abcdefghij"]
    agent = _StubAgent(traces)
    L = ReDispatchLedger(max_per_signature=99)
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=4)
    assert out["dispatches"] == 5  # max_redispatch + 1, then stops
    # terminal 'retry' (budget remained, outer cap stopped the loop) is normalized to a resolved verdict
    assert out["action"] == "abandon"


@pytest.mark.asyncio
async def test_bound_survives_fresh_worker():
    """THE headline invariant: a fresh worker cannot reset the bound — the ledger is external."""
    L = ReDispatchLedger(max_per_signature=2)
    sig = error_signature("bash", _TRANSIENT)

    a1 = _StubAgent([_fault_trace(_TRANSIENT)] * 10)
    r1 = await run_with_reflection(a1, "task", ledger=L, max_redispatch=9)
    assert r1["action"] == "abandon" and r1["signature"] == sig

    a2 = _StubAgent([_fault_trace(_TRANSIENT)] * 10)  # FRESH worker, brand-new instance
    r2 = await run_with_reflection(
        a2, "task", ledger=L, max_redispatch=9, prior_signature=r1["signature"]
    )
    # With the signature threaded, the fresh worker abandons WITHOUT dispatching at all:
    assert r2["action"] == "abandon" and a2.dispatches == 0
    assert r2["trace"] is None  # pre-dispatch abandon return contract: no trace


@pytest.mark.asyncio
async def test_across_call_costs_one_dispatch_without_prior_signature():
    """Honest boundary: without prior_signature, a new call must dispatch once to learn the sig."""
    L = ReDispatchLedger(max_per_signature=2)
    a1 = _StubAgent([_fault_trace(_TRANSIENT)] * 10)
    await run_with_reflection(a1, "task", ledger=L, max_redispatch=9)  # exhaust
    a2 = _StubAgent([_fault_trace(_TRANSIENT)] * 10)
    r2 = await run_with_reflection(a2, "task", ledger=L, max_redispatch=9)  # no prior_signature
    assert r2["action"] == "abandon" and a2.dispatches == 1


# -- commit resets the budget (the ledger's own semantics) ---------------------


@pytest.mark.asyncio
async def test_commit_resets_retried_signature():
    L = ReDispatchLedger(max_per_signature=3)
    sig = error_signature("bash", _TRANSIENT)
    # fail (transient) twice, then succeed
    agent = _StubAgent([_fault_trace(_TRANSIENT), _fault_trace(_TRANSIENT), _clean_trace()])
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=9)
    assert out["action"] == "commit" and agent.dispatches == 3
    assert L.attempts(sig) == 0  # reset on success so the fault may recur freely later


# -- structured result ---------------------------------------------------------


@pytest.mark.asyncio
async def test_result_records_every_decision():
    agent = _StubAgent([_fault_trace(_TRANSIENT), _clean_trace()])
    L = ReDispatchLedger(max_per_signature=3)
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=9)
    # decisions is the full audit trail; it may exceed dispatches (pre-dispatch abandons)
    assert isinstance(out["decisions"], list) and len(out["decisions"]) >= out["dispatches"]
    assert out["trace"].completed is True  # final trace is the successful one
    assert out["action"] == "commit"
    assert out["signature"] is None  # a real success reports no fault signature


@pytest.mark.asyncio
async def test_ledger_is_required_external_state():
    """The ledger must be caller-held (no worker-resident default) — omitting it is an error."""
    agent = _StubAgent([_clean_trace()])
    with pytest.raises(TypeError):
        await run_with_reflection(agent, "task")  # ledger is a required keyword


# -- commit health gate (Guard 5): absence of a tool-call fault is NOT sufficient --------------


def _incomplete_trace() -> ExecutionTrace:
    """Worker exhausted max_steps: did tool work, never emitted complete -> completed=False, no error."""
    t = ExecutionTrace(task_id="t", start_time="now", completed=False)
    t.tool_calls.append(ToolCall(tool_name="bash", arguments={}, result={"ok": True}))  # no error
    return t


def _errored_trace() -> ExecutionTrace:
    """Worker broke on max-recoveries: trace.error set, no per-tool-call error recorded."""
    return ExecutionTrace(
        task_id="t", start_time="now", completed=False, error="connection timed out"
    )


@pytest.mark.asyncio
async def test_incomplete_trace_is_not_committed():
    agent = _StubAgent([_incomplete_trace()])
    out = await run_with_reflection(agent, "task", ledger=ReDispatchLedger())
    assert out["action"] == "escalate"  # no tool fault, but the task did not complete
    assert "not a real success" in out["reason"]


@pytest.mark.asyncio
async def test_errored_trace_is_not_committed():
    agent = _StubAgent([_errored_trace()])
    out = await run_with_reflection(agent, "task", ledger=ReDispatchLedger())
    assert out["action"] == "escalate"  # trace.error set despite no tool-call error


# -- dispatch-failure counting (Guard 4): a dying/hung worker must be bounded -------------------


class _RaisingAgent:
    """Worker whose run_task RAISES instead of returning a trace (OOM-kill / process death)."""

    def __init__(self):
        self.dispatches = 0

    async def run_task(self, task, env=None, timeout=1800):
        self.dispatches += 1
        raise RuntimeError("worker process died (OOM-killed)")


@pytest.mark.asyncio
async def test_dispatch_exception_is_counted_and_bounded():
    agent = _RaisingAgent()
    L = ReDispatchLedger(max_per_signature=2)
    out = await run_with_reflection(agent, "task", ledger=L, max_redispatch=9)
    # a worker that DIES is counted by the ledger and bounded, not retried forever
    assert out["action"] == "abandon"
    assert agent.dispatches == 2  # cap reached via dispatch-exception counting
    assert out["trace"] is None


@pytest.mark.asyncio
async def test_wall_clock_timeout_is_counted(monkeypatch):
    import cohezion.agent.reflective_orchestrator as ro

    monkeypatch.setattr(ro, "_DISPATCH_GRACE_S", 0)  # so wait_for(timeout=0) fires immediately

    class _HangingAgent:
        def __init__(self):
            self.dispatches = 0

        async def run_task(self, task, env=None, timeout=1800):
            self.dispatches += 1
            await asyncio.sleep(10)  # never completes within the orchestrator wall-clock

    agent = _HangingAgent()
    L = ReDispatchLedger(max_per_signature=1)
    out = await ro.run_with_reflection(agent, "task", ledger=L, timeout=0, max_redispatch=5)
    # the orchestrator counts and bounds the hung dispatch (wait_for may cancel the coro before its
    # body runs, so agent.dispatches is unreliable — the orchestrator-side count is the invariant).
    assert out["action"] == "abandon" and out["dispatches"] == 1


# -- fail-fast on misconfiguration -------------------------------------------------------------


@pytest.mark.asyncio
async def test_negative_max_redispatch_raises():
    agent = _StubAgent([_clean_trace()])
    with pytest.raises(ValueError, match="max_redispatch"):
        await run_with_reflection(agent, "task", ledger=ReDispatchLedger(), max_redispatch=-1)


@pytest.mark.asyncio
async def test_terminal_retry_is_normalized_to_abandon():
    # max_redispatch=0 -> exactly one dispatch; a transient fault yields 'retry' which the loop
    # cannot act on -> normalized to a resolved 'abandon'.
    agent = _StubAgent([_fault_trace(_TRANSIENT)])
    out = await run_with_reflection(agent, "task", ledger=ReDispatchLedger(), max_redispatch=0)
    assert out["action"] == "abandon" and agent.dispatches == 1
    assert "re-invoke" in out["reason"]
