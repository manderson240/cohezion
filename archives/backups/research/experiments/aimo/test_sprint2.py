"""
Sprint 2 Integration Tests - Reasoning Swarm Development

Tests:
- Story 2.1: Specialist routing
- Story 2.2: Adversarial review loop
- Story 2.3: FLUME proof navigator
"""

import pytest
from flume_navigator import FLUMEProfilerNavigator
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


class TestStory21SpecialistRouting:
    """Tests for specialist routing (Story 2.1)."""

    @pytest.mark.fast
    def test_plan_journey_algebra_problem(self):
        """Test routing assigns Algebraist for algebra problems."""
        coordinator = SwarmCoordinator()
        problem = "Solve for x: x^2 + 3x + 2 = 0"

        task = coordinator.plan_journey("test1", problem)

        assert "Algebraist" in task.assigned_specialists
        assert len(task.assigned_specialists) >= 2
        assert task.state.algebra > 0.2

    @pytest.mark.fast
    def test_plan_journey_geometry_problem(self):
        """Test routing assigns Geometer for geometry problems."""
        coordinator = SwarmCoordinator()
        problem = "Find the area of a triangle with base 5 and height 10"

        task = coordinator.plan_journey("test2", problem)

        assert "Geometer" in task.assigned_specialists
        assert task.state.geometry > 0.2

    @pytest.mark.fast
    def test_plan_journey_number_theory_problem(self):
        """Test routing assigns NumberTheorist for number theory problems."""
        coordinator = SwarmCoordinator()
        problem = "Find the remainder when 2^100 is divided by 7"

        task = coordinator.plan_journey("test3", problem)

        assert "NumberTheorist" in task.assigned_specialists
        assert task.state.number_theory > 0.2

    @pytest.mark.fast
    def test_plan_journey_combinatorics_problem(self):
        """Test routing assigns Combinatorist for counting problems."""
        coordinator = SwarmCoordinator()
        problem = "How many ways can 5 people be arranged in a row?"

        task = coordinator.plan_journey("test4", problem)

        assert "Combinatorist" in task.assigned_specialists
        assert task.state.combinatorics > 0.2

    @pytest.mark.fast
    def test_plan_journey_fallback_minimum_two_specialists(self):
        """Test routing always assigns at least 2 specialists."""
        coordinator = SwarmCoordinator()
        problem = "A general math problem"

        task = coordinator.plan_journey("test5", problem)

        assert len(task.assigned_specialists) >= 2


