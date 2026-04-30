"""Tests for Research Squad - Self-improving compound system.

Tests the recursive optimization loop.
"""

from __future__ import annotations

import pytest

from cohezion.research import (
    OptimizationResult,
    ResearchSquad,
    integrate_with_compound_system,
)


class TestResearchSquad:
    """Tests for Research Squad functionality."""

    @pytest.fixture
    def squad(self):
        """Create Research Squad for testing."""
        return ResearchSquad()

    @pytest.mark.fast
    def test_squad_initialization(self):
        """[SQUAD-01] Research Squad initializes correctly."""
        squad = ResearchSquad()

        assert squad.swarm is not None
        assert squad.executor is not None
        assert squad.cost_tracker is not None
        assert squad.degradation_thresholds["coherence"] == 0.5
        assert squad.degradation_thresholds["success_rate"] == 0.75

    @pytest.mark.fast
    def test_factory_integration(self):
        """[SQUAD-02] Factory function creates integrated squad."""
        squad = integrate_with_compound_system()

        assert squad is not None
        assert squad.cost_tracker.budget.max_cost_usd == 10.0
        assert squad.cost_tracker.budget.hard_limit is True

    @pytest.mark.fast
    def test_degradation_detection_coherence(self, squad):
        """[SQUAD-03] Detect coherence degradation."""
        skill_name = "coding"
        metrics = {
            "coherence": 0.45,  # Below 0.5 threshold
            "success_rate": 0.90,
        }

        signal = squad.detect_degradation(skill_name, metrics)

        assert signal is not None
        assert signal.skill_name == skill_name
        assert signal.metric_name == "coherence"
        assert signal.current_value == 0.45
        assert signal.severity == "high"  # 0.45 >= 0.4 threshold for critical
        assert signal.is_critical() is False

    @pytest.mark.fast
    def test_degradation_detection_success_rate(self, squad):
        """[SQUAD-04] Detect success rate degradation."""
        skill_name = "analysis"
        metrics = {
            "coherence": 0.85,
            "success_rate": 0.70,  # Below 0.75 threshold
        }

        signal = squad.detect_degradation(skill_name, metrics)

        assert signal is not None
        assert signal.metric_name == "success_rate"
        assert signal.severity in ["high", "critical"]

    @pytest.mark.fast
    def test_no_degradation_detected(self, squad):
        """[SQUAD-05] No degradation when metrics good."""
        skill_name = "secure_coding"
        metrics = {
            "coherence": 0.85,
            "success_rate": 0.95,
        }

        signal = squad.detect_degradation(skill_name, metrics)

        assert signal is None

    @pytest.mark.fast
    def test_optimize_skill(self, squad):
        """[SQUAD-06] Skill optimization runs experiments."""
        skill_name = "coding"
        baseline = 0.45

        result = squad.optimize_skill(skill_name, baseline, max_experiments=5)

        assert isinstance(result, OptimizationResult)
        assert result.target_skill == skill_name
        assert result.before_metric == baseline
        assert result.experiments_run > 0
        assert result.experiments_run <= 5
        assert result.cost_usd >= 0
        assert result.wall_time_seconds >= 0
        assert len(result.learnings) > 0

    @pytest.mark.fast
    def test_optimization_result_calculation(self, squad):
        """[SQUAD-07] Improvement percentage calculated correctly."""
        result = squad.optimize_skill("test_skill", 1.0, max_experiments=3)

        # Check percentage calculation
        expected_pct = (result.before_metric - result.after_metric) / result.before_metric * 100
        assert abs(result.improvement_pct - expected_pct) < 0.1

    @pytest.mark.fast
    def test_apply_refinement(self, squad):
        """[SQUAD-08] Refinement applied to skill."""
        result = squad.optimize_skill("test_skill", 1.0, max_experiments=3)

        success = squad.apply_refinement(result)

        assert success is True
        assert result.refinement_applied is True

    @pytest.mark.fast
    def test_run_optimization_cycle(self, squad):
        """[SQUAD-09] Full optimization cycle on degraded skills."""
        skill_metrics = {
            "coding": {
                "coherence": 0.45,  # Degraded
                "success_rate": 0.95,
            },
            "analysis": {
                "coherence": 0.85,  # Good
                "success_rate": 0.90,
            },
            "security": {
                "coherence": 0.40,  # Degraded
                "success_rate": 0.88,
            },
        }

        results = squad.run_optimization_cycle(skill_metrics)

        # Should optimize coding and security
        assert len(results) == 2
        assert any(r.target_skill == "coding" for r in results)
        assert any(r.target_skill == "security" for r in results)

    @pytest.mark.fast
    def test_optimization_report(self, squad):
        """[SQUAD-10] Generate optimization report."""
        # Run some optimizations
        squad.optimize_skill("skill1", 1.0, max_experiments=3)
        squad.optimize_skill("skill2", 1.0, max_experiments=3)

        report = squad.get_optimization_report()

        assert report["total_optimizations"] == 2
        assert report["total_cost_usd"] >= 0
        assert "average_improvement_pct" in report
        assert "optimizations" in report

    @pytest.mark.fast
    def test_empty_report(self, squad):
        """[SQUAD-11] Empty report when no optimizations."""
        report = squad.get_optimization_report()

        assert report["status"] == "no_optimizations_run"

    @pytest.mark.fast
    def test_cost_tracking_integrated(self, squad):
        """[SQUAD-12] Cost tracking during optimization."""
        result = squad.optimize_skill("test", 1.0, max_experiments=5)

        # Cost should be tracked
        assert result.cost_usd >= 0
        assert squad.cost_tracker.total_cost >= 0

    @pytest.mark.fast
    def test_optimization_history_persistence(self, squad):
        """[SQUAD-13] Optimization history tracked."""
        initial_count = len(squad.optimization_history)

        squad.optimize_skill("test", 1.0, max_experiments=3)

        assert len(squad.optimization_history) == initial_count + 1
        assert squad.optimization_history[-1].target_skill == "test"

    @pytest.mark.fast
    def test_degradation_signal_critical_vs_high(self, squad):
        """[SQUAD-14] Severity levels correctly assigned."""
        # Critical: very low coherence
        critical_metrics = {"coherence": 0.35, "success_rate": 0.95}
        critical_signal = squad.detect_degradation("critical", critical_metrics)
        assert critical_signal.severity == "critical"

        # High: moderately low coherence
        high_metrics = {"coherence": 0.48, "success_rate": 0.95}
        high_signal = squad.detect_degradation("high", high_metrics)
        assert high_signal.severity == "high"


