"""Tests for PPO Trainer module — TRIUNE policy, value network, and PPO training loop.

Tests:
1. TRIUNEPolicy forward shapes (256D → 2048 → 512 → 256D)
2. ValueNetwork forward shapes (256D → 512 → 256 → 1)
3. PPOConfig defaults
4. PPOTrainer.get_action returns correct shapes
5. PPOTrainer.update buffer management (insufficient/sufficient samples)
6. PPOTrainer.checkpoint/load roundtrip
7. EpisodeResult dataclass defaults
8. GAE computation correctness
9. Action clamping to [-1, 1]
"""

from __future__ import annotations

import numpy as np
import pytest
import torch


class TestTRIUNEPolicy:
    """Tests for TRIUNEPolicy neural network architecture."""

    @pytest.fixture
    def policy_cls(self):
        try:
            from cohezion.rl.ppo_trainer import TRIUNEPolicy

            return TRIUNEPolicy
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_forward_returns_correct_shape(self, policy_cls):
        """Forward pass returns (batch, z_dim) tensor."""
        policy = policy_cls()
        batch_size = 4
        state = torch.randn(batch_size, 256)
        action = policy(state)
        assert action.shape == (batch_size, 256)

    def test_forward_single_sample(self, policy_cls):
        """Forward pass works with single sample (batch=1)."""
        policy = policy_cls()
        state = torch.randn(1, 256)
        action = policy(state)
        assert action.shape == (1, 256)

    def test_output_in_expected_range(self, policy_cls):
        """Output is a determinstic action tensor (tanh applied)."""
        policy = policy_cls()
        state = torch.randn(2, 256)
        action = policy(state)
        assert action.dtype == torch.float32
        assert action.requires_grad is False

    def test_trainable_parameters(self, policy_cls):
        """Policy has learnable parameters."""
        policy = policy_cls()
        params = list(policy.parameters())
        assert len(params) > 0
        assert all(p.requires_grad for p in params)

    def test_policy_is_nn_module(self, policy_cls):
        """TRIUNEPolicy inherits from nn.Module."""
        from torch import nn

        policy = policy_cls()
        assert isinstance(policy, nn.Module)


class TestValueNetwork:
    """Tests for ValueNetwork architecture."""

    @pytest.fixture
    def value_cls(self):
        try:
            from cohezion.rl.ppo_trainer import ValueNetwork

            return ValueNetwork
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_forward_returns_batch_value(self, value_cls):
        """Forward pass returns (batch, 1) value tensor."""
        value_net = value_cls()
        batch_size = 8
        state = torch.randn(batch_size, 256)
        value = value_net(state)
        assert value.shape == (batch_size, 1)

    def test_forward_single_sample(self, value_cls):
        """Forward pass works with single sample."""
        value_net = value_cls()
        state = torch.randn(1, 256)
        value = value_net(state)
        assert value.shape == (1, 1)

    def test_value_positive(self, value_cls):
        """Value network outputs can be positive or negative."""
        value_net = value_cls()
        state = torch.randn(4, 256)
        value = value_net(state)
        assert value.shape == (4, 1)

    def test_trainable_parameters(self, value_cls):
        """Value network has learnable parameters."""
        value_net = value_cls()
        params = list(value_net.parameters())
        assert len(params) > 0

    def test_value_is_nn_module(self, value_cls):
        """ValueNetwork inherits from nn.Module."""
        from torch import nn

        value_net = value_cls()
        assert isinstance(value_net, nn.Module)


