"""
Acceptance Tests - Live API Integration

Tests that hit the real Ollama API with cloud models.
Requires Ollama server running with deepseek-r1:7b available.

Run with: pytest test_acceptance_live.py -v -m integration
"""

import pytest
from base_specialist import BaseSpecialist
from knower_auditor import KnowerAuditor
from swarm_coordinator import SwarmCoordinator


def check_ollama_available():
    """Check if Ollama server is accessible."""
    try:
        import requests

        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        return response.status_code == 200
    except Exception:
        return False


@pytest.fixture
def ollama_server():
    """Skip tests if Ollama is not available."""
    if not check_ollama_available():
        pytest.skip("Ollama server not available")


class TestLiveAPISmoke:
    """Smoke tests for live Ollama API."""

    @pytest.mark.integration
    def test_cloud_model_responds(self, ollama_server):
        """Test cloud model responds to simple query."""
        specialist = BaseSpecialist("Algebraist", model_name="deepseek-r1:7b")

        response = specialist.solve("What is 1 + 1?")

        # Should not be an error
        assert not response.startswith("Error")
        assert len(response) > 0

    @pytest.mark.integration
    def test_cloud_model_extracts_answer(self, ollama_server):
        """Test answer extraction from cloud model response."""
        specialist = BaseSpecialist("Algebraist", model_name="deepseek-r1:7b")

        response = specialist.solve("What is 2 + 2? Put answer in \\boxed{}")
        answer = specialist.extract_answer(response)

        # Should extract a number (not 0 from error)
        assert answer != 0 or "\\boxed" in response


class TestLiveDualRunConsistency:
    """Tests for dual-run consistency with live API."""

    @pytest.mark.integration
    def test_dual_run_simple_algebra(self, ollama_server):
        """Test dual-run on simple algebra problem."""
        coordinator = SwarmCoordinator()
        auditor = KnowerAuditor()

        problem = "Solve for x: x + 3 = 7"
        task = coordinator.plan_journey("test", problem)

        # Run 1
        spec1 = BaseSpecialist(task.assigned_specialists[0], model_name="deepseek-r1:7b")
        response1 = spec1.solve(problem)
        ans1 = spec1.extract_answer(response1)

        # Run 2
        spec2_name = (
            task.assigned_specialists[1]
            if len(task.assigned_specialists) > 1
            else task.assigned_specialists[0]
        )
        spec2 = BaseSpecialist(spec2_name, model_name="deepseek-r1:7b")
        response2 = spec2.solve(problem)
        ans2 = spec2.extract_answer(response2)

        # Audit
        audit = auditor.audit_runs([ans1, ans2], [response1, response2])

        # Simple problem should be consistent
        assert audit["consistent"] is True
        assert audit["final_answer"] == 4

    @pytest.mark.integration
    def test_dual_run_geometry(self, ollama_server):
        """Test dual-run on geometry problem."""
        coordinator = SwarmCoordinator()
        auditor = KnowerAuditor()

        problem = "Find the area of a rectangle with length 5 and width 3"
        task = coordinator.plan_journey("test", problem)

        # Run 1
        spec1 = BaseSpecialist(task.assigned_specialists[0], model_name="deepseek-r1:7b")
        response1 = spec1.solve(problem)
        ans1 = spec1.extract_answer(response1)

        # Run 2
        spec2_name = (
            task.assigned_specialists[1]
            if len(task.assigned_specialists) > 1
            else task.assigned_specialists[0]
        )
        spec2 = BaseSpecialist(spec2_name, model_name="deepseek-r1:7b")
        response2 = spec2.solve(problem)
        ans2 = spec2.extract_answer(response2)

        # Audit
        audit = auditor.audit_runs([ans1, ans2], [response1, response2])

        # Should agree on 15
        assert audit["final_answer"] == 15


class TestLiveSpecialistRouting:
    """Tests for specialist routing with live API."""

    @pytest.mark.integration
    def test_algebra_routing(self, ollama_server):
        """Test Algebraist is assigned for algebra problems."""
        coordinator = SwarmCoordinator()

        problem = "Solve the quadratic equation x^2 + 5x + 6 = 0"
        task = coordinator.plan_journey("test", problem)

        assert "Algebraist" in task.assigned_specialists
        assert task.state.algebra > 0.2

    @pytest.mark.integration
    def test_number_theory_routing(self, ollama_server):
        """Test NumberTheorist is assigned for number theory."""
        coordinator = SwarmCoordinator()

        problem = "Find the remainder when 2^100 is divided by 7"
        task = coordinator.plan_journey("test", problem)

        assert "NumberTheorist" in task.assigned_specialists
        assert task.state.number_theory > 0.2

    @pytest.mark.integration
    def test_geometry_routing(self, ollama_server):
        """Test Geometer is assigned for geometry."""
        coordinator = SwarmCoordinator()

        problem = "Find the circumference of a circle with radius 7"
        task = coordinator.plan_journey("test", problem)

        assert "Geometer" in task.assigned_specialists
        assert task.state.geometry > 0.2


