"""Tests for End-to-End Universe Training Pipeline."""

import numpy as np

from cohezion.universe.training_pipeline import (
    MyceliumSignal,
    TrainingConfig,
    TrainingReport,
    UniverseTrainingPipeline,
    emit_mycelium_signal,
)


class TestTrainingConfig:
    """Test training configuration."""

    def test_default_config(self):
        """Should create config with sensible defaults."""
        config = TrainingConfig()
        assert config.scenario_count > 0
        assert config.agent_count > 0
        assert config.max_concurrent_scenarios > 0

    def test_custom_config(self):
        """Should accept custom configuration."""
        config = TrainingConfig(
            scenario_count=20,
            agent_count=5,
            max_concurrent_scenarios=8,
            difficulty_min=0.2,
            difficulty_max=0.9,
        )
        assert config.scenario_count == 20
        assert config.agent_count == 5


class TestMyceliumSignal:
    """Test Mycelium signal interface."""

    def test_signal_creation(self):
        """Should create signal with required fields."""
        signal = MyceliumSignal(
            event_type="pipeline_complete",
            scenario_count=10,
            agent_count=3,
            capability_deltas={"task_completion": 0.05},
        )
        assert signal.event_type == "pipeline_complete"
        assert signal.scenario_count == 10

    def test_emit_signal(self):
        """Should emit signal without error."""
        signal = MyceliumSignal(
            event_type="pipeline_complete",
            scenario_count=5,
            agent_count=2,
            capability_deltas={},
        )
        # Should not raise
        emit_mycelium_signal(signal)


class TestUniverseTrainingPipeline:
    """Test end-to-end training pipeline."""

    def test_pipeline_creation(self):
        """Should create pipeline with default config."""
        pipeline = UniverseTrainingPipeline()
        assert pipeline is not None

    def test_pipeline_with_config(self):
        """Should create pipeline with custom config."""
        config = TrainingConfig(scenario_count=5, agent_count=2)
        pipeline = UniverseTrainingPipeline(config=config)
        assert pipeline.config.scenario_count == 5

    def test_pipeline_run(self):
        """Should execute complete training loop."""
        config = TrainingConfig(
            scenario_count=4,
            agent_count=2,
            max_steps=10,
            seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        assert isinstance(report, TrainingReport)
        assert report.scenarios_completed > 0
        assert report.agents_evaluated > 0
        assert len(report.agent_profiles) > 0

    def test_pipeline_generates_scenarios(self):
        """Should generate scenarios of all types."""
        config = TrainingConfig(scenario_count=8, agent_count=1, seed=42)
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        # Should have completed scenarios
        assert report.scenarios_completed > 0

    def test_pipeline_produces_capability_profiles(self):
        """Should produce per-agent capability profiles."""
        config = TrainingConfig(
            scenario_count=4, agent_count=3, max_steps=10, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        # Should have profiles for each agent
        assert len(report.agent_profiles) == 3
        for profile in report.agent_profiles.values():
            assert 0.0 <= profile.task_completion <= 1.0
            assert profile.num_scenarios > 0

    def test_pipeline_records_to_ouroboros(self):
        """Should record events via Ouroboros recorder."""
        config = TrainingConfig(
            scenario_count=2, agent_count=1, max_steps=5, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        # Recorder should have events
        assert report.recording_id is not None

    def test_pipeline_encodes_journeys(self):
        """Should encode journeys via FLUME VAE."""
        config = TrainingConfig(
            scenario_count=2, agent_count=1, max_steps=10, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        # Should have journey embeddings
        assert len(report.journey_embeddings) > 0
        for embedding in report.journey_embeddings:
            assert isinstance(embedding, np.ndarray)
            assert embedding.shape == (256,)

    def test_pipeline_emits_mycelium_signal(self):
        """Should emit mycelium signal after completion."""
        config = TrainingConfig(
            scenario_count=2, agent_count=1, max_steps=5, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        assert report.mycelium_signal is not None
        assert report.mycelium_signal.scenario_count > 0

    def test_pipeline_handles_individual_failures(self):
        """Individual scenario failures should not crash batch."""
        config = TrainingConfig(
            scenario_count=4, agent_count=1, max_steps=5, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        # Should complete without crashing even if some scenarios fail
        report = pipeline.run()
        assert report is not None

    def test_pipeline_experience_replay(self):
        """Should support experience replay via VAE embeddings."""
        config = TrainingConfig(
            scenario_count=4, agent_count=1, max_steps=10, seed=42,
        )
        pipeline = UniverseTrainingPipeline(config=config)
        report = pipeline.run()

        if len(report.journey_embeddings) >= 2:
            # Find similar journeys using cosine similarity
            similar = pipeline.find_similar_journeys(
                report.journey_embeddings[0], report.journey_embeddings
            )
            assert len(similar) > 0
