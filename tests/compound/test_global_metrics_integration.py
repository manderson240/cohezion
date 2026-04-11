"""Integration tests for global metrics aggregation with team execution.

Tests how GlobalMetricsAggregator integrates with:
- TeamMetricsAggregator for team-level metrics
- CompoundExecutor for individual executions
- VaultExecutionLogger for knowledge persistence
"""

from __future__ import annotations

import time

import pytest

from cohezion.compound.global_metrics_aggregator import (
    InstanceMetrics,
    get_global_aggregator,
    reset_global_aggregator,
)
from cohezion.swarm.team_metrics import (
    TeamCompoundMetrics,
    TeamMetricsAggregator,
    WaveMetrics,
)


@pytest.fixture
def global_agg():
    """Create fresh global aggregator for each test."""
    reset_global_aggregator()
    return get_global_aggregator()


class TestGlobalMetricsWithTeamAggregator:
    """Tests for integration with TeamMetricsAggregator."""

    def test_team_metrics_converted_to_global_metrics(self, global_agg):
        """Test converting TeamCompoundMetrics to global metrics."""
        # Create team metrics
        team_metrics = TeamCompoundMetrics(
            plan_name="analysis_team",
            waves=[
                WaveMetrics(
                    wave_index=0,
                    task_count=5,
                    duration_ms=200.0,
                    tokens=2000,
                    model_usage={"deepseek": 5},
                    successes=5,
                    failures=0,
                ),
                WaveMetrics(
                    wave_index=1,
                    task_count=3,
                    duration_ms=150.0,
                    tokens=1500,
                    model_usage={"qwen": 3},
                    successes=3,
                    failures=0,
                ),
            ],
            total_tasks=8,
            total_tokens=3500,
            total_duration_ms=300.0,
            model_usage={"deepseek": 5, "qwen": 3},
            parallel_efficiency=0.85,
            compound_score_delta=0.15,
            success_rate=1.0,
        )

        # Record team metrics as if from an instance
        global_agg.record_team_metrics("team1", "analysis_executor_1", team_metrics)

        # Query the instance metrics
        metrics = global_agg.query_by_agent("analysis_executor_1")
        assert len(metrics) == 1
        assert metrics[0].execution_count == 8
        assert metrics[0].total_tokens == 3500
        assert metrics[0].success_rate == 1.0

    def test_multi_wave_execution_tracking(self, global_agg):
        """Test tracking metrics across multiple execution waves."""
        team_agg = TeamMetricsAggregator("multi_wave_test")

        # Simulate 3 waves of execution
        for wave_idx in range(3):
            task_results = [
                {
                    "task_id": f"task_{i}",
                    "tokens": 500,
                    "model": "deepseek",
                    "status": "completed",
                }
                for i in range(5 + wave_idx)  # Increasing task count
            ]

            team_agg.record_wave(
                wave_index=wave_idx,
                task_results=task_results,
                duration_ms=100.0 + wave_idx * 20,
            )

            # Record to global metrics
            if wave_idx == 2:  # After all waves, finalize
                final = team_agg.finalize(300.0, 0.12)
                global_agg.record_team_metrics("team2", "executor_wave", final)

        # Verify global aggregation
        metrics = global_agg.query_by_agent("executor_wave")
        assert len(metrics) == 1
        assert metrics[0].execution_count == 5 + 6 + 7  # 18 tasks total

    def test_parallel_team_metrics_aggregation(self, global_agg):
        """Test aggregating metrics from parallel team executions."""
        # Simulate 3 parallel teams executing simultaneously
        teams = ["planning_team", "analysis_team", "refinement_team"]
        base_time = time.time()

        for team_idx, team_id in enumerate(teams):
            team_agg = TeamMetricsAggregator(team_id)

            # Each team executes 2 waves
            for wave_idx in range(2):
                task_results = [
                    {"tokens": 400, "model": f"model_{team_idx}", "status": "completed"}
                    for _ in range(4)
                ]
                team_agg.record_wave(wave_idx, task_results, 80.0 + wave_idx * 20)

            final = team_agg.finalize(160.0, 0.10 + team_idx * 0.02)

            # Use custom timestamp to show concurrent execution
            final.timestamp = base_time + team_idx * 10

            # Record each team's metrics
            global_agg.record_team_metrics(team_id, f"{team_id}_executor", final)

        # Query aggregate metrics for the time range
        window = global_agg.query_by_time_range(base_time - 10, base_time + 100)

        # Should have metrics from all 3 teams
        assert window.instance_count >= 3
        assert window.total_executions == 3 * 8  # 3 teams * 8 tasks