class TestStory23FLUMENavigator:
    """Tests for FLUME proof navigator (Story 2.3)."""

    @pytest.mark.fast
    def test_encode_reasoning_chain(self):
        """Test encoding of reasoning chain into thought vectors."""
        navigator = FLUMEProfilerNavigator()
        reasoning = """
        Step 1: Let x be the unknown variable.
        Step 2: Set up the equation x^2 + 3x + 2 = 0.
        Step 3: Factor as (x+1)(x+2) = 0.
        Step 4: Solutions are x = -1, -2.
        """

        chain = navigator.encode_reasoning_chain(reasoning)

        assert len(chain) >= 4
        assert all(v.latent_vector.shape == (512,) for v in chain)
        assert all(0.0 <= v.coherence <= 1.0 for v in chain)

    @pytest.mark.fast
    def test_compute_drift_identical_chains(self):
        """Test drift is near zero for identical chains."""
        navigator = FLUMEProfilerNavigator()
        reasoning = "Step 1: x = 1\nStep 2: y = 2\nStep 3: x + y = 3"

        chain1 = navigator.encode_reasoning_chain(reasoning)
        chain2 = navigator.encode_reasoning_chain(reasoning)

        drift = navigator.compute_drift(chain1, chain2)

        # Same text should have very low drift (not zero due to hash randomness)
        assert drift < 0.5  # Below stability threshold

    @pytest.mark.fast
    def test_compute_drift_different_chains(self):
        """Test drift is higher for different reasoning."""
        navigator = FLUMEProfilerNavigator()
        reasoning1 = "Algebra: solve x^2 = 4, x = 2"
        reasoning2 = "Geometry: area = pi * r^2"

        chain1 = navigator.encode_reasoning_chain(reasoning1)
        chain2 = navigator.encode_reasoning_chain(reasoning2)

        drift = navigator.compute_drift(chain1, chain2)

        # Different domains should have measurable drift
        assert drift > 0.1

    @pytest.mark.fast
    def test_identify_stable_trajectory(self):
        """Test selecting most stable chain from multiple runs."""
        navigator = FLUMEProfilerNavigator()

        # Create chains with varying coherence
        chain1 = navigator.encode_reasoning_chain(
            "High coherence: therefore, thus, implies \\boxed{1}"
        )
        chain2 = navigator.encode_reasoning_chain("Low coherence: random text")
        chain3 = navigator.encode_reasoning_chain("Medium: therefore \\boxed{2}")

        chains = [chain1, chain2, chain3]
        stable_idx = navigator.identify_stable_trajectory(chains)

        # Chain 1 should have highest coherence
        assert stable_idx == 0

    @pytest.mark.fast
    def test_check_stability_below_threshold(self):
        """Test stability check with drift below threshold."""
        navigator = FLUMEProfilerNavigator()
        reasoning = "Step 1: x = 1\nStep 2: y = 2"

        chain1 = navigator.encode_reasoning_chain(reasoning)
        chain2 = navigator.encode_reasoning_chain(reasoning)

        stable = navigator.check_stability(chain1, chain2)

        # Same reasoning should be stable
        assert stable == True


class TestKnowerAuditorIntegration:
    """Tests for Knower auditor integration."""

    @pytest.mark.fast
    def test_audit_runs_consistent(self):
        """Test audit detects consistent runs."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs(
            [47, 47], ["Long reasoning chain A...", "Long reasoning chain B..."]
        )

        assert result["consistent"] is True
        assert result["stability_score"] == 1.0
        assert result["action"] == "COMMIT"
        assert result["final_answer"] == 47

    @pytest.mark.fast
    def test_audit_runs_inconsistent(self):
        """Test audit detects inconsistent runs."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([47, 42], ["Long reasoning...", "Short proof."])

        assert result["consistent"] is False
        assert result["stability_score"] < 1.0
        assert result["action"] == "TIE_BREAKER"

    @pytest.mark.fast
    def test_resolve_tie_majority_vote(self):
        """Test tie-breaker with majority voting."""
        auditor = KnowerAuditor()

        # Two agree, one different
        result = auditor.resolve_tie(47, 47, 42)
        assert result == 47

        # All different (first wins by count)
        result = auditor.resolve_tie(47, 42, 42)
        assert result == 42


class TestSprint2Integration:
    """End-to-end integration test for Sprint 2 components."""

    @pytest.mark.fast
    def test_full_reasoning_pipeline(self):
        """Test complete pipeline: routing → reasoning → audit."""
        # 1. Route problem
        coordinator = SwarmCoordinator()
        problem = "Find x: x^2 = 4"
        task = coordinator.plan_journey("int1", problem)

        assert len(task.assigned_specialists) >= 2
        assert "Algebraist" in task.assigned_specialists

        # 2. Simulate reasoning chains (mock)
        reasoning1 = "Step 1: x^2 = 4 implies x = 2 or x = -2. \\boxed{2}"
        reasoning2 = "Step 1: sqrt(4) = 2. \\boxed{2}"

        # 3. Encode with FLUME
        navigator = FLUMEProfilerNavigator()
        chain1 = navigator.encode_reasoning_chain(reasoning1)
        chain2 = navigator.encode_reasoning_chain(reasoning2)

        # 4. Check stability
        stable = navigator.check_stability(chain1, chain2)

        # 5. Audit results
        auditor = KnowerAuditor()
        result = auditor.audit_runs([2, 2], [reasoning1, reasoning2])

        assert result["consistent"] is True
        assert result["final_answer"] == 2


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
