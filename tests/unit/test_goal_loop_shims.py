"""R3 / P5: rival goal-loop modules adapt the spine instead of redefining it."""

from __future__ import annotations

import cohezion.compound.goals_and_loops_orchestrator as rival_orch
import cohezion.flume.loop_goal_refactor_engine as spine
from cohezion.compound import inter_daemon_loop_nexus
from cohezion.recursive_trace.goal_loop import GoalDrivenTraceLoop


def test_orchestrator_vocabulary_is_the_spines_not_a_copy() -> None:
    """Identity, not equality: a second enum with the same members would still `==`
    nothing across modules. Mutation: re-declare GoalStatus in the rival -> red."""
    assert rival_orch.GoalStatus is spine.GoalStatus
    assert rival_orch.LoopStage is spine.LoopStage
    assert rival_orch.AcceptanceCriterion is spine.AcceptanceCriterion
    assert inter_daemon_loop_nexus.GoalStatus is spine.GoalStatus  # a live src/ importer


def test_orchestrator_still_runs_end_to_end() -> None:
    import asyncio

    orch = rival_orch.GoalsAndLoopsOrchestrator()
    goal = orch.create_goal("g1", "t", "o", [("c1", "d")])
    loop = orch.create_loop("g1", max_cycles=2)

    async def ok() -> tuple[bool, str]:
        return True, "fine"

    async def noop() -> None:
        return None

    assert asyncio.run(loop.run(noop, ok)) is True
    assert goal.status is spine.GoalStatus.SATISFIED
    assert "g1" in orch.render_summary()


def test_goal_loop_graph_write_goes_through_the_spine_persistence(monkeypatch) -> None:
    seen: list[str] = []
    monkeypatch.setattr(
        spine.DurableSurrealGoalPersistence, "execute", lambda self, stmt: seen.append(stmt) or []
    )
    loop = GoalDrivenTraceLoop(["a"], {"initial": ["a"]}, persist_graph=True)
    loop._persist_graph_edge("goal 1", "a", "initial", True, 2)
    assert len(seen) == 1
    assert "RELATE $g->RESOLVED_BY->$s" in seen[0] and "kg_node:goal_goal1" in seen[0]


def test_goal_loop_graph_write_stays_fail_soft_but_no_longer_swallows_err_silently(
    monkeypatch,
) -> None:
    def boom(self, stmt):
        raise RuntimeError("SurrealDB statement error: The table 'x' does not exist")

    monkeypatch.setattr(spine.DurableSurrealGoalPersistence, "execute", boom)
    loop = GoalDrivenTraceLoop(["a"], {"initial": ["a"]}, persist_graph=True)
    loop._persist_graph_edge("g", "a", "initial", False, 1)  # must not raise


def test_persist_graph_off_writes_nothing(monkeypatch) -> None:
    called: list[str] = []
    monkeypatch.setattr(
        spine.DurableSurrealGoalPersistence, "execute", lambda self, stmt: called.append(stmt) or []
    )
    GoalDrivenTraceLoop(["a"], {"initial": ["a"]})._persist_graph_edge("g", "a", "initial", True, 1)
    assert called == []
