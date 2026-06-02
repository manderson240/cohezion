"""Tests for ReflectiveDriver — the keystone that makes the compound self-improvement loop LIVE.

The driver joins the three tested-but-latent halves with ONE shared GroundTruthHierarchy and ONE
driver-owned ReDispatchLedger:
  * WRITE  — run_with_reflection(trust=H) -> reflect -> adapt_skill records guards into H
  * BOUND  — the ledger lives on the driver, so the livelock bound survives across tasks
  * READ   — every worker the driver builds is UnifiedAgent(guidance=H), so it reads guards back

The DISCRIMINATING invariants (what no caller wires today): object identity of the shared H across
the read and write sides, and ledger persistence across separate run() calls.

No network: stub workers / mocked executors.
"""

from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import AsyncMock

import pytest

from cohezion.agent.error_loop import ReDispatchLedger
from cohezion.agent.reflective_driver import ReflectiveDriver
from cohezion.agent.unified_harness import ExecutionTrace, ToolCall, UnifiedAgent
from cohezion.memory.trust_hierarchy import GroundTruthHierarchy


_FAULT = "disk full"


def _fault_trace() -> ExecutionTrace:
    t = ExecutionTrace(task_id="t", start_time="now")
    t.tool_calls.append(ToolCall(tool_name="write", arguments={}, error=_FAULT))
    return t


def _clean_trace() -> ExecutionTrace:
    return ExecutionTrace(task_id="t", start_time="now", completed=True)


class _StubWorker:
    """Duck-typed worker returning scripted traces; carries guidance like a real agent would."""

    def __init__(self, traces, guidance=None):
        self._t = list(traces)
        self.dispatches = 0
        self.guidance = guidance

    async def run_task(self, task, env=None, timeout=1800) -> ExecutionTrace:
        i = min(self.dispatches, len(self._t) - 1)
        self.dispatches += 1
        return self._t[i]


# -- the identity join (the missing wire) -------------------------------------


def test_default_factory_wires_the_shared_hierarchy_into_the_worker():
    driver = ReflectiveDriver(executor_factory=lambda: AsyncMock())
    agent = driver.build_agent()
    assert agent.guidance is driver.guidance  # read side reads the SAME H the write side writes


def test_explicit_hierarchy_and_ledger_are_held():
    H = GroundTruthHierarchy()
    L = ReDispatchLedger(max_per_signature=2)
    driver = ReflectiveDriver(guidance=H, ledger=L, executor_factory=lambda: AsyncMock())
    assert driver.guidance is H and driver.ledger is L


# -- WRITE half: a faulting task records a guard into the shared hierarchy -----


@pytest.mark.asyncio
async def test_faulting_task_writes_guard_into_shared_hierarchy():
    H = GroundTruthHierarchy()
    driver = ReflectiveDriver(
        guidance=H,
        ledger=ReDispatchLedger(max_per_signature=3),
        agent_factory=lambda: _StubWorker([_fault_trace()] * 5),
    )
    out = await driver.run("flaky task", max_redispatch=9)
    assert out["action"] == "abandon"  # bounded
    # the guard was written into the SAME hierarchy via trust=driver.guidance
    assert any(_FAULT in f.content for f in H.rank())


# -- BOUND: the ledger persists across separate run() calls (cross-task) -------


@pytest.mark.asyncio
async def test_ledger_persists_across_runs():
    driver = ReflectiveDriver(
        ledger=ReDispatchLedger(max_per_signature=2),
        agent_factory=lambda: _StubWorker([_fault_trace()] * 5),
    )
    r1 = await driver.run("flaky", max_redispatch=9)
    assert r1["action"] == "abandon"
    r2 = await driver.run("flaky", max_redispatch=9)  # SAME driver-owned ledger
    # second run on the already-exhausted signature is bounded to a single re-learn dispatch
    assert r2["action"] == "abandon" and r2["dispatches"] <= 1


# -- READ half end-to-end: the written guard reaches a fresh worker's prompt ---