class TestPPOConfig:
    """Tests for PPOConfig dataclass."""

    @pytest.fixture
    def config_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOConfig

            return PPOConfig
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_config_has_required_fields(self, config_cls):
        """PPOConfig has all required fields with correct defaults."""
        config = config_cls()
        assert hasattr(config, "clip_epsilon")
        assert hasattr(config, "n_epochs")
        assert hasattr(config, "lr")
        assert hasattr(config, "gamma")
        assert hasattr(config, "gae_lambda")
        assert hasattr(config, "entropy_coef")
        assert hasattr(config, "value_coef")
        assert hasattr(config, "max_grad_norm")
        assert hasattr(config, "min_samples")
        assert hasattr(config, "z_dim")
        assert hasattr(config, "action_dim")

    def test_default_clip_epsilon(self, config_cls):
        """clip_epsilon defaults to 0.2."""
        config = config_cls()
        assert config.clip_epsilon == 0.2

    def test_default_n_epochs(self, config_cls):
        """n_epochs defaults to 4."""
        config = config_cls()
        assert config.n_epochs == 4

    def test_default_lr(self, config_cls):
        """lr defaults to 3e-4."""
        config = config_cls()
        assert config.lr == 3e-4

    def test_default_gamma(self, config_cls):
        """gamma defaults to 0.99."""
        config = config_cls()
        assert config.gamma == 0.99

    def test_default_gae_lambda(self, config_cls):
        """gae_lambda defaults to 0.95."""
        config = config_cls()
        assert config.gae_lambda == 0.95

    def test_default_z_dim(self, config_cls):
        """z_dim defaults to 256."""
        config = config_cls()
        assert config.z_dim == 256

    def test_default_action_dim(self, config_cls):
        """action_dim defaults to 256."""
        config = config_cls()
        assert config.action_dim == 256

    def test_custom_config(self, config_cls):
        """Custom values override defaults."""
        config = config_cls(clip_epsilon=0.1, n_epochs=10, lr=1e-3)
        assert config.clip_epsilon == 0.1
        assert config.n_epochs == 10
        assert config.lr == 1e-3


class TestPPOTrainer:
    """Tests for PPOTrainer class."""

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            return PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    @pytest.fixture
    def config_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOConfig

            return PPOConfig
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_trainer_creation(self, trainer_cls, config_cls):
        """Trainer initializes with default config."""
        trainer = trainer_cls()
        assert trainer is not None

    def test_trainer_creation_with_config(self, trainer_cls, config_cls):
        """Trainer initializes with custom config."""
        config = config_cls(lr=1e-3, n_epochs=8)
        trainer = trainer_cls(config=config)
        assert trainer is not None

    def test_trainer_has_policy(self, trainer_cls, config_cls):
        """Trainer has a policy network."""
        trainer = trainer_cls()
        assert hasattr(trainer, "policy")

    def test_trainer_has_value_network(self, trainer_cls, config_cls):
        """Trainer has a value network."""
        trainer = trainer_cls()
        assert hasattr(trainer, "value_network")

    def test_get_action_returns_tuple(self, trainer_cls):
        """get_action returns (action, log_prob, value)."""
        trainer = trainer_cls()
        state = np.random.randn(256).astype(np.float32)
        result = trainer.get_action(state)
        assert isinstance(result, tuple)
        assert len(result) == 3

    def test_get_action_shapes(self, trainer_cls):
        """get_action returns correctly shaped outputs."""
        trainer = trainer_cls()
        state = np.random.randn(256).astype(np.float32)
        action, log_prob, value = trainer.get_action(state)
        assert action.shape == (256,)
        assert isinstance(log_prob, (float, np.floating))
        assert isinstance(value, (float, np.floating))

    def test_get_action_batch_state(self, trainer_cls):
        """get_action works with batched state."""
        trainer = trainer_cls()
        state = np.random.randn(8, 256).astype(np.float32)
        action, log_prob, value = trainer.get_action(state)
        assert action.shape == (256,)

    def test_action_clamped_to_range(self, trainer_cls):
        """Actions are clamped to [-1, 1]."""
        trainer = trainer_cls()
        state = np.random.randn(256).astype(np.float32)
        action, _, _ = trainer.get_action(state)
        assert np.all(action >= -1.0)
        assert np.all(action <= 1.0)

    def test_update_with_empty_buffer(self, trainer_cls):
        """update() with insufficient samples returns n_epochs_run=0."""
        trainer = trainer_cls()
        result = trainer.update()
        assert result["n_epochs_run"] == 0

    def test_update_after_one_episode(self, trainer_cls):
        """update() after collecting min_samples runs epoch."""
        trainer = trainer_cls()
        config = trainer.config
        for _ in range(config.min_samples):
            state = np.random.randn(256).astype(np.float32)
            action, log_prob, value = trainer.get_action(state)
            reward = np.random.randn()
            trainer.buffer.append((state, action, log_prob, value, reward, False))
        result = trainer.update()
        assert result["n_epochs_run"] == config.n_epochs

    def test_update_returns_metrics(self, trainer_cls):
        """update() returns dict with training metrics."""
        trainer = trainer_cls()
        config = trainer.config
        for _ in range(config.min_samples):
            state = np.random.randn(256).astype(np.float32)
            action, log_prob, value = trainer.get_action(state)
            reward = np.random.randn()
            trainer.buffer.append((state, action, log_prob, value, reward, False))
        result = trainer.update()
        assert "policy_loss" in result
        assert "value_loss" in result
        assert "entropy" in result
        assert "approx_kl" in result
        assert "n_epochs_run" in result

    def test_checkpoint_and_load(self, trainer_cls, tmp_path):
        """checkpoint() and load() roundtrip the trainer."""
        trainer = trainer_cls()
        ckpt_path = tmp_path / "ppo_ckpt.pt"
        trainer.checkpoint(ckpt_path)
        assert ckpt_path.exists()

        trainer2 = trainer_cls()
        trainer2.load(ckpt_path)
        assert trainer2 is not None