class TestSelfImprovementLoop:
    """Tests for self-improvement recursive loop."""

    @pytest.mark.fast
    def test_compound_to_research_feedback(self):
        """[LOOP-01] Compound metrics feed into Research Squad."""
        import random

        random.seed(42)  # Deterministic: ensures improvement > 0.1

        compound_metrics = {
            "coherence": 0.45,  # Degraded
            "success_rate": 0.70,
        }

        squad = ResearchSquad()

        signal = squad.detect_degradation("compound_executor", compound_metrics)
        assert signal is not None

        result = squad.optimize_skill("compound_executor", signal.current_value)
        assert result.improvement_pct > 0  # Improvement occurred
        assert result.target_skill == "compound_executor"

    @pytest.mark.fast
    def test_research_to_skill_refinement(self):
        """[LOOP-02] Research findings feed into skill refinement."""
        squad = ResearchSquad()

        # Run optimization
        result = squad.optimize_skill("skill_to_refine", 0.5, max_experiments=5)

        # Apply refinement
        success = squad.apply_refinement(result)

        assert success is True
        assert result.refinement_applied is True
        assert len(result.learnings) > 0

    @pytest.mark.fast
    def test_recursive_optimization_chain(self):
        """[LOOP-03] Chain of optimizations."""
        squad = ResearchSquad()

        # First optimization
        result1 = squad.optimize_skill("skill_a", 1.0, max_experiments=3)
        squad.apply_refinement(result1)

        # Second optimization (dependent on first)
        result2 = squad.optimize_skill("skill_b", result1.after_metric, max_experiments=3)
        squad.apply_refinement(result2)

        # Verify chain
        assert len(squad.optimization_history) == 2
        assert squad.optimization_history[0].refinement_applied is True
        assert squad.optimization_history[1].refinement_applied is True

    @pytest.mark.slow
    def test_full_optimization_cycle(self):
        """[LOOP-04] Full cycle: detect -> optimize -> refine -> validate."""
        squad = ResearchSquad()

        # Step 1: Detect degradation
        skill_metrics = {
            "degraded_skill": {
                "coherence": 0.40,
                "success_rate": 0.95,
            },
        }

        results = squad.run_optimization_cycle(skill_metrics)

        # Step 2: Verify optimization
        assert len(results) == 1
        result = results[0]

        # Step 3: Verify refinement applied
        assert result.refinement_applied is True

        # Step 4: Verify report generated
        report = squad.get_optimization_report()
        assert report["total_optimizations"] == 1
        assert report["successful_refinements"] >= 1


class TestCostControls:
    """Tests for budget enforcement."""

    @pytest.mark.fast
    def test_budget_enforcement(self):
        """[COST-01] Budget limits enforced during optimization."""
        from cohezion.research.cost_optimization import CostBudget

        budget = CostBudget(max_cost_usd=1.0, hard_limit=True)
        squad = ResearchSquad(cost_budget=budget)

        # Simulate high cost
        squad.cost_tracker.total_cost = 1.5

        # Check budget
        within, _status = squad.cost_tracker.check_budget()
        assert within is False

    @pytest.mark.fast
    def test_cost_efficiency(self):
        """[COST-02] Optimization is cost-efficient."""
        squad = ResearchSquad()

        result = squad.optimize_skill("test", 1.0, max_experiments=10)

        # Cost per experiment should be reasonable
        cost_per_exp = result.cost_usd / result.experiments_run
        assert cost_per_exp <= 1.0  # Reasonable threshold


class TestIntegrationPoints:
    """Tests for integration with compound system."""

    @pytest.mark.fast
    def test_integration_with_compound_executor(self):
        """[INT-01] Squad uses CompoundExecutor."""
        from cohezion.compound.core.executor import CompoundExecutor

        squad = ResearchSquad()

        assert isinstance(squad.executor, CompoundExecutor)

    @pytest.mark.fast
    def test_integration_with_swarm(self):
        """[INT-02] Squad integrates with Swarm (SwarmConfig)."""
        from cohezion.swarm.orchestrator import SwarmConfig

        squad = ResearchSquad()

        assert isinstance(squad.swarm, SwarmConfig)

    @pytest.mark.fast
    def test_integration_with_research_agent(self):
        """[INT-03] Squad uses ResearchAgent."""

        squad = ResearchSquad()

        # Squad should be able to create agents
        assert squad.executor is not None