class TestGlobalMetricsWithExecutor:
    """Tests for integration with CompoundExecutor."""

    def test_executor_execution_metrics_recording(self, global_agg):
        """Test recording execution-level metrics from executor."""
        executor_id = "compound_executor_1"
        now = time.time()

        # Simulate 10 executions with varying success rates
        for i in range(10):
            success = i < 8  # 80% success rate
            m = InstanceMetrics(
                instance_id=executor_id,
                timestamp=now + i * 100,
                execution_count=1,
                success_count=1 if success else 0,
                total_tokens=500 + i * 50,
                avg_duration_ms=150.0 + (i % 3) * 20,
                coherence_score=0.80 + (i % 10) * 0.02,
                cache_hit_rate=0.70 + (i % 8) * 0.02,
                model_usage={"deepseek": 1},
            )
            global_agg.record_instance_metrics(executor_id, m)

        # Verify aggregated metrics
        metrics = global_agg.query_by_agent(executor_id)
        assert len(metrics) == 10
        assert metrics[0].success_rate == 1.0  # First execution succeeded

        # Query time window
        window = global_agg.query_by_time_range(now, now + 1000)
        assert window.total_executions == 10
        assert window.success_rate == 0.8

    def test_skill_execution_metrics_tracking(self, global_agg):
        """Test tracking metrics for skills executed by executor."""
        # Simulate skill executions from an executor
        skills = ["skill_refine", "skill_analyze", "skill_validate"]

        for skill in skills:
            for _ in range(20):
                global_agg.record_skill_metrics(
                    skill_name=skill,
                    execution_count=1,
                    success_count=1,
                    avg_tokens=400.0,
                    avg_duration_ms=100.0,
                    coherence=0.85,
                    efficiency=0.80,
                )

        # Verify skill metrics
        for skill in skills:
            metrics = global_agg.query_by_skill(skill)
            assert metrics is not None
            assert metrics.execution_count == 20
            assert metrics.success_rate == 1.0


