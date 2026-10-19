"""Unit tests for Multi-Solver Disagreement Rewards & Curricula (arXiv:2608.30035)."""

from __future__ import annotations

import pytest

from cohezion.optimization.r_zero_challenger_solver import (
    DisagreementMetrics,
    MultiSolverDisagreementEngine,
    MultiSolverTriadLoop,
    RZeroEvaluation,
    RZeroSolution,
    RZeroSolver,
)


class TestMultiSolverDisagreementEngine:
    """Test suite for MultiSolverDisagreementEngine."""

    @pytest.fixture
    def engine(self) -> MultiSolverDisagreementEngine:
        return MultiSolverDisagreementEngine(target_coherence=0.50, sigma=0.20)

    def test_single_solver_returns_zero_entropy(
        self, engine: MultiSolverDisagreementEngine
    ) -> None:
        """A single solver cannot produce inter-model disagreement."""
        sol = RZeroSolution("s1", "c1", "m1", "def transform(x): return x")
        ev = RZeroEvaluation("c1", "s1", True, 1.0, 1.0, "ok", 0.0, 2.0, None)  # type: ignore[arg-type]
        metrics = engine.evaluate_disagreement([sol], [ev])

        assert metrics.entropy == 0.0
        assert metrics.solvability_rate == 1.0
        assert not metrics.is_frontier_task

    def test_uniform_agreement_returns_zero_entropy(
        self, engine: MultiSolverDisagreementEngine
    ) -> None:
        """When all solvers agree on the same solution, disagreement entropy is 0."""
        sols = [
            RZeroSolution("s1", "c1", "m1", "def transform(x): return x", predicted_output=[[1]]),
            RZeroSolution("s2", "c1", "m2", "def transform(x): return x", predicted_output=[[1]]),
            RZeroSolution("s3", "c1", "m3", "def transform(x): return x", predicted_output=[[1]]),
        ]
        evs = [
            RZeroEvaluation("c1", f"s{i}", True, 1.0, 1.0, "ok", 0.0, 2.0, None)  # type: ignore[arg-type]
            for i in range(1, 4)
        ]
        metrics = engine.evaluate_disagreement(sols, evs)

        assert metrics.entropy == 0.0
        assert metrics.solvability_rate == 1.0
        assert metrics.num_unique_clusters == 1
        assert not metrics.is_frontier_task

    def test_disagreement_maximizes_entropy_and_hiho_reward(
        self, engine: MultiSolverDisagreementEngine
    ) -> None:
        """When solvers produce conflicting outputs near 50% solvability, entropy and HIHO reward peak."""
        sols = [
            RZeroSolution("s1", "c1", "m1", "code1", predicted_output=[[1, 0]]),
            RZeroSolution("s2", "c1", "m2", "code2", predicted_output=[[1, 0]]),
            RZeroSolution("s3", "c1", "m3", "code3", predicted_output=[[0, 1]]),
            RZeroSolution("s4", "c1", "m4", "code4", predicted_output=[[9, 9]]),
        ]
        # 2 out of 4 correct -> solvability_rate = 0.50
        evs = [
            RZeroEvaluation("c1", "s1", True, 1.0, 1.0, "ok", 0.0, 2.0, None),  # type: ignore[arg-type]
            RZeroEvaluation("c1", "s2", True, 1.0, 1.0, "ok", 0.0, 2.0, None),  # type: ignore[arg-type]
            RZeroEvaluation("c1", "s3", False, 0.5, 0.0, "fail", 0.0, 2.0, None),  # type: ignore[arg-type]
            RZeroEvaluation("c1", "s4", False, 0.0, 0.0, "fail", 0.0, 2.0, None),  # type: ignore[arg-type]
        ]
        metrics = engine.evaluate_disagreement(sols, evs)

        assert metrics.solvability_rate == 0.50
        assert metrics.entropy > 0.50
        assert metrics.hiho_alignment_reward > 0.50
        assert metrics.num_unique_clusters == 3
        assert metrics.is_frontier_task


@pytest.mark.asyncio
class TestMultiSolverTriadLoop:
    """Test suite for MultiSolverTriadLoop."""

    async def test_multi_solver_step_execution(self) -> None:
        """Verify multi-solver loop runs complete step and computes disagreement metrics."""
        # 3 solvers with different behaviors
        s1 = RZeroSolver(model_name="solver_heuristic")
        s2 = RZeroSolver(model_name="solver_identity")
        s3 = RZeroSolver(model_name="solver_rot90")

        loop = MultiSolverTriadLoop(
            domain="arc_agi",
            initial_difficulty=2.0,
            solvers=[s1, s2, s3],
        )

        multi_eval = await loop.step()
        assert multi_eval.challenge_id.startswith("rzero_arc_agi_")
        assert len(multi_eval.solutions) == 3
        assert len(multi_eval.individual_evaluations) == 3
        assert isinstance(multi_eval.disagreement_metrics, DisagreementMetrics)
        assert len(loop.history) == 1
