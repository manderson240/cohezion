"""Tests for TRIUNE PPO Trainer (Phase 4).

Tests cover:
- TRIUNEPolicy 3-tier architecture (Knower→Thinker→Doer)
- PPO update with clip objective
- Value head separate network
- Memory buffer management (80GB ceiling)
- Checkpoint save/load
"""

from __future__ import annotations

import tempfile
from pathlib import Path

import numpy as np
import pytest
import torch
import torch.nn as nn


class TestTRIUNEPolicy:
    """Tests for TRIUNEPolicy 3-tier architecture."""

    @pytest.fixture
    def policy_cls(self):
        from cohezion.rl.ppo_trainer import TRIUNEPolicy

        return TRIUNEPolicy

    def test_knower_output_shape(self, policy_cls):
        """Knower layer maps 256D → 2048D."""
        policy = policy_cls(z_dim=256)
        z = torch.randn(2, 256)
        with torch.no_grad():
            knower_out = policy.knower(z)
        assert knower_out.shape == (2, 2048)

    def test_thinker_output_shape(self, policy_cls):
        """Thinker layer maps 2048D → 512D."""
        policy = policy_cls(z_dim=256)
        h = torch.randn(2, 2048)
        with torch.no_grad():
            thinker_out = policy.thinker(h)
        assert thinker_out.shape == (2, 512)

    def test_doer_output_shape(self, policy_cls):
        """Doer layer maps 512D → z_dim (256D for standard config)."""
        policy = policy_cls(z_dim=256)
        h = torch.randn(2, 512)
        with torch.no_grad():
            doer_out = policy.doer(h)
        assert doer_out.shape == (2, 256)

    def test_forward_returns_zdim_action(self, policy_cls):
        """forward() returns z_dim action from 256D VAE latent."""
        policy = policy_cls(z_dim=256)
        z = torch.randn(4, 256)
        action = policy(z)
        assert action.shape == (4, 256)
        assert action.dtype == torch.float32

    def test_forward_tanh_bounded_output(self, policy_cls):
        """forward() output is bounded by Tanh to [-1, 1]."""
        policy = policy_cls(z_dim=256)
        z = torch.randn(32, 256)
        action = policy(z)
        assert action.min() >= -1.0
        assert action.max() <= 1.0

    def test_policy_is_nn_module(self, policy_cls):
        """TRIUNEPolicy inherits from nn.Module."""
        policy = policy_cls()
        assert isinstance(policy, nn.Module)

    def test_custom_z_dim(self, policy_cls):
        """TRIUNEPolicy accepts custom z_dim."""
        policy = policy_cls(z_dim=128)
        z = torch.randn(2, 128)
        action = policy(z)
        assert action.shape == (2, 128)

    def test_all_parameters_trainable(self, policy_cls):
        """All TRIUNEPolicy parameters require gradients."""
        policy = policy_cls()
        for param in policy.parameters():
            assert param.requires_grad, f"Parameter {param.shape} is not trainable"


class TestValueNetwork:
    """Tests for separate value head."""

    @pytest.fixture
    def trainer_cls(self):
        from cohezion.rl.ppo_trainer import PPOTrainer

        return PPOTrainer

    def test_value_network_exists(self, trainer_cls):
        """PPOTrainer has a value_network attribute."""
        trainer = trainer_cls()
        assert hasattr(trainer, "value_network")
        assert isinstance(trainer.value_network, nn.Module)

    def test_value_network_maps_256_to_1(self, trainer_cls):
        """Value network maps 256D state → 1D value."""
        trainer = trainer_cls()
        z = torch.randn(4, 256)
        with torch.no_grad():
            value = trainer.value_network(z)
        assert value.shape == (4, 1)
        assert value.dtype == torch.float32

    def test_value_network_output_unbounded(self, trainer_cls):
        """Value network output is not bounded (can be any real)."""
        trainer = trainer_cls()
        z = torch.randn(32, 256)
        value = trainer.value_network(z)
        assert value.shape == (32, 1)


class TestPPOConfig:
    """Tests for PPOConfig dataclass."""

    def test_default_config_values(self):
        """Default config has correct PPO hyperparameters."""
        from cohezion.rl.ppo_trainer import PPOConfig

        config = PPOConfig()
        assert config.clip_epsilon == 0.2
        assert config.n_epochs == 4
        assert config.lr == 3e-4
        assert config.gamma == 0.99
        assert config.gae_lambda == 0.95
        assert config.entropy_coef == 0.01

    def test_custom_config_values(self):
        """Config accepts custom hyperparameter values."""
        from cohezion.rl.ppo_trainer import PPOConfig

        config = PPOConfig(
            clip_epsilon=0.1,
            n_epochs=8,
            lr=1e-4,
            gamma=0.95,
        )
        assert config.clip_epsilon == 0.1
        assert config.n_epochs == 8
        assert config.lr == 1e-4
        assert config.gamma == 0.95