class TestGlobalMetricsPerformance:
    """Performance tests for global metrics in production scenarios."""

    def test_high_frequency_recording_performance(self, global_agg):
        """Test high-frequency metric recording (100+ per second)."""
        executor_id = "high_freq_executor"
        start_time = time.time()

        # Record 1000 metrics at high frequency
        for i in range(1000):
            m = InstanceMetrics(
                instance_id=executor_id,
                timestamp=start_time + i * 0.01,  # 10ms apart
                execution_count=1,
                success_count=1,
                total_tokens=400,
                avg_duration_ms=100.0,
                coherence_score=0.85,
            )
            global_agg.record_instance_metrics(executor_id, m)

        elapsed = time.time() - start_time

        # Should handle 1000 recordings in <100ms
        assert elapsed < 0.1, f"Recording took {elapsed * 1000}ms"

        metrics = global_agg.query_by_agent(executor_id)
        assert len(metrics) == 1000

    def test_memory_efficiency_with_large_teams(self, global_agg):
        """Test memory efficiency with many instances and large time ranges."""
        now = time.time()

        # Simulate 20 instances each recording 100 metrics over 1 hour
        for instance_idx in range(20):
            instance_id = f"executor_{instance_idx}"
            for minute in range(100):  # Rough approximation of 1 hour
                m = InstanceMetrics(
                    instance_id=instance_id,
                    timestamp=now - 3600 + minute * 36,
                    execution_count=50,
                    success_count=48,
                    total_tokens=2000,
                    avg_duration_ms=120.0,
                    coherence_score=0.85,
                )
                global_agg.record_instance_metrics(instance_id, m)

        # Memory should be bounded due to 1000-record limit per instance
        for instance_idx in range(20):
            metrics = global_agg.query_by_agent(f"executor_{instance_idx}")
            assert len(metrics) <= 1000

        # Queries should still be fast
        start = time.time()
        global_agg.query_by_time_range(now - 3600, now)
        latency = (time.time() - start) * 1000

        assert latency < 500

    def test_dashboard_real_time_with_multiple_readers(self, global_agg):
        """Test dashboard snapshot performance with multiple concurrent readers."""
        import threading

        # Pre-populate with data
        now = time.time()
        for i in range(5):
            m = InstanceMetrics(
                instance_id=f"agent_{i}",
                timestamp=now,
                execution_count=100,
                success_count=95,
            )
            global_agg.record_instance_metrics(f"agent_{i}", m)

        # Measure concurrent dashboard queries
        latencies = []
        lock = threading.Lock()

        def query_dashboard():
            """Query dashboard and record latency."""
            start = time.time()
            snapshot = global_agg.get_dashboard_snapshot()
            latency = (time.time() - start) * 1000

            with lock:
                latencies.append(latency)

            # Verify snapshot quality
            assert snapshot["active_instances"] > 0

        # 10 concurrent readers
        threads = [threading.Thread(target=query_dashboard) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        # All should complete quickly
        assert all(lat < 500 for lat in latencies)
        assert len(latencies) == 10


class TestGlobalMetricsVaultIntegration:
    """Tests for vault integration for historical analysis."""

    def test_vault_export_format(self, global_agg, tmp_path):
        """Test vault export contains all necessary fields."""
        now = time.time()
        for i in range(3):
            m = InstanceMetrics(
                instance_id=f"agent_{i}",
                timestamp=now,
                execution_count=100,
                success_count=95,
                coherence_score=0.85,
            )
            global_agg.record_instance_metrics(f"agent_{i}", m)

        # Export to vault
        vault_path = tmp_path / "vault"
        result = global_agg.export_to_vault(vault_path)

        assert result != ""

        # Verify JSON structure
        import json

        data = json.loads((vault_path / result.split("/")[-1]).read_text())
        assert "exported_at" in data
        assert "instance_metrics" in data
        assert all(isinstance(v, list) for v in data["instance_metrics"].values())

    def test_csv_export_for_analytics(self, global_agg, tmp_path):
        """Test CSV export for downstream analytics."""
        now = time.time()
        for i in range(10):
            m = InstanceMetrics(
                instance_id="executor_1",
                timestamp=now + i * 60,
                execution_count=100 + i * 10,
                success_count=95 + i * 9,
                total_tokens=5000 + i * 500,
                coherence_score=0.80 + i * 0.01,
            )
            global_agg.record_instance_metrics("executor_1", m)

        # Export to CSV
        csv_path = tmp_path / "metrics.csv"
        result = global_agg.export_to_csv(csv_path)

        assert result != ""

        # Verify CSV has expected columns and data
        lines = (tmp_path / result.split("/")[-1]).read_text().splitlines()
        assert len(lines) == 11  # Header + 10 records

        # Parse CSV
        import csv

        reader = list(csv.DictReader(lines))
        assert len(reader) == 10
        assert float(reader[0]["execution_count"]) == 100
        assert float(reader[-1]["execution_count"]) == 190


class TestDashboardMetricsConsistency:
    """Tests for consistency of dashboard metrics across queries."""

    def test_consistent_success_rate_calculations(self, global_agg):
        """Test that success rate is consistent across different query methods."""
        now = time.time()
        base_time = now - 100  # Within 5-minute window for dashboard

        # Record identical metrics for 3 agents
        for agent_idx in range(3):
            m = InstanceMetrics(
                instance_id=f"agent_{agent_idx}",
                timestamp=base_time + 50,  # Well within time range
                execution_count=100,
                success_count=85,
            )
            global_agg.record_instance_metrics(f"agent_{agent_idx}", m)

        # Query by different methods
        agent_metrics = global_agg.query_by_agent("agent_0")
        agent_success = agent_metrics[0].success_rate

        window_metrics = global_agg.query_by_time_range(base_time - 10, now)
        window_success = window_metrics.success_rate

        dashboard_snapshot = global_agg.get_dashboard_snapshot()
        dashboard_success = dashboard_snapshot["success_rate"]

        # All should report same success rate
        assert agent_success == 0.85
        assert window_success == 0.85
        assert dashboard_success == 0.85

    def test_coherence_aggregation_consistency(self, global_agg):
        """Test coherence scores aggregate consistently."""
        now = time.time()
        base_time = now - 300

        # Record metrics with varying coherence
        coherences = [0.70, 0.80, 0.75, 0.85, 0.88]

        for i, coherence in enumerate(coherences):
            m = InstanceMetrics(
                instance_id=f"agent_{i % 2}",
                timestamp=base_time + i * 60,
                execution_count=100,
                success_count=95,
                coherence_score=coherence,
            )
            global_agg.record_instance_metrics(f"agent_{i % 2}", m)

        # Query window
        window = global_agg.query_by_time_range(base_time, now)

        # Average coherence should be reasonable
        expected_avg = sum(coherences) / len(coherences)
        assert abs(window.avg_coherence - expected_avg) < 0.01
