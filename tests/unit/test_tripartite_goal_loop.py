"""Unit tests for TripartiteGoalLoop (Codebase Sweep, Bleeding Edge Research, Experiential Learning).

Validates:
1. Internal Codebase Sweep verification and reporting.
2. Bleeding Edge Research retrieval and strategy recommendation.
3. Experiential Learning AutoHarness gating, ZK-FV proof generation, and reward formulation.
4. Dual persistence into Obsidian Vault (01-Learnings) and SurrealDB (experiential_replay).
5. Full iterative convergence of TripartiteGoalLoop.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from cohezion.flume.loop_goal_refactor_engine import GoalSpecification
from cohezion.recursive_trace.tripartite_goal_loop import (
    BleedingEdgeResearchResult,
    CodebaseSweepResult,
    ExperientialLearningResult,
    TripartiteGoalLoop,
    TripartiteGoalLoopResult,
)


def test_internal_codebase_sweep():
    loop = TripartiteGoalLoop()
    sweep = loop.execute_internal_sweep()
    assert isinstance(sweep, CodebaseSweepResult)
    assert sweep.checks_evaluated >= 2
    assert sweep.integrity_score >= 0.85
    assert sweep.passed is True
    assert len(sweep.findings) > 0


def test_bleeding_edge_research():
    loop = TripartiteGoalLoop()
    research = loop.execute_frontier_research("Stabilize Strix Halo APU Mesh", "drift")
    assert isinstance(research, BleedingEdgeResearchResult)
    assert len(research.citations) >= 3
    assert any("AutoHarness" in c for c in research.citations)
    assert any("Graphiti" in c for c in research.citations)
    assert any("A-MEM" in c for c in research.citations)
    assert len(research.frontier_paradigms) >= 3
    assert research.recommended_strategy in loop.strategies


def test_experiential_learning_with_dual_persistence(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
):
    # Route vault writes to tmp_path for test isolation
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_LEARNINGS", tmp_path / "01-Learnings"
    )
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_RETROS", tmp_path / "retros"
    )
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_KANBAN", tmp_path / "kanban"
    )

    loop = TripartiteGoalLoop()
    goal = GoalSpecification(
        goal_id="test_exp_goal_001",
        title="Verify Experiential Learning Pipeline",
        target_metric="coherence",
        target_threshold=0.50,
    )
    sweep = loop.execute_internal_sweep()
    research = loop.execute_frontier_research(goal.title, "initial")

    learning, v_path, _s_rec = loop.execute_experiential_learning(
        goal, 1, "cellular_sheaf_diffusion", True, sweep, research
    )

    assert isinstance(learning, ExperientialLearningResult)
    assert learning.reward >= 0.90
    assert learning.autoharness_allowed is True
    assert learning.zkfv_verified is True
    assert "zkproof-" in learning.zkfv_proof_id

    # Verify Obsidian Vault artifact
    assert learning.vault_persisted is True
    assert Path(v_path).exists()
    content = Path(v_path).read_text()
    assert "AutoHarness" in content
    assert "ZK-FV Formal Proof Valid" in content
    assert str(goal.goal_id) in content


def test_full_tripartite_goal_loop_execution(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_LEARNINGS", tmp_path / "01-Learnings"
    )
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_RETROS", tmp_path / "retros"
    )
    monkeypatch.setattr(
        "cohezion.recursive_trace.tripartite_goal_loop.VAULT_KANBAN", tmp_path / "kanban"
    )

    loop = TripartiteGoalLoop(max_depth=3)
    goal = GoalSpecification(
        goal_id="test_tripartite_full_002",
        title="End-to-End Tripartite Loop Convergence",
        target_metric="pass_rate",
        target_threshold=1.0,
        max_iterations=3,
    )

    # Step function that succeeds on second try
    step_calls = []

    def mock_step(g, strat):
        step_calls.append(strat)
        if len(step_calls) == 1:
            return False, "Initial probe detected drift", "drift"
        return True, "Converged via sheaf harmonic diffusion", None

    res: TripartiteGoalLoopResult = loop.run(goal, mock_step)

    assert res.converged is True
    assert res.iterations_run == 2
    assert res.final_reward >= 0.90
    assert len(res.history) == 2
    assert len(res.vault_notes_created) == 2

    # Check first iteration (failed probe)
    it1 = res.history[0]
    assert it1.satisfied is False
    assert it1.sweep.passed is True
    assert it1.research.recommended_strategy is not None

    # Check second iteration (converged)
    it2 = res.history[1]
    assert it2.satisfied is True
    assert it2.learning.zkfv_verified is True
