"""
Epic 6 Unit Tests - Testing & Validation (Mocked)

Tests the benchmark pipeline logic without actual Ollama calls.
Validates:
- Accuracy computation
- Stability computation
- Performance profiling
- Tie-breaker logic
"""

import json
from pathlib import Path
from unittest.mock import Mock, patch

import pytest
from flume_navigator import FLUMEProfilerNavigator
from knower_auditor import KnowerAuditor
from performance_profiler import PerformanceProfiler
from swarm_coordinator import SwarmCoordinator


class TestEpic6Pipeline:
    """Test Epic 6 pipeline logic with mocked LLM calls."""

    @pytest.mark.fast
    def test_benchmark_runner_initialization(self):
        """Test benchmark runner loads reference problems."""
        from epic6_benchmark_runner import Epic6BenchmarkRunner

        runner = Epic6BenchmarkRunner("reference_problems.json")

        assert len(runner.reference_problems) == 4
        assert runner.reference_problems[0]["id"] == "aimo3_ref_1"
        assert runner.reference_problems[0]["answer"] == 16

    @pytest.mark.fast
    def test_coordinator_routing(self):
        """Test specialist routing on reference problems."""
        coordinator = SwarmCoordinator()

        problem = "Let $n = 3^3 \\cdot 11^3$. Find the number of distinct positive divisors."
        task = coordinator.plan_journey("test", problem)

        assert len(task.assigned_specialists) >= 2
        assert task.state.number_theory > 0.2

    @pytest.mark.fast
    def test_knower_audit_consistent(self):
        """Test Knower audit with consistent answers."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([16, 16], ["reasoning1", "reasoning2"])

        assert result["consistent"] is True
        assert result["stability_score"] == 1.0
        assert result["action"] == "COMMIT"
        assert result["final_answer"] == 16

    @pytest.mark.fast
    def test_knower_audit_inconsistent(self):
        """Test Knower audit with divergent answers."""
        auditor = KnowerAuditor()

        result = auditor.audit_runs([16, 17], ["reasoning1", "reasoning2"])

        assert result["consistent"] is False
        assert result["action"] == "TIE_BREAKER"

    @pytest.mark.fast
    def test_tie_breaker_majority(self):
        """Test tie-breaker with majority voting."""
        auditor = KnowerAuditor()

        result = auditor.resolve_tie(16, 17, 16)
        assert result == 16

    @pytest.mark.fast
    def test_flume_stability_check(self):
        """Test FLUME stability check."""
        flume = FLUMEProfilerNavigator()

        reasoning1 = "Step 1: x = 1\nStep 2: y = 2"
        reasoning2 = "Step 1: x = 1\nStep 2: y = 2"

        chain1 = flume.encode_reasoning_chain(reasoning1)
        chain2 = flume.encode_reasoning_chain(reasoning2)

        stable = flume.check_stability(chain1, chain2)
        assert stable == True

    @pytest.mark.fast
    def test_performance_profiler_budget(self):
        """Test performance profiler tracks time budget."""
        profiler = PerformanceProfiler()

        timings = profiler.start_problem("test")
        timings = profiler.end_routing(timings)
        timings = profiler.end_run1(timings)
        timings = profiler.end_run2(timings)
        timings = profiler.end_audit(timings)

        profiler.record_metrics("test", timings)

        budget = profiler.check_time_budget()
        assert budget["problems_solved"] == 1
        assert budget["remaining_problems"] == 109

    @pytest.mark.fast
    def test_mock_benchmark_run(self):
        """Test full benchmark pipeline with mocked LLM."""
        from epic6_benchmark_runner import Epic6BenchmarkRunner

        runner = Epic6BenchmarkRunner("reference_problems.json")

        # Mock the BaseSpecialist to return correct answers
        with patch("epic6_benchmark_runner.BaseSpecialist") as MockSpecialist:
            mock_instance = Mock()
            mock_instance.solve.return_value = "Step 1: The answer is \\boxed{16}"
            mock_instance.extract_answer.return_value = 16
            MockSpecialist.return_value = mock_instance

            # Run single problem
            problem = runner.reference_problems[0]
            result = runner._run_single_problem(problem)

            assert result.problem_id == problem["id"]
            assert result.expected_answer == 16
            assert result.actual_answer == 16
            assert result.correct is True

    @pytest.mark.fast
    def test_summary_computation(self):
        """Test summary metrics computation."""
        from epic6_benchmark_runner import BenchmarkResult, Epic6BenchmarkRunner

        runner = Epic6BenchmarkRunner.__new__(Epic6BenchmarkRunner)
        runner.results = [
            BenchmarkResult("p1", 16, 16, True, True, 16, 16, False, 10.0, "r1"),
            BenchmarkResult("p2", 47, 47, True, True, 47, 47, False, 10.0, "r2"),
            BenchmarkResult("p3", 84, 84, True, False, 84, 84, False, 10.0, "r3"),
        ]

        summary = runner._compute_summary()

        assert summary["total_problems"] == 3
        assert summary["correct_count"] == 3
        assert summary["accuracy"] == 1.0
        assert summary["stable_count"] == 2
        assert summary["stability_ratio"] == 2 / 3
        assert summary["accuracy_pass"] is True
        assert summary["stability_pass"] is False  # 0.67 < 0.90

    @pytest.mark.fast
    def test_all_targets_met(self):
        """Test all targets met computation."""
        from epic6_benchmark_runner import BenchmarkResult, Epic6BenchmarkRunner

        runner = Epic6BenchmarkRunner.__new__(Epic6BenchmarkRunner)
        runner.results = [
            BenchmarkResult("p1", 16, 16, True, True, 16, 16, False, 100.0, "r1"),
            BenchmarkResult("p2", 47, 47, True, True, 47, 47, False, 100.0, "r2"),
        ]

        summary = runner._compute_summary()

        assert summary["accuracy"] == 1.0
        assert summary["stability_ratio"] == 1.0
        assert summary["avg_time"] == 100.0
        assert summary["all_targets_met"] is True  # All pass

    @pytest.mark.fast
    def test_save_results(self):
        """Test saving results to JSON."""
        from epic6_benchmark_runner import BenchmarkResult, Epic6BenchmarkRunner

        runner = Epic6BenchmarkRunner.__new__(Epic6BenchmarkRunner)
        runner.results = [
            BenchmarkResult("p1", 16, 16, True, True, 16, 16, False, 10.0, "r1"),
        ]

        test_path = "data/test_benchmark_results.json"
        Path(test_path).parent.mkdir(parents=True, exist_ok=True)
        runner.save_results(test_path)

        assert Path(test_path).exists()
        with open(test_path) as f:
            data = json.load(f)
            assert "results" in data
            assert "summary" in data

        # Cleanup
        Path(test_path).unlink()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
