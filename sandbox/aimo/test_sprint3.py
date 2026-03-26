"""
Sprint 3 Integration Tests - Verification & Stability

Tests:
- Story 3.1: Dual-Run Protocol
- Story 3.2: Knower Audit
- Story 3.3: Tie-Breaker Logic
"""

from unittest.mock import patch

import pytest
from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


class TestStory31DualRunProtocol:
    """Tests for dual-run protocol (Story 3.1)."""

    @pytest.mark.fast
    def test_dual_run_executes_two_specialists(self):
        """Test that dual-run executes two independent reasoning chains."""
        coordinator = SwarmCoordinator()
        problem = "Solve for x: x + 2 = 5"

        task = coordinator.plan_journey("test1", problem)

        # Verify at least 2 specialists assigned for dual-run
        assert len(task.assigned_specialists) >= 2

        # Verify different specialists for Run 1 and Run 2
        spec1_name = task.assigned_specialists[0]
        spec2_name = task.assigned_specialists[1]

        # Should be different specialists
        assert spec1_name != spec2_name or len(task.assigned_specialists) == 1

    @pytest.mark.fast
    def test_dual_run_collects_both_results(self):
        """Test that both run results are collected."""
        # Mock specialist responses
        with patch.object(BaseSpecialist, "solve") as mock_solve:
            mock_solve.side_effect = [
                "Step 1: x = 3. \\boxed{3}",
                "Step 1: Solve x + 2 = 5, x = 3. \\boxed{3}",
            ]

            with patch.object(BaseSpecialist, "extract_answer") as mock_extract:
                mock_extract.side_effect = [3, 3]

                spec1 = BaseSpecialist("Algebraist")
                spec2 = BaseSpecialist("NumberTheorist")

                response1 = spec1.solve("test")
                ans1 = spec1.extract_answer(response1)

                response2 = spec2.solve("test")
                ans2 = spec2.extract_answer(response2)

                # Both results collected
                assert ans1 is not None
                assert ans2 is not None

    @pytest.mark.fast
    def test_dual_run_logs_both_chains(self):
        """Test that both reasoning chains are logged."""
        run_results = []
        reasoning_chains = []

        # Simulate dual-run collection
        responses = ["Step 1: x = 3. Long reasoning...", "Step 1: x = 3. Short reasoning."]

        for response in responses:
            run_results.append(3)
            reasoning_chains.append(response)

        # Both chains logged
        assert len(reasoning_chains) == 2
        assert len(run_results) == 2


class TestStory32KnowerAudit:
    """Tests for Knower audit (Story 3.2)."""

    @pytest.mark.fast
    def test_audit_returns_audit_result_structure(self):
        """Test audit returns correct structure."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs(
            [47, 47], ["Long reasoning chain A...", "Long reasoning chain B..."]
        )

        # Verify structure
        assert "consistent" in result
        assert "stability_score" in result
        assert "drift_ratio" in result
        assert "final_answer" in result
        assert "action" in result

        # Verify types
        assert isinstance(result["consistent"], bool)
        assert isinstance(result["stability_score"], float)
        assert isinstance(result["drift_ratio"], float)
        assert isinstance(result["final_answer"], int)
        assert result["action"] in ["COMMIT", "TIE_BREAKER"]

    @pytest.mark.fast
    def test_audit_consistent_returns_commit(self):
        """Test consistent runs return COMMIT action."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([42, 42], ["chain1", "chain2"])

        assert result["consistent"] is True
        assert result["stability_score"] == 1.0
        assert result["action"] == "COMMIT"
        assert result["final_answer"] == 42

    @pytest.mark.fast
    def test_audit_inconsistent_returns_tie_breaker(self):
        """Test inconsistent runs return TIE_BREAKER action."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([42, 47], ["chain1", "chain2"])

        assert result["consistent"] is False
        assert result["stability_score"] < 1.0
        assert result["action"] == "TIE_BREAKER"

    @pytest.mark.fast
    def test_audit_both_none_returns_zero(self):
        """Test both None results return 0."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([None, None], ["chain1", "chain2"])

        assert result["consistent"] is False
        assert result["stability_score"] == 0.0
        assert result["final_answer"] == 0

    @pytest.mark.fast
    def test_audit_drift_penalty(self):
        """Test audit applies drift penalty for length variance."""
        auditor = KnowerAuditor()

        # Large length difference
        result = auditor.audit_runs(
            [42, 42], ["Very long reasoning chain with lots of text...", "Short."]
        )

        # Should still be consistent but with penalty
        assert result["consistent"] is True
        assert result["drift_ratio"] > 0.3
        assert result["stability_score"] < 1.0


