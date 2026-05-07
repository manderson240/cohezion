"""Integration tests for the end-to-end training pipeline.

Tests the full loop: mass sim -> .npy export -> VAE training ->
weight bridge -> FlumePhysics with trained weights -> coherence validation.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import numpy as np
import pytest
import torch


if TYPE_CHECKING:
    from pathlib import Path


def _rust_available() -> bool:
    """Check if Rust FlumePhysics extension is available."""
    try:
        from cohezion_core.cohezion_core_rs import FlumePhysics  # noqa: F401

        return True
    except ImportError:
        return False


requires_rust = pytest.mark.skipif(
    not _rust_available(),
    reason="Rust FlumePhysics extension not compiled",
)


@pytest.fixture
def tmp_artifact_dir(tmp_path: Path) -> Path:
    """Create a temporary artifact directory."""
    d = tmp_path / "artifacts"
    d.mkdir()
    return d


@pytest.fixture
def tmp_npy_files(tmp_artifact_dir: Path) -> list[Path]:
    """Create synthetic .npy files mimicking mass sim output."""
    rng = np.random.default_rng(42)
    files = []
    for i in range(3):
        data = rng.normal(0.5, 0.25, (50, 256)).astype(np.float32)
        path = tmp_artifact_dir / f"universe_{i}_final.npy"
        np.save(path, data)
        files.append(path)
    return files


@pytest.fixture
def trained_policy_path(tmp_path: Path) -> Path:
    """Create a PolicyNetwork checkpoint for testing."""
    from cohezion.rl.trainer import PolicyNetwork

    policy = PolicyNetwork(state_dim=256, action_dim=256, hidden=128)
    path = tmp_path / "policy_test.pt"
    torch.save(policy.state_dict(), path)
    return path


class TestMassSimExportsNpy:
    """Test that mass sim exports .npy files when configured."""

    @requires_rust
    def test_mass_sim_exports_npy(self, tmp_artifact_dir: Path):
        from cohezion.mass_sim.batch_runner import BatchSimulationRunner
        from cohezion.mass_sim.config import ScaleTier, SimulationConfig, UniverseSpec

        tier = ScaleTier(
            name="test",
            n_agents=10,
            n_epochs=50,
            n_universes=1,
            checkpoint_interval=50,
            batch_size=10,
        )
        config = SimulationConfig(
            scale=tier,
            export_npy=True,
            artifact_dir=tmp_artifact_dir,
            persist_to_db=False,
        )

        runner = BatchSimulationRunner(config)
        rng = np.random.default_rng(42)
        agents = rng.normal(0.5, 0.25, (10, 256)).astype(np.float32)
        spec = UniverseSpec("test_u0", seed=0)
        runner.simulate_universe(spec, agents)

        npy_files = list(tmp_artifact_dir.glob("*.npy"))
        assert len(npy_files) >= 1
        data = np.load(npy_files[0])
        assert data.shape == (10, 256)
        assert data.dtype == np.float32


class TestVaeTrainsOnRealData:
    """Test VAE training on real .npy data."""

    def test_vae_trains_on_real_data(self, tmp_npy_files: list[Path], tmp_path: Path):
        from cohezion.flume.training import FlumeVAETrainer, TrainConfig

        data_dir = tmp_npy_files[0].parent
        checkpoint_dir = tmp_path / "vae_ckpt"

        config = TrainConfig(
            epochs=2,
            batch_size=16,
            data_dir=str(data_dir),
            checkpoint_dir=str(checkpoint_dir),
            log_interval=1,
        )

        trainer = FlumeVAETrainer(config)
        metrics = trainer.train()

        assert len(metrics) == 2
        assert metrics[0]["total"] > 0
        assert np.isfinite(metrics[-1]["total"])
        # Loss should not explode
        assert metrics[-1]["total"] < metrics[0]["total"] * 2.0


class TestRustLoadTrainedWeights:
    """Test that WeightBridge can create FlumePhysics from policy weights."""

    @requires_rust
    def test_rust_loads_trained_weights(self, trained_policy_path: Path):
        from cohezion.pipeline.weight_bridge import WeightBridge

        physics = WeightBridge.policy_to_flume_physics(trained_policy_path)

        rng = np.random.default_rng(42)
        agents = rng.normal(0.5, 0.25, (20, 256)).astype(np.float32)
        evolved = physics.simulate_epochs_navigated(agents, 50)
        stats = physics.compute_batch_stats(evolved)

        assert "mean_coherence" in stats
        mean_coh = float(stats["mean_coherence"])
        assert 0.0 <= mean_coh <= 1.0


class TestCompositeRewardInEnv:
    """Test that FlumeNavEnv uses CompositeReward correctly."""

    def test_composite_reward_in_env(self):
        from cohezion.rl.environment import FlumeNavEnv

        env = FlumeNavEnv(use_composite_reward=True)
        obs, info = env.reset(seed=42)
        assert "coherence" in info

        rewards = []
        for _ in range(10):
            action = env.action_space.sample()
            _obs, reward, terminated, truncated, info = env.step(action)
            rewards.append(reward)
            if terminated or truncated:
                break

        # Rewards should vary (not all identical)
        assert len({f"{r:.6f}" for r in rewards}) > 1
        env.close()

    def test_legacy_reward_still_works(self):
        from cohezion.rl.environment import FlumeNavEnv

        env = FlumeNavEnv(use_composite_reward=False)
        obs, info = env.reset(seed=42)

        action = env.action_space.sample()
        _obs, reward, _terminated, _truncated, _info = env.step(action)
        assert isinstance(reward, float)
        env.close()


class TestUniverseFactoryWithWeights:
    """Test that UniverseFactory accepts pre-trained weights."""

    @requires_rust
    def test_factory_with_pretrained_weights(self, trained_policy_path: Path):
        from cohezion.mass_sim.config import UniverseSpec
        from cohezion.mass_sim.universe_factory import UniverseFactory
        from cohezion.pipeline.weight_bridge import WeightBridge

        weights = WeightBridge.policy_to_flume_weights(trained_policy_path)
        spec = UniverseSpec("test_pretrained", seed=99)
        physics = UniverseFactory.create(spec, weights=weights)

        rng = np.random.default_rng(42)
        agents = rng.normal(0.5, 0.25, (10, 256)).astype(np.float32)
        evolved = physics.simulate_epochs_navigated(agents, 50)
        stats = physics.compute_batch_stats(evolved)

        assert "mean_coherence" in stats


class TestPipelineEndToEnd:
    """Full end-to-end pipeline test (small scale)."""

    @requires_rust
    def test_pipeline_end_to_end(self, tmp_path: Path):
        from scripts.pipeline import PipelineConfig, run_pipeline

        config = PipelineConfig(
            n_agents=10,
            n_epochs=50,
            n_universes=2,
            vae_epochs=2,
            vae_batch_size=8,
            rl_episodes=5,
            rl_max_steps=20,
            output_dir=tmp_path / "pipeline",
        )

        result = run_pipeline(config)

        assert len(result.npy_files) >= 2
        assert result.vae_final_loss > 0
        assert np.isfinite(result.vae_final_loss)
        assert 0.0 <= result.rl_final_coherence <= 1.0
        assert 0.0 <= result.mean_coherence <= 1.0
        assert result.elapsed_seconds > 0
