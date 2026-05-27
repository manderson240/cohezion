"""Integration test for the full training pipeline at demo scale.

Tests the complete flow: sim → export → VAE train → RL train → weight bridge.
Uses small parameters to run in seconds, not minutes.
"""

from __future__ import annotations

import numpy as np
import pytest
import torch

from cohezion.flume.dataset import FlumeTrajectoryDataset
from cohezion.flume.training import FlumeVAETrainer, TrainConfig
from cohezion.pipeline.trained_navigator import TrainedNavigator
from cohezion.pipeline.weight_bridge import WeightBridge
from cohezion.rl.trainer import PolicyNetwork, TrainingConfig, train


def _flume_nav_registered() -> bool:
    try:
        import gymnasium as gym

        return "cohezion/FlumeNav-v0" in gym.envs.registry
    except Exception:
        return False


_skip_no_flume_nav = pytest.mark.skipif(
    not _flume_nav_registered(),
    reason="cohezion/FlumeNav-v0 gymnasium environment not registered",
)


@pytest.fixture
def pipeline_dir(tmp_path):
    """Create directory structure for the pipeline test."""
    dirs = {
        "sim_artifacts": tmp_path / "sim_artifacts",
        "vae_checkpoints": tmp_path / "vae_checkpoints",
        "rl_checkpoints": tmp_path / "rl_checkpoints",
    }
    for d in dirs.values():
        d.mkdir()
    return dirs


@pytest.fixture
def sim_data(pipeline_dir):
    """Generate synthetic simulation data as .npy files."""
    rng = np.random.default_rng(42)
    artifact_dir = pipeline_dir["sim_artifacts"]

    # Create 3 universes with 50 agents each
    for uid in range(3):
        states = rng.normal(0.5, 0.15, (50, 256)).astype(np.float32)
        np.save(artifact_dir / f"universe_{uid}_final.npy", states)

    return artifact_dir


class TestFullPipelineDemoScale:
    """End-to-end test at minimal scale: 3 universes, 5 VAE epochs, 10 RL episodes."""

    def test_step1_export_creates_loadable_data(self, sim_data):
        """Step 1: Verify exported .npy files are loadable."""
        dataset = FlumeTrajectoryDataset(data_dir=sim_data, max_samples=200)
        assert len(dataset) == 150  # 3 x 50
        assert dataset[0].shape == (256,)

    def test_step2_vae_trains_and_improves(self, sim_data, pipeline_dir):
        """Step 2: VAE training reduces loss over 5 epochs."""
        config = TrainConfig(
            z_dim=256,
            batch_size=32,
            epochs=5,
            lr=1e-3,
            checkpoint_dir=str(pipeline_dir["vae_checkpoints"]),
            data_dir=str(sim_data),
            log_interval=1,
        )
        trainer = FlumeVAETrainer(config)
        metrics = trainer.train()

        assert len(metrics) == 5
        assert metrics[-1]["mse"] < metrics[0]["mse"]  # Loss should decrease

    @_skip_no_flume_nav
    def test_step3_rl_trains_and_produces_checkpoint(self, pipeline_dir):
        """Step 3: RL training produces a checkpoint file."""
        config = TrainingConfig(
            n_episodes=10,
            max_steps=20,
            lr=3e-4,
            z_dim=256,
            hidden_dim=128,
            save_interval=5,
            output_dir=str(pipeline_dir["rl_checkpoints"]),
            log_interval=5,
        )
        results = train(config)

        assert len(results) == 10
        assert all(r.steps > 0 for r in results)

        # Final checkpoint should exist
        final_path = pipeline_dir["rl_checkpoints"] / "policy_final.pt"
        assert final_path.exists()

    def test_step4_weight_bridge_extracts_shapes(self, pipeline_dir):
        """Step 4: Weight bridge produces correct tensor shapes."""
        # Create a checkpoint first
        policy = PolicyNetwork(256, 256, 128)
        ckpt_path = pipeline_dir["rl_checkpoints"] / "test_policy.pt"
        torch.save(policy.state_dict(), ckpt_path)

        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        assert weights["w1"].shape == (128, 256)
        assert weights["b1"].shape == (128,)
        assert weights["w2"].shape == (256, 128)
        assert weights["b2"].shape == (256,)
        assert weights["gamma"].shape == (128,)
        assert weights["beta"].shape == (128,)
        assert all(v.dtype == np.float32 for v in weights.values())

    def test_step5_trained_navigator_produces_deltas(self, pipeline_dir):
        """Step 5: Trained navigator returns valid delta vectors."""
        # Create a checkpoint
        policy = PolicyNetwork(256, 256, 128)
        ckpt_path = pipeline_dir["rl_checkpoints"] / "nav_policy.pt"
        torch.save(policy.state_dict(), ckpt_path)

        nav = TrainedNavigator(ckpt_path, action_scale=0.01)

        states = np.random.default_rng(0).normal(0.5, 0.1, (10, 256)).astype(np.float32)
        deltas = nav.navigate_batch(states)

        assert deltas.shape == (10, 256)
        assert deltas.dtype == np.float32
        # Deltas should be small (action_scale=0.01 + tanh bounds)
        assert np.abs(deltas).max() < 0.02

    @_skip_no_flume_nav
    def test_full_roundtrip(self, sim_data, pipeline_dir):
        """Full pipeline: sim data → VAE → RL → weight bridge → navigator."""
        # 1. Load sim data
        dataset = FlumeTrajectoryDataset(data_dir=sim_data)
        assert len(dataset) > 0

        # 2. Train VAE
        vae_config = TrainConfig(
            epochs=3,
            batch_size=32,
            checkpoint_dir=str(pipeline_dir["vae_checkpoints"]),
            data_dir=str(sim_data),
            log_interval=1,
        )
        trainer = FlumeVAETrainer(vae_config)
        vae_metrics = trainer.train()
        assert len(vae_metrics) > 0

        # 3. Train RL
        rl_config = TrainingConfig(
            n_episodes=5,
            max_steps=10,
            output_dir=str(pipeline_dir["rl_checkpoints"]),
            save_interval=5,
            log_interval=5,
        )
        rl_results = train(rl_config)
        assert len(rl_results) == 5

        # 4. Extract weights
        rl_ckpt = pipeline_dir["rl_checkpoints"] / "policy_final.pt"
        weights = WeightBridge.policy_to_flume_weights(rl_ckpt)
        assert "w1" in weights

        # 5. Create navigator
        nav = TrainedNavigator(rl_ckpt)
        states = np.random.default_rng(0).normal(0.5, 0.1, (5, 256)).astype(np.float32)
        deltas = nav.navigate_batch(states)
        assert deltas.shape == states.shape

        # Pipeline complete!
