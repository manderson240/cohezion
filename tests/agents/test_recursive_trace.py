"""Recursive ExecutionTrace + agent delegation nesting (unified_harness).

The compounding primitive: traces form a tree so retrospection (A-Evolve Diagnose)
can reason over the whole recursive call tree, not a flat list.
"""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from cohezion.agent.unified_harness import ExecutionTrace, ToolCall, UnifiedAgent


# --- ExecutionTrace recursive structure (no agent machinery needed) ---


def test_add_child_stamps_parent_and_depth() -> None:
    root = ExecutionTrace(task_id="root", start_time="t")
    child = root.add_child(ExecutionTrace(task_id="c1", start_time="t"))
    assert child.parent_task_id == "root"
    assert child.depth == 1
    assert root.children == [child]


def test_walk_is_preorder_over_the_whole_tree() -> None:
    root = ExecutionTrace(task_id="root", start_time="t")
    c1 = root.add_child(ExecutionTrace(task_id="c1", start_time="t"))
    root.add_child(ExecutionTrace(task_id="c2", start_time="t"))
    c1.add_child(ExecutionTrace(task_id="gc", start_time="t"))
    assert [n.task_id for n in root.walk()] == ["root", "c1", "gc", "c2"]
    assert [n.depth for n in root.walk()] == [0, 1, 2, 1]


def test_aggregate_rolls_up_metrics_recursively() -> None:
    root = ExecutionTrace(task_id="root", start_time="t", completed=True)
    root.tool_calls.append(ToolCall(tool_name="bash", arguments={}))
    c1 = root.add_child(ExecutionTrace(task_id="c1", start_time="t", completed=True, recoveries=1))
    c1.tool_calls.append(ToolCall(tool_name="python", arguments={}))
    root.add_child(ExecutionTrace(task_id="bad", start_time="t", error="boom"))

    agg = root.aggregate()
    assert agg["node_count"] == 3
    assert agg["max_depth"] == 1
    assert agg["total_tool_calls"] == 2
    assert agg["total_recoveries"] == 1
    assert agg["completed_subtree"] is False  # 'bad' never completed
    assert agg["failed_task_ids"] == ["bad"]


def test_single_node_aggregate_is_self() -> None:
    t = ExecutionTrace(task_id="solo", start_time="t", completed=True)
    agg = t.aggregate()
    assert agg["node_count"] == 1 and agg["max_depth"] == 0 and agg["completed_subtree"] is True


# --- Delegation producer: run_task nests a child trace (mocked planner + session) ---


def _agent_with_script(actions: list[dict]) -> UnifiedAgent:
    """A UnifiedAgent whose planner replays a fixed action script, no real LLM/session."""
    agent = UnifiedAgent(executor=MagicMock())
    # Mock the async session-manager context (check_alignment / end_session).
    mgr = MagicMock()
    mgr.check_alignment.return_value = MagicMock(should_proceed=True, issues=[])
    mgr.end_session.return_value = {}
    agent.session_mgr = MagicMock(
        __aenter__=AsyncMock(return_value=mgr), __aexit__=AsyncMock(return_value=False)
    )
    agent._plan_next_action = AsyncMock(side_effect=actions)
    return agent


@pytest.mark.asyncio
async def test_run_task_nests_delegated_child_trace() -> None:
    """A 'delegate' action spawns a nested run whose trace nests under the parent."""
    # Parent: delegate once, then complete. Child: complete immediately.
    parent_actions = [
        {"delegate": True, "subtask": "do the sub thing"},
        {"complete": True, "result": {"ok": True}},
    ]
    child_actions = [{"complete": True, "result": {"sub": True}}]
    agent = _agent_with_script(parent_actions + child_actions)

    trace = await agent.run_task("parent task")

    assert len(trace.children) == 1, "delegated subtask should nest as a child trace"
    child = trace.children[0]
    assert child.parent_task_id == trace.task_id and child.depth == 1
    assert child.completed is True
    # the delegation is also recorded as a tool call on the parent
    assert any(tc.tool_name == "delegate" for tc in trace.tool_calls)
    assert trace.aggregate()["node_count"] == 2


@pytest.mark.asyncio
async def test_delegation_depth_is_capped() -> None:
    """At max_delegation_depth a 'delegate' action does NOT recurse further."""
    agent = _agent_with_script([{"delegate": True, "subtask": "x"}, {"complete": True}])
    agent.max_delegation_depth = 0  # no delegation allowed
    trace = await agent.run_task("task")
    assert trace.children == [], "depth guard must block delegation at the cap"


# --- Bridge: RetrospectionEngine consumes the recursive tree (recursive-aware gate) ---


def test_retrospection_refines_on_clean_subtree() -> None:
    from cohezion.core.compound.retrospection import RetrospectionEngine

    root = ExecutionTrace(task_id="root", start_time="t", completed=True)
    root.add_child(ExecutionTrace(task_id="c1", start_time="t", completed=True))
    out = RetrospectionEngine().analyze_recursive_trace(root, skill_name="DEMO")
    assert out["should_refine"] is True
    assert out["failed_task_ids"] == []
    assert out["max_depth"] == 1


def test_retrospection_blocks_refine_when_delegated_child_failed() -> None:
    """The recursive-aware gate: top-level success but a delegated subtask failed
    must NOT refine — a flat trace would miss this and learn a bad lesson."""
    from cohezion.core.compound.retrospection import RetrospectionEngine

    root = ExecutionTrace(task_id="root", start_time="t", completed=True)  # top-level "ok"
    root.add_child(ExecutionTrace(task_id="sub", start_time="t", error="boom"))  # child FAILED
    out = RetrospectionEngine().analyze_recursive_trace(root, skill_name="DEMO")
    assert out["should_refine"] is False
    assert "sub" in out["failed_task_ids"]
    assert "Fix delegated failure" in out["recommendation"]