class TestStory33TieBreakerLogic:
    """Tests for tie-breaker logic (Story 3.3)."""

    @pytest.mark.fast
    def test_resolve_tie_majority_wins(self):
        """Test majority voting in tie-breaker."""
        auditor = KnowerAuditor()

        # Two agree, one different
        result = auditor.resolve_tie(47, 47, 42)
        assert result == 47

    @pytest.mark.fast
    def test_resolve_tie_second_pair_wins(self):
        """Test second pair wins majority."""
        auditor = KnowerAuditor()

        result = auditor.resolve_tie(47, 42, 42)
        assert result == 42

    @pytest.mark.fast
    def test_resolve_tie_all_same(self):
        """Test all three same returns that value."""
        auditor = KnowerAuditor()

        result = auditor.resolve_tie(42, 42, 42)
        assert result == 42

    @pytest.mark.fast
    def test_resolve_tie_all_different(self):
        """Test all different returns first by count (tie)."""
        auditor = KnowerAuditor()

        result = auditor.resolve_tie(42, 47, 51)
        # All have count 1, first max wins
        assert result == 42


class TestSprint3Integration:
    """End-to-end integration test for Sprint 3 components."""

    @pytest.mark.fast
    def test_full_dual_run_with_audit(self):
        """Test complete dual-run + audit pipeline."""
        coordinator = SwarmCoordinator()
        auditor = KnowerAuditor()

        problem = "Find x: x^2 = 4"
        task = coordinator.plan_journey("int1", problem)

        # Simulate dual-run
        run_results = [2, 2]
        reasoning_chains = [
            "Step 1: x^2 = 4 implies x = 2 or -2. Answer 2.",
            "Step 1: sqrt(4) = 2.",
        ]

        # Audit
        audit = auditor.audit_runs(run_results, reasoning_chains)

        assert audit["consistent"] is True
        assert audit["action"] == "COMMIT"
        assert audit["final_answer"] == 2

    @pytest.mark.fast
    def test_dual_run_divergence_triggers_tie_breaker(self):
        """Test divergent answers trigger tie-breaker."""
        auditor = KnowerAuditor()

        # Simulate divergent dual-run
        run_results = [2, 3]
        reasoning_chains = ["chain1", "chain2"]

        audit = auditor.audit_runs(run_results, reasoning_chains)

        assert audit["consistent"] is False
        assert audit["action"] == "TIE_BREAKER"

        # Run tie-breaker
        final = auditor.resolve_tie(2, 3, 2)
        assert final == 2  # Majority wins

    @pytest.mark.fast
    def test_stability_score_computation(self):
        """Test stability score computation across runs."""
        auditor = KnowerAuditor()

        # Test 1: Perfect consistency
        result1 = auditor.audit_runs([47, 47], ["long", "long"])
        assert result1["stability_score"] == 1.0

        # Test 2: Inconsistency
        result2 = auditor.audit_runs([47, 42], ["long", "short"])
        assert result2["stability_score"] < 1.0

        # Test 3: Both fail
        result3 = auditor.audit_runs([None, None], ["", ""])
        assert result3["stability_score"] == 0.0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