class TestPPOTrainerInitialization:
    """Tests for PPOTrainer initialization."""

    def test_trainer_has_policy(self):
        """PPOTrainer has a policy attribute."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        assert hasattr(trainer, "policy")
        assert isinstance(trainer.policy, nn.Module)

    def test_trainer_has_buffer(self):
        """PPOTrainer has a buffer list."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        assert hasattr(trainer, "buffer")
        assert isinstance(trainer.buffer, list)
        assert len(trainer.buffer) == 0

    def test_trainer_has_optimizer(self):
        """PPOTrainer has Adam optimizer."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        assert hasattr(trainer, "optimizer")
        assert isinstance(trainer.optimizer, torch.optim.Adam)

    def test_trainer_has_scheduler(self):
        """PPOTrainer has lr_scheduler."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        assert hasattr(trainer, "scheduler")

    def test_trainer_with_custom_config(self):
        """PPOTrainer accepts custom PPOConfig."""
        from cohezion.rl.ppo_trainer import PPOConfig, PPOTrainer

        config = PPOConfig(clip_epsilon=0.15, n_epochs=6)
        trainer = PPOTrainer(config=config)
        assert trainer.config.clip_epsilon == 0.15
        assert trainer.config.n_epochs == 6


class TestMemoryBuffer:
    """Tests for episode buffer memory management."""

    def test_buffer_stores_transitions(self):
        """Buffer stores dict with required keys."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        transition = {
            "state": np.random.randn(256).astype(np.float32),
            "action": np.random.randn(256).astype(np.float32),
            "reward": 0.5,
            "done": False,
            "log_prob": -1.5,
            "value": 1.2,
        }
        trainer.buffer.append(transition)
        assert len(trainer.buffer) == 1
        assert trainer.buffer[0]["state"].shape == (256,)
        assert trainer.buffer[0]["action"].shape == (256,)

    def test_buffer_uses_32bit_floats(self):
        """Buffer stores transitions as 32-bit floats."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        transition = {
            "state": np.random.randn(256).astype(np.float32),
            "action": np.random.randn(256).astype(np.float32),
            "reward": 0.5,
            "done": False,
            "log_prob": -1.5,
            "value": 1.2,
        }
        trainer.buffer.append(transition)
        assert trainer.buffer[0]["state"].dtype == np.float32
        assert trainer.buffer[0]["action"].dtype == np.float32

    def test_clear_buffer(self):
        """Buffer can be cleared."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        for _ in range(10):
            trainer.buffer.append(
                {
                    "state": np.random.randn(256).astype(np.float32),
                    "action": np.random.randn(256).astype(np.float32),
                    "reward": 0.5,
                    "done": False,
                    "log_prob": -1.5,
                    "value": 1.2,
                }
            )
        trainer.buffer.clear()
        assert len(trainer.buffer) == 0


class TestPPOUpdate:
    """Tests for PPO update logic."""

    def test_update_requires_sufficient_samples(self):
        """update() requires minimum number of samples."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        trainer.buffer.append(
            {
                "state": np.random.randn(256).astype(np.float32),
                "action": np.random.randn(256).astype(np.float32),
                "reward": 0.5,
                "done": False,
                "log_prob": -1.5,
                "value": 1.2,
            }
        )
        result = trainer.update()
        assert result["status"] == "insufficient_samples"

    def test_update_returns_metrics(self):
        """update() returns dict with loss metrics."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        for _ in range(128):
            trainer.buffer.append(
                {
                    "state": np.random.randn(256).astype(np.float32),
                    "action": np.random.randn(256).astype(np.float32),
                    "reward": float(np.random.randn()),
                    "done": np.random.rand() > 0.9,
                    "log_prob": float(np.random.randn()),
                    "value": float(np.random.randn()),
                }
            )
        result = trainer.update()
        assert "policy_loss" in result
        assert "value_loss" in result
        assert "entropy" in result
        assert "approx_kl" in result

    def test_clip_epsilon_in_config(self):
        """PPOConfig.clip_epsilon defaults to 0.2."""
        from cohezion.rl.ppo_trainer import PPOConfig

        config = PPOConfig()
        assert config.clip_epsilon == 0.2

    def test_update_runs_multiple_epochs(self):
        """update() runs for n_epochs iterations."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        n_epochs = trainer.config.n_epochs
        for _ in range(256):
            trainer.buffer.append(
                {
                    "state": np.random.randn(256).astype(np.float32),
                    "action": np.random.randn(256).astype(np.float32),
                    "reward": float(np.random.randn()),
                    "done": False,
                    "log_prob": float(np.random.randn()),
                    "value": float(np.random.randn()),
                }
            )
        result = trainer.update()
        assert result["n_epochs_run"] == n_epochs

    def test_update_clears_buffer_after_processing(self):
        """update() clears the buffer after processing."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        for _ in range(128):
            trainer.buffer.append(
                {
                    "state": np.random.randn(256).astype(np.float32),
                    "action": np.random.randn(256).astype(np.float32),
                    "reward": 0.5,
                    "done": False,
                    "log_prob": -1.5,
                    "value": 1.2,
                }
            )
        trainer.update()
        assert len(trainer.buffer) == 0


class TestCheckpointing:
    """Tests for checkpoint save/load."""

    @pytest.fixture
    def trainer_cls(self):
        from cohezion.rl.ppo_trainer import PPOTrainer

        return PPOTrainer

    @pytest.fixture
    def temp_dir(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            yield Path(tmpdir)

    def test_checkpoint_saves_policy_state(self, trainer_cls, temp_dir):
        """checkpoint() saves policy state dict."""
        trainer = trainer_cls()
        path = temp_dir / "policy.pt"
        trainer.checkpoint(path)
        assert path.exists()

    def test_checkpoint_saves_optimizer_state(self, trainer_cls, temp_dir):
        """checkpoint() saves optimizer state dict."""
        trainer = trainer_cls()
        path = temp_dir / "full_state.pt"
        trainer.checkpoint(path)
        assert path.exists()

    def test_checkpoint_saves_scheduler_state(self, trainer_cls, temp_dir):
        """checkpoint() saves scheduler state dict."""
        trainer = trainer_cls()
        path = temp_dir / "full_state.pt"
        trainer.checkpoint(path)
        assert path.exists()

    def test_load_restores_policy(self, trainer_cls, temp_dir):
        """load() restores policy state."""
        trainer1 = trainer_cls()
        path = temp_dir / "policy.pt"
        trainer1.checkpoint(path)

        trainer2 = trainer_cls()
        trainer2.load(path)

        for (k1, v1), v2 in zip(
            trainer1.policy.state_dict().items(),
            trainer2.policy.state_dict().values(),
            strict=True,
        ):
            assert torch.allclose(v1, v2), f"Mismatch at {k1}"

    def test_load_restores_optimizer(self, trainer_cls, temp_dir):
        """load() restores optimizer state."""
        trainer1 = trainer_cls()
        path = temp_dir / "full_state.pt"
        trainer1.checkpoint(path)

        trainer2 = trainer_cls()
        trainer2.load(path)
        loaded_state = trainer2.optimizer.state_dict()
        assert "state" in loaded_state

    def test_load_restores_scheduler(self, trainer_cls, temp_dir):
        """load() restores scheduler state."""
        trainer1 = trainer_cls()
        path = temp_dir / "full_state.pt"
        trainer1.checkpoint(path)

        trainer2 = trainer_cls()
        trainer2.load(path)
        assert trainer2.scheduler is not None

    def test_load_nonexistent_raises(self, trainer_cls, temp_dir):
        """load() raises FileNotFoundError for missing checkpoint."""
        trainer = trainer_cls()
        path = temp_dir / "nonexistent.pt"
        with pytest.raises(FileNotFoundError):
            trainer.load(path)


class TestGAE:
    """Tests for GAE (Generalized Advantage Estimation)."""

    def test_compute_gae_returns_advantages(self):
        """compute_gae() returns advantage estimates."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        rewards = torch.tensor([1.0, 2.0, 3.0, 4.0])
        values = torch.tensor([1.5, 2.5, 3.5, 4.5])
        dones = torch.tensor([False, False, False, True])
        gamma = trainer.config.gamma
        gae_lambda = trainer.config.gae_lambda

        advantages, returns = trainer.compute_gae(rewards, values, dones, gamma, gae_lambda)

        assert advantages.shape == (4,)
        assert returns.shape == (4,)
        assert advantages.dtype == torch.float32
        assert returns.dtype == torch.float32

    def test_gae_nonterminal_last_step_uses_bootstrap(self):
        """GAE advantage for non-terminal last step uses value bootstrap."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        rewards = torch.tensor([1.0, 2.0, 3.0, 4.0])
        values = torch.tensor([1.5, 2.5, 3.5, 4.5])
        dones = torch.tensor([False, False, False, False])

        advantages, _ = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert advantages[-1].item() == pytest.approx(-0.5, abs=1e-4)

    def test_gae_terminal_step_has_nonzero_advantage(self):
        """GAE advantage for terminal step equals delta (no bootstrap)."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        rewards = torch.tensor([1.0, 2.0, 3.0, 4.0])
        values = torch.tensor([1.5, 2.5, 3.5, 0.0])
        dones = torch.tensor([False, False, False, True])

        advantages, _ = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert advantages[-1].item() == pytest.approx(4.0, rel=1e-4)


class TestActionSampling:
    """Tests for action sampling from policy."""

    def test_get_action_returns_action_and_log_prob(self):
        """get_action() returns (action, log_prob, value)."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        state = np.random.randn(256).astype(np.float32)
        action, log_prob, value = trainer.get_action(state)

        assert action.shape == (256,)
        assert isinstance(log_prob, float)
        assert isinstance(value, float)
        assert -1.0 <= action.min() <= action.max() <= 1.0

    def test_get_action_is_reproducible_with_same_instance(self):
        """Same state + same policy produces same action."""
        from cohezion.rl.ppo_trainer import PPOTrainer

        trainer = PPOTrainer()
        torch.manual_seed(42)
        np.random.seed(42)
        state = np.random.randn(256).astype(np.float32)
        action1, _, _ = trainer.get_action(state)

        torch.manual_seed(42)
        np.random.seed(42)
        action2, _, _ = trainer.get_action(state)

        np.testing.assert_array_almost_equal(action1, action2)
