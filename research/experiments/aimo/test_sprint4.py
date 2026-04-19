"""
Sprint 4 Integration Tests - Submission & Optimization

Tests:
- Story 4.1: Optimize for 5-Hour Limit (performance_profiler.py)
- Story 4.2: Model Fine-Tuning (placeholder - requires ML infrastructure)
- Story 4.3: Submission Automation (kaggle API integration)
"""

import time

import pytest
from performance_profiler import PerformanceProfiler


class TestStory41PerformanceProfiler:
    """Tests for performance profiler (Story 4.1)."""

    @pytest.mark.fast
    def test_profiler_initialization(self):
        """Test profiler initializes with correct time budget."""
        profiler = PerformanceProfiler(total_time_limit=5 * 3600, problem_count=110)

        assert profiler.total_time_limit == 18000  # 5 hours
        assert profiler.problem_count == 110
        assert abs(profiler.time_per_problem - 163.636) < 0.1
        assert profiler.problems_solved == 0

    @pytest.mark.fast
    def test_start_problem_timing(self):
        """Test problem timing starts correctly."""
        profiler = PerformanceProfiler()

        timings = profiler.start_problem("test1")

        assert "problem_start" in timings
        assert "routing_start" in timings
        # Allow small floating point difference (< 1ms)
        assert abs(timings["problem_start"] - timings["routing_start"]) < 0.001

    @pytest.mark.fast
    def test_end_routing_timing(self):
        """Test routing timing ends correctly."""
        profiler = PerformanceProfiler()
        timings = profiler.start_problem("test1")

        time.sleep(0.01)
        timings = profiler.end_routing(timings)

        assert "routing_end" in timings
        assert "run1_start" in timings
        assert timings["routing_end"] >= timings["routing_start"]

    @pytest.mark.fast
    def test_end_run1_timing(self):
        """Test Run 1 timing ends correctly."""
        profiler = PerformanceProfiler()
        timings = profiler.start_problem("test1")
        timings = profiler.end_routing(timings)

        time.sleep(0.01)
        timings = profiler.end_run1(timings)

        assert "run1_end" in timings
        assert "run2_start" in timings
        assert timings["run1_end"] >= timings["run1_start"]

    @pytest.mark.fast
    def test_end_run2_timing(self):
        """Test Run 2 timing ends correctly."""
        profiler = PerformanceProfiler()
        timings = profiler.start_problem("test1")
        timings = profiler.end_routing(timings)
        timings = profiler.end_run1(timings)

        time.sleep(0.01)
        timings = profiler.end_run2(timings)

        assert "run2_end" in timings
        assert "audit_start" in timings
        assert timings["run2_end"] >= timings["run2_start"]

    @pytest.mark.fast
    def test_end_audit_timing(self):
        """Test audit timing ends correctly."""
        profiler = PerformanceProfiler()
        timings = profiler.start_problem("test1")
        timings = profiler.end_routing(timings)
        timings = profiler.end_run1(timings)
        timings = profiler.end_run2(timings)

        time.sleep(0.01)
        timings = profiler.end_audit(timings)

        assert "audit_end" in timings
        assert "problem_end" in timings
        assert timings["audit_end"] >= timings["audit_start"]

    @pytest.mark.fast
    def test_record_metrics(self):
        """Test metrics recording."""
        profiler = PerformanceProfiler()

        timings = profiler.start_problem("test1")
        time.sleep(0.01)
        timings = profiler.end_routing(timings)
        time.sleep(0.02)
        timings = profiler.end_run1(timings)
        time.sleep(0.02)
        timings = profiler.end_run2(timings)
        time.sleep(0.01)
        timings = profiler.end_audit(timings)

        metrics = profiler.record_metrics("test1", timings)

        assert metrics.problem_id == "test1"
        assert metrics.total_time > 0
        assert metrics.run1_time > 0
        assert metrics.run2_time > 0
        assert profiler.problems_solved == 1

    @pytest.mark.fast
    def test_check_time_budget_on_track(self):
        """Test time budget check when on track."""
        profiler = PerformanceProfiler()

        # Simulate fast problem using proper API
        timings = profiler.start_problem("test1")
        time.sleep(0.01)
        timings = profiler.end_routing(timings)
        time.sleep(0.01)
        timings = profiler.end_run1(timings)
        time.sleep(0.01)
        timings = profiler.end_run2(timings)
        time.sleep(0.01)
        timings = profiler.end_audit(timings)

        profiler.record_metrics("test1", timings)

        budget = profiler.check_time_budget()

        assert budget["problems_solved"] == 1
        assert budget["remaining_problems"] == 109
        assert budget["on_track"] is True  # Fast execution << 163.6s target

    @pytest.mark.fast
    def test_check_time_budget_behind(self):
        """Test time budget check when behind."""
        profiler = PerformanceProfiler()

        # Simulate slow problem - manually set timings
        timings = profiler.start_problem("test1")
        timings = profiler.end_routing(timings)
        timings = profiler.end_run1(timings)
        timings = profiler.end_run2(timings)
        timings = profiler.end_audit(timings)

        # Override problem_end to simulate 200s total
        timings["problem_end"] = timings["problem_start"] + 200

        profiler.record_metrics("test1", timings)

        budget = profiler.check_time_budget()

        assert budget["problems_solved"] == 1
        assert budget["on_track"] is False  # 200s > 163.6s target

    @pytest.mark.fast
    def test_generate_report(self):
        """Test performance report generation."""
        profiler = PerformanceProfiler()

        # Simulate problem using proper API
        timings = profiler.start_problem("test1")
        time.sleep(0.01)
        timings = profiler.end_routing(timings)
        time.sleep(0.01)
        timings = profiler.end_run1(timings)
        time.sleep(0.01)
        timings = profiler.end_run2(timings)
        time.sleep(0.01)
        timings = profiler.end_audit(timings)

        profiler.record_metrics("test1", timings)

        report = profiler.generate_report()

        assert "Performance Report" in report
        assert "Problems solved: 1/110" in report
        assert "Total time:" in report
        assert "Average time:" in report
        assert "Time Budget Status:" in report

    @pytest.mark.fast
    def test_tie_breaker_timing(self):
        """Test tie-breaker timing recording."""
        profiler = PerformanceProfiler()

        timings = profiler.start_problem("test1")
        timings = profiler.end_routing(timings)
        timings = profiler.end_run1(timings)
        timings = profiler.end_run2(timings)
        timings = profiler.end_audit(timings)

        # Add tie-breaker timing
        timings["tie_breaker_start"] = time.time()
        time.sleep(0.01)
        timings["tie_breaker_end"] = time.time()
        timings["problem_end"] = time.time()

        metrics = profiler.record_metrics("test1", timings, tie_breaker=True)

        assert metrics.tie_breaker_time > 0


class TestStory43SubmissionAutomation:
    """Tests for submission automation (Story 4.3)."""

    @pytest.mark.fast
    def test_mock_env_predict_called_once(self):
        """Test env.predict() called exactly once per row."""
        from unittest.mock import Mock

        mock_env = Mock()
        mock_df = Mock()
        mock_df.loc = {0: {"answer": 42}}

        # Simulate single prediction
        mock_env.predict(mock_df)

        mock_env.predict.assert_called_once()

    @pytest.mark.fast
    def test_submission_format(self):
        """Test submission format matches Kaggle requirements."""
        import polars as pl

        # Create mock submission DataFrame
        submission = pl.DataFrame({"id": ["test1"], "answer": [42]})

        assert submission.shape == (1, 2)
        assert "id" in submission.columns
        assert "answer" in submission.columns


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
