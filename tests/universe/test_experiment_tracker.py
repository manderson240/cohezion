"""Tests for the Experiment Tracker."""

from pathlib import Path

import numpy as np
import pytest

from cohezion.universe.experiment_tracker import (
    ExperimentRun,
    ExperimentTracker,
    MetricEntry,
    RunComparison,
    RunConfig,
    RunStatus,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def reset_tracker():
    """Reset singleton between tests."""
    ExperimentTracker.reset()
    yield
    ExperimentTracker.reset()


@pytest.fixture
def tracker(tmp_path):
    return ExperimentTracker(base_dir=str(tmp_path / "experiments"))


@pytest.fixture
def config():
    return RunConfig(
        seed=42,
        environment={"grid_size": 64, "max_steps": 500},
        agent={"lr": 3e-4, "gamma": 0.99},
        training={"num_episodes": 100},
    )


# ---------------------------------------------------------------------------
# RunConfig tests
# ---------------------------------------------------------------------------


class TestRunConfig:
    def test_config_hash_deterministic(self, config):
        h1 = config.config_hash
        h2 = config.config_hash
        assert h1 == h2

    def test_config_hash_varies(self):
        c1 = RunConfig(seed=42, environment={}, agent={}, training={})
        c2 = RunConfig(seed=99, environment={}, agent={}, training={})
        assert c1.config_hash != c2.config_hash


# ---------------------------------------------------------------------------
# ExperimentRun tests
# ---------------------------------------------------------------------------


class TestExperimentRun:
    def test_get_final_metrics(self):
        run = ExperimentRun(
            run_id="r1",
            name="test",
            config=RunConfig(42, {}, {}, {}),
        )
        run.metrics["reward"] = [
            MetricEntry(step=0, name="reward", value=1.0),
            MetricEntry(step=1, name="reward", value=2.0),
            MetricEntry(step=2, name="reward", value=3.0),
        ]
        finals = run.get_final_metrics()
        assert finals["reward"] == 3.0

    def test_get_metric_series(self):
        run = ExperimentRun(
            run_id="r1",
            name="test",
            config=RunConfig(42, {}, {}, {}),
        )
        run.metrics["loss"] = [
            MetricEntry(step=0, name="loss", value=1.0),
            MetricEntry(step=10, name="loss", value=0.5),
        ]
        series = run.get_metric_series("loss")
        assert series == [(0, 1.0), (10, 0.5)]

    def test_summary(self):
        run = ExperimentRun(
            run_id="r1",
            name="test",
            config=RunConfig(42, {}, {}, {}),
            tags={"type": "baseline"},
        )
        s = run.summary()
        assert s["run_id"] == "r1"
        assert s["seed"] == 42
        assert s["tags"] == {"type": "baseline"}


# ---------------------------------------------------------------------------
# ExperimentTracker tests
# ---------------------------------------------------------------------------


class TestExperimentTracker:
    def test_create_run(self, tracker, config):
        run = tracker.create_run(name="test_run", config=config)
        assert run.run_id.startswith("run_")
        assert run.status == RunStatus.CREATED
        assert run.config.seed == 42

    def test_start_and_end_run(self, tracker, config):
        run = tracker.create_run(name="test", config=config)
        tracker.start_run(run.run_id)
        assert run.status == RunStatus.RUNNING

        tracker.end_run(run.run_id, RunStatus.COMPLETED)
        assert run.status == RunStatus.COMPLETED
        assert run.completed_at is not None
        assert run.duration_seconds is not None

    def test_log_metric(self, tracker, config):
        run = tracker.create_run(name="test", config=config)
        tracker.log_metric("reward", 1.5, step=0)
        tracker.log_metric("reward", 2.5, step=1)

        assert len(run.metrics["reward"]) == 2
        assert run.metrics["reward"][0].value == 1.5
        assert run.metrics["reward"][1].value == 2.5

    def test_log_metrics_batch(self, tracker, config):
        run = tracker.create_run(name="test", config=config)
        tracker.log_metrics(
            {"reward": 1.0, "loss": 0.5, "coherence": 0.48},
            step=0,
        )

        assert "reward" in run.metrics
        assert "loss" in run.metrics
        assert "coherence" in run.metrics

    def test_save_and_load_checkpoint(self, tracker, config):
        run = tracker.create_run(name="test", config=config)

        state = {
            "weights": np.random.randn(10, 5),
            "bias": np.zeros(5),
        }
        ref = tracker.save_checkpoint(state, step=10)

        assert ref.step == 10
        assert ref.checkpoint_id == "ckpt_000010"

        loaded = tracker.load_checkpoint(run.run_id, step=10)
        np.testing.assert_array_almost_equal(loaded["weights"], state["weights"])
        np.testing.assert_array_almost_equal(loaded["bias"], state["bias"])

    def test_load_latest_checkpoint(self, tracker, config):
        run = tracker.create_run(name="test", config=config)

        tracker.save_checkpoint({"w": np.array([1.0])}, step=10)
        tracker.save_checkpoint({"w": np.array([2.0])}, step=20)

        loaded = tracker.load_checkpoint(run.run_id)  # No step = latest
        assert loaded["w"][0] == pytest.approx(2.0)

    def test_list_runs(self, tracker):
        c1 = RunConfig(42, {}, {}, {})
        c2 = RunConfig(99, {}, {}, {})
        tracker.create_run(name="baseline", config=c1, tags={"type": "baseline"})
        tracker.create_run(name="experiment", config=c2, tags={"type": "experiment"})

        all_runs = tracker.list_runs()
        assert len(all_runs) == 2

        filtered = tracker.list_runs(tag_filter={"type": "baseline"})
        assert len(filtered) == 1
        assert filtered[0]["name"] == "baseline"

    def test_list_runs_by_status(self, tracker, config):
        r1 = tracker.create_run(name="r1", config=config)
        tracker.create_run(name="r2", config=config)
        tracker.start_run(r1.run_id)
        tracker.end_run(r1.run_id, RunStatus.COMPLETED)

        completed = tracker.list_runs(status=RunStatus.COMPLETED)
        assert len(completed) == 1

    def test_get_run(self, tracker, config):
        run = tracker.create_run(name="test", config=config)
        retrieved = tracker.get_run(run.run_id)
        assert retrieved is not None
        assert retrieved.name == "test"

        assert tracker.get_run("nonexistent") is None

    def test_compare_runs(self, tracker):
        c1 = RunConfig(42, {}, {}, {})
        c2 = RunConfig(99, {}, {}, {})
        r1 = tracker.create_run(name="v1", config=c1)
        r2 = tracker.create_run(name="v2", config=c2)

        # Log metrics for both runs
        for i in range(20):
            tracker.log_metric(
                "coherence", 0.48 + np.random.normal(0, 0.02), step=i, run_id=r1.run_id
            )
            tracker.log_metric(
                "coherence", 0.52 + np.random.normal(0, 0.02), step=i, run_id=r2.run_id
            )
            tracker.log_metric("reward", float(i) * 0.1, step=i, run_id=r1.run_id)
            tracker.log_metric("reward", float(i) * 0.12, step=i, run_id=r2.run_id)

        comparison = tracker.compare_runs(r1.run_id, r2.run_id)
        assert isinstance(comparison, RunComparison)
        assert "coherence" in comparison.common_metrics
        assert "reward" in comparison.common_metrics
        assert len(comparison.metric_comparisons) == 2

    def test_data_persists_to_disk(self, tracker, config):
        run = tracker.create_run(name="persist_test", config=config)
        tracker.log_metric("test_metric", 42.0, step=0)
        tracker.end_run(run.run_id)

        # Check files exist
        run_dir = Path(tracker.base_dir) / run.run_id
        assert (run_dir / "config.json").exists()
        assert (run_dir / "metrics.jsonl").exists()
        assert (run_dir / "summary.json").exists()

    def test_no_active_run_raises(self, tracker):
        with pytest.raises(ValueError, match="No active run"):
            tracker.log_metric("x", 1.0, step=0)

    def test_nonexistent_run_raises(self, tracker):
        with pytest.raises(ValueError, match="Run not found"):
            tracker.log_metric("x", 1.0, step=0, run_id="fake_id")

    def test_no_checkpoints_raises(self, tracker, config):
        run = tracker.create_run(name="test", config=config)
        with pytest.raises(ValueError, match="No checkpoints"):
            tracker.load_checkpoint(run.run_id)

    def test_singleton_pattern(self, tmp_path):
        ExperimentTracker.reset()
        t1 = ExperimentTracker.get_instance(str(tmp_path / "exp"))
        t2 = ExperimentTracker.get_instance(str(tmp_path / "exp"))
        assert t1 is t2

    def test_index_persistence(self, tmp_path, config):
        # Create tracker and run
        t1 = ExperimentTracker(base_dir=str(tmp_path / "exp"))
        run = t1.create_run(name="indexed", config=config)
        run_id = run.run_id

        # Create new tracker instance (simulates restart)
        t2 = ExperimentTracker(base_dir=str(tmp_path / "exp"))

        # Should find the run from index
        retrieved = t2.get_run(run_id)
        assert retrieved is not None
        assert retrieved.name == "indexed"