@pytest.mark.asyncio
async def test_closed_loop_written_guard_is_read_by_next_worker():
    H = GroundTruthHierarchy()
    driver = ReflectiveDriver(
        guidance=H,
        ledger=ReDispatchLedger(max_per_signature=3),
        agent_factory=lambda: _StubWorker([_fault_trace()] * 5),
    )
    await driver.run("flaky task", max_redispatch=9)  # WRITE: populates H (recurs -> clears floor)

    # READ: a real worker sharing the driver's H injects the guard into its planning prompt.
    reader = UnifiedAgent(executor=AsyncMock(), guidance=driver.guidance)
    reader.executor.execute_task = AsyncMock(
        return_value=SimpleNamespace(output='{"complete": true}')
    )
    await reader._plan_next_action(
        task="new task", trace=ExecutionTrace("t", "now"), workdir="/tmp", step=0
    )
    prompt = reader.executor.execute_task.call_args.kwargs["task"]
    assert _FAULT in prompt  # the loop is closed: a fault on task 1 informs planning on task 2


# -- clean task commits -------------------------------------------------------


@pytest.mark.asyncio
async def test_clean_task_commits():
    driver = ReflectiveDriver(agent_factory=lambda: _StubWorker([_clean_trace()]))
    out = await driver.run("easy task")
    assert out["action"] == "commit"


# -- HIGH#1: a volatile-token fault corroborates ONE masked guard (loop works for REAL faults) ----


def _fault_trace_vol(i: int) -> ExecutionTrace:
    """A fault whose reason carries a per-run volatile path (the realistic case)."""
    t = ExecutionTrace(task_id="t", start_time="now")
    t.tool_calls.append(
        ToolCall(tool_name="write", arguments={}, error=f"{_FAULT} at /tmp/agent_{i}/out")
    )
    return t


@pytest.mark.asyncio
async def test_volatile_token_fault_corroborates_one_injectable_guard():
    H = GroundTruthHierarchy()
    driver = ReflectiveDriver(
        guidance=H,
        ledger=ReDispatchLedger(max_per_signature=3),
        agent_factory=lambda: _StubWorker([_fault_trace_vol(i) for i in range(5)]),
    )
    await driver.run("flaky task", max_redispatch=9)
    guard_facts = [f for f in H.rank() if "guarded against" in f.content]
    # masking collapses the per-run paths to ONE guard (not N distinct trust=0.5 facts)...
    assert len(guard_facts) == 1
    # ...which corroborates across recurrences and crosses the injection floor (the READ half lives)
    assert guard_facts[0].trust >= 0.6
    assert "#" in guard_facts[0].content  # the volatile path was masked


# -- HIGH#2: the DEFAULT build_agent path actually reads a written guard (fails if guidance= dropped)


@pytest.mark.asyncio
async def test_default_build_agent_reads_written_guard_end_to_end():
    H = GroundTruthHierarchy()
    H.add("skill 'write' guarded against: disk full")  # recurring (>= floor) guard already present
    H.add("skill 'write' guarded against: disk full")
    driver = ReflectiveDriver(guidance=H, executor_factory=lambda: AsyncMock())
    agent = driver.build_agent()  # DEFAULT factory -> real UnifiedAgent(guidance=self.guidance)
    agent.executor.execute_task = AsyncMock(
        return_value=SimpleNamespace(output='{"complete": true}')
    )
    await agent._plan_next_action(
        task="x", trace=ExecutionTrace("t", "now"), workdir="/tmp", step=0
    )
    prompt = agent.executor.execute_task.call_args.kwargs["task"]
    assert _FAULT in prompt  # the production build_agent path injects the guard


# -- MED: a custom factory whose worker doesn't share the hierarchy warns (no silent half-open loop)


def test_half_open_loop_warns(caplog):
    driver = ReflectiveDriver(agent_factory=lambda: _StubWorker([_clean_trace()], guidance=None))
    with caplog.at_level("WARNING"):
        driver.build_agent()
    assert "detached" in caplog.text.lower() or "half" in caplog.text.lower()