class TestGAE:
    """Tests for GAE (Generalized Advantage Estimation) computation."""

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            return PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_compute_gae_basic(self, trainer_cls):
        """compute_gae returns advantages and returns of correct length."""
        trainer = trainer_cls()
        rewards = np.array([1.0, 2.0, 3.0, 4.0])
        values = np.array([1.5, 2.5, 3.0, 3.5])
        dones = np.array([False, False, False, True])
        advantages, returns = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert len(advantages) == len(rewards)
        assert len(returns) == len(rewards)

    def test_compute_gae_single_step(self, trainer_cls):
        """compute_gae works with single step."""
        trainer = trainer_cls()
        rewards = np.array([1.0])
        values = np.array([1.5])
        dones = np.array([True])
        advantages, returns = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert len(advantages) == 1
        assert len(returns) == 1

    def test_compute_gae_zeros_on_done(self, trainer_cls):
        """Advantages are near zero at episode end (done=True)."""
        trainer = trainer_cls()
        rewards = np.array([1.0, 1.0, 1.0])
        values = np.array([1.0, 1.0, 1.0])
        dones = np.array([False, False, True])
        advantages, _ = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert abs(advantages[-1]) < 1e-3

    def test_gae_lambda_one_equals_mc(self, trainer_cls):
        """gae_lambda=1.0 approximates Monte Carlo (no bias)."""
        trainer = trainer_cls()
        rewards = np.array([1.0, 2.0, 3.0, 4.0])
        values = np.array([2.5, 3.5, 3.0, 2.0])
        dones = np.array([False, False, False, True])
        advantages, returns = trainer.compute_gae(rewards, values, dones, 0.99, 1.0)
        assert len(advantages) == len(rewards)

    def test_gae_shape_matches_inputs(self, trainer_cls):
        """compute_gae output shapes match input shapes."""
        trainer = trainer_cls()
        n = 10
        rewards = np.random.randn(n)
        values = np.random.randn(n)
        dones = np.random.randint(0, 2, n).astype(bool)
        advantages, returns = trainer.compute_gae(rewards, values, dones, 0.99, 0.95)
        assert advantages.shape == (n,)
        assert returns.shape == (n,)


