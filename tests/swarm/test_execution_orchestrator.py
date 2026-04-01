"""Tests for swarm/execution_orchestrator.py.

Covers parallel execution of team plans with dependency tracking.
"""

from __future__ import annotations

import asyncio

import pytest

from cohezion.swarm.execution_orchestrator import (
    ExecutionOrchestrator,
    TaskResult,
    _topological_sort,
)
from cohezion.swarm.team_orchestrator import TaskSpec, TeamPlan


def test_topological_sort_independent():
    """[P0] Should group independent tasks in one wave."""
    tasks = [
        TaskSpec(id="t1", subject="s1", description="d1"),
        TaskSpec(id="t2", subject="s2", description="d2"),
    ]
    waves = _topological_sort(tasks)
    assert len(waves) == 1
    assert len(waves[0]) == 2

def test_topological_sort_dependent():
    """[P0] Should split dependent tasks into waves."""
    tasks = [
        TaskSpec(id="t1", subject="s1", description="d1"),
        TaskSpec(id="t2", subject="s2", description="d2", blocked_by=["t1"]),
    ]
    waves = _topological_sort(tasks)
    assert len(waves) == 2
    assert waves[0][0].id == "t1"
    assert waves[1][0].id == "t2"

@pytest.mark.asyncio
async def test_execution_orchestrator_parallel(monkeypatch):
    """[P0] Should execute independent tasks in parallel."""
    # Mock _execute_task to record start times
    execution_times = []
    
    async def mock_exec(task):
        execution_times.append(asyncio.get_event_loop().time())
        await asyncio.sleep(0.1)
        return TaskResult(task_id=task.id, subject=task.subject)

    orch = ExecutionOrchestrator()
    monkeypatch.setattr(orch, "_execute_task", mock_exec)
    
    plan = TeamPlan(
        name="test-plan",
        intent="parallel test",
        tasks=[
            TaskSpec(id="t1", subject="s1", description="d1"),
            TaskSpec(id="t2", subject="s2", description="d2"),
        ]
    )
    
    report = await orch.execute(plan)
    
    assert len(report.task_results) == 2
    # Check that they started nearly at the same time
    assert abs(execution_times[0] - execution_times[1]) < 0.05

@pytest.mark.asyncio
async def test_execution_orchestrator_sequential(monkeypatch):
    """[P0] Should respect dependencies."""
    execution_order = []
    
    async def mock_exec(task):
        execution_order.append(task.id)
        return TaskResult(task_id=task.id, subject=task.subject)

    orch = ExecutionOrchestrator()
    monkeypatch.setattr(orch, "_execute_task", mock_exec)
    
    plan = TeamPlan(
        name="test-plan",
        intent="sequential test",
        tasks=[
            TaskSpec(id="t1", subject="s1", description="d1"),
            TaskSpec(id="t2", subject="s2", description="d2", blocked_by=["t1"]),
        ]
    )
    
    await orch.execute(plan)
    assert execution_order == ["t1", "t2"]