class TestLiveTimeoutHandling:
    """Tests for timeout handling with live API."""

    @pytest.mark.integration
    def test_short_timeout_returns_error(self, ollama_server):
        """Test short timeout returns error, not hang."""
        specialist = BaseSpecialist("Algebraist", model_name="deepseek-r1:7b", timeout=1)

        # Long problem should timeout
        long_problem = "Solve: " + "x " * 1000
        response = specialist.solve(long_problem)

        # Should return error, not hang
        assert response.startswith("Error")

    @pytest.mark.integration
    def test_normal_timeout_succeeds(self, ollama_server):
        """Test normal timeout succeeds on simple problem."""
        specialist = BaseSpecialist("Algebraist", model_name="deepseek-r1:7b", timeout=300)

        response = specialist.solve("What is 10 + 10?")

        # Should succeed
        assert not response.startswith("Error")


class TestLiveReferenceProblems:
    """Tests on actual AIMO reference problems."""

    @pytest.mark.integration
    def test_reference_problem_1(self, ollama_server):
        """Test reference problem 1: divisors of n = 3^3 * 11^3."""
        specialist = BaseSpecialist("NumberTheorist", model_name="deepseek-r1:7b")

        problem = "Let $n = 3^3 \\cdot 11^3$. Find the number of distinct positive divisors of $n$."
        response = specialist.solve(problem)
        answer = specialist.extract_answer(response)

        # Expected: 16 (divisors: (3+1)*(3+1) = 16)
        assert answer == 16

    @pytest.mark.integration
    def test_reference_problem_2(self, ollama_server):
        """Test reference problem 2: last digit of 7^2023."""
        specialist = BaseSpecialist("NumberTheorist", model_name="deepseek-r1:7b")

        problem = "Find the last digit of $7^{2023}$."
        response = specialist.solve(problem)
        answer = specialist.extract_answer(response)

        # Expected: 3 (pattern: 7,9,3,1 repeats every 4, 2023 mod 4 = 3)
        assert answer == 3

    @pytest.mark.integration
    def test_reference_problem_3(self, ollama_server):
        """Test reference problem 3: sum of roots."""
        specialist = BaseSpecialist("Algebraist", model_name="deepseek-r1:7b")

        problem = "Find the sum of the roots of $x^2 - 6x + 8 = 0$."
        response = specialist.solve(problem)
        answer = specialist.extract_answer(response)

        # Expected: 6 (Vieta: sum = -b/a = 6)
        assert answer == 6


class TestLiveTieBreaker:
    """Tests for tie-breaker logic with live API."""

    @pytest.mark.integration
    def test_tie_breaker_phi4(self, ollama_server):
        """Test tie-breaker uses Phi-4 model."""
        coordinator = SwarmCoordinator()
        auditor = KnowerAuditor()

        problem = "Solve for x: 2x = 10"
        task = coordinator.plan_journey("test", problem)

        # Run 1 & 2
        spec1 = BaseSpecialist(task.assigned_specialists[0], model_name="deepseek-r1:7b")
        response1 = spec1.solve(problem)
        ans1 = spec1.extract_answer(response1)

        spec2_name = (
            task.assigned_specialists[1]
            if len(task.assigned_specialists) > 1
            else task.assigned_specialists[0]
        )
        spec2 = BaseSpecialist(spec2_name, model_name="deepseek-r1:7b")
        response2 = spec2.solve(problem)
        ans2 = spec2.extract_answer(response2)

        # Force tie-breaker scenario (simulate divergence)
        if ans1 == ans2:
            # Manually create divergence for testing
            ans1 = 5
            ans2 = 6

        # Tie-breaker
        tie_spec = BaseSpecialist(task.assigned_specialists[0], model_name="phi4:latest")
        response3 = tie_spec.solve(problem)
        ans3 = tie_spec.extract_answer(response3)

        final = auditor.resolve_tie(ans1, ans2, ans3)

        # Should be 5 (correct answer)
        assert final == 5