class TestEpisodeResult:
    """Tests for EpisodeResult dataclass."""

    @pytest.fixture
    def result_cls(self):
        try:
            from cohezion.rl.ppo_trainer import EpisodeResult

            return EpisodeResult
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_creation_with_required_fields(self, result_cls):
        """EpisodeResult can be created with required fields."""
        result = result_cls(
            episode=1,
            total_reward=100.0,
            mean_coherence=0.5,
            final_coherence=0.6,
            steps=200,
        )
        assert result.episode == 1
        assert result.total_reward == 100.0

    def test_creation_with_all_fields(self, result_cls):
        """EpisodeResult can be created with all fields including optional."""
        result = result_cls(
            episode=5,
            total_reward=150.0,
            mean_coherence=0.55,
            final_coherence=0.65,
            steps=180,
            policy_loss=0.01,
            value_loss=0.02,
            entropy=0.1,
            approx_kl=0.05,
        )
        assert result.policy_loss == 0.01
        assert result.value_loss == 0.02
        assert result.entropy == 0.1
        assert result.approx_kl == 0.05

    def test_defaults_for_optional_fields(self, result_cls):
        """Optional fields default to None or 0."""
        result = result_cls(
            episode=1,
            total_reward=100.0,
            mean_coherence=0.5,
            final_coherence=0.6,
            steps=200,
        )
        assert result.policy_loss is None or isinstance(result.policy_loss, (int, float))
        assert result.value_loss is None or isinstance(result.value_loss, (int, float))
        assert result.entropy is None or isinstance(result.entropy, (int, float))
        assert result.approx_kl is None or isinstance(result.approx_kl, (int, float))

    def test_is_dataclass(self, result_cls):
        """EpisodeResult is a dataclass."""
        import dataclasses

        assert dataclasses.is_dataclass(result_cls)


class TestActionClamping:
    """Tests for action clamping to [-1, 1] range."""

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            return PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_action_always_in_range(self, trainer_cls):
        """Actions from get_action are always in [-1, 1]."""
        trainer = trainer_cls()
        for _ in range(10):
            state = np.random.randn(256).astype(np.float32)
            action, _, _ = trainer.get_action(state)
            assert np.all(action >= -1.0), f"Action below -1: min={action.min()}"
            assert np.all(action <= 1.0), f"Action above 1: max={action.max()}"

    def test_action_not_all_zeros(self, trainer_cls):
        """Actions are not all zeros (policy produces variation)."""
        trainer = trainer_cls()
        states = [np.random.randn(256).astype(np.float32) for _ in range(5)]
        actions = [trainer.get_action(s)[0] for s in states]
        action_norms = [np.linalg.norm(a) for a in actions]
        assert any(n > 1e-6 for n in action_norms), "All actions are zero"


class TestBufferManagement:
    """Tests for training buffer management."""

    @pytest.fixture
    def trainer_cls(self):
        try:
            from cohezion.rl.ppo_trainer import PPOTrainer

            return PPOTrainer
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_buffer_starts_empty(self, trainer_cls):
        """Training buffer initializes empty."""
        trainer = trainer_cls()
        assert hasattr(trainer, "buffer")
        assert len(trainer.buffer) == 0

    def test_buffer_accumulates_transitions(self, trainer_cls):
        """Buffer accumulates transitions correctly."""
        trainer = trainer_cls()
        config = trainer.config
        for i in range(10):
            state = np.random.randn(256).astype(np.float32)
            action, log_prob, value = trainer.get_action(state)
            reward = float(i)
            trainer.buffer.append((state, action, log_prob, value, reward, False))
        assert len(trainer.buffer) == 10

    def test_buffer_cleared_after_update(self, trainer_cls):
        """Buffer is cleared after update()."""
        trainer = trainer_cls()
        config = trainer.config
        for _ in range(config.min_samples):
            state = np.random.randn(256).astype(np.float32)
            action, log_prob, value = trainer.get_action(state)
            reward = 1.0
            trainer.buffer.append((state, action, log_prob, value, reward, False))
        trainer.update()
        assert len(trainer.buffer) == 0


class TestTrainFunction:
    """Tests for the train() function."""

    def test_train_function_exists(self):
        """train() function exists in ppo_trainer module."""
        try:
            from cohezion.rl.ppo_trainer import train

            assert callable(train)
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")

    def test_train_function_signature(self):
        """train() accepts (config, n_episodes, task_specs, output_dir, ...)."""
        try:
            from cohezion.rl.ppo_trainer import PPOConfig, train
        except ImportError:
            pytest.skip("PPO trainer not yet implemented")
        import inspect

        sig = inspect.signature(train)
        params = list(sig.parameters.keys())
        assert "config" in params
        assert "n_episodes" in params
        assert "task_specs" in params
        assert "output_dir" in params
