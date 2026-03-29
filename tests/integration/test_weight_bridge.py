"""Integration tests for WeightBridge: policy -> FlumePhysics weight transfer."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch

from cohezion.pipeline.weight_bridge import WeightBridge
from cohezion.rl.trainer import PolicyNetwork


@pytest.fixture()
def policy_checkpoint(tmp_path):
    """Create a temporary PolicyNetwork checkpoint for testing."""
    state_dim = 256
    hidden_dim = 128
    action_dim = 256

    policy = PolicyNetwork(state_dim=state_dim, action_dim=action_dim, hidden=hidden_dim)
    ckpt_path = tmp_path / "test_policy.pt"
    torch.save(policy.state_dict(), ckpt_path)
    return ckpt_path, state_dim, hidden_dim, action_dim


class TestPolicyToFlumeWeights:
    """Test weight extraction and layer collapsing."""

    def test_weight_shapes(self, policy_checkpoint):
        """Extracted weights have correct shapes for the Rust engine."""
        ckpt_path, state_dim, hidden_dim, action_dim = policy_checkpoint
        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        assert weights["w1"].shape == (hidden_dim, state_dim)
        assert weights["b1"].shape == (hidden_dim,)
        assert weights["w2"].shape == (action_dim, hidden_dim)
        assert weights["b2"].shape == (action_dim,)
        assert weights["gamma"].shape == (hidden_dim,)
        assert weights["beta"].shape == (hidden_dim,)

    def test_weight_dtypes(self, policy_checkpoint):
        """All weights are float32 for Rust compatibility."""
        ckpt_path, *_ = policy_checkpoint
        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        for name, arr in weights.items():
            assert arr.dtype == np.float32, f"{name} has dtype {arr.dtype}"

    def test_layer_collapse_correctness(self, policy_checkpoint):
        """Collapsed w2 = mean_head.weight @ shared[2].weight."""
        ckpt_path, *_ = policy_checkpoint
        state_dict = torch.load(ckpt_path, map_location="cpu", weights_only=True)

        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        # Manually compute expected collapsed weights
        shared2_w = state_dict["shared.2.weight"].numpy()
        shared2_b = state_dict["shared.2.bias"].numpy()
        mean_w = state_dict["mean_head.weight"].numpy()
        mean_b = state_dict["mean_head.bias"].numpy()

        expected_w2 = mean_w @ shared2_w
        expected_b2 = mean_b + mean_w @ shared2_b

        np.testing.assert_allclose(weights["w2"], expected_w2, rtol=1e-3, atol=1e-8)
        np.testing.assert_allclose(weights["b2"], expected_b2, rtol=1e-3, atol=1e-8)

    def test_layernorm_defaults(self, policy_checkpoint):
        """LayerNorm gamma=1, beta=0.5 (HIHO target shift)."""
        ckpt_path, _, hidden_dim, _ = policy_checkpoint
        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        np.testing.assert_array_equal(weights["gamma"], np.ones(hidden_dim, dtype=np.float32))
        np.testing.assert_array_equal(weights["beta"], np.full(hidden_dim, 0.5, dtype=np.float32))

    def test_weights_are_finite(self, policy_checkpoint):
        """No NaN or Inf values in any extracted weight."""
        ckpt_path, *_ = policy_checkpoint
        weights = WeightBridge.policy_to_flume_weights(ckpt_path)

        for name, arr in weights.items():
            assert np.all(np.isfinite(arr)), f"{name} contains non-finite values"


class TestLoadPolicyNetwork:
    """Test checkpoint load round-trip."""

    def test_roundtrip(self, policy_checkpoint):
        """Load a saved checkpoint and verify it produces a working PolicyNetwork."""
        ckpt_path, state_dim, _hidden_dim, action_dim = policy_checkpoint
        policy = WeightBridge.load_policy_network(ckpt_path)

        assert isinstance(policy, PolicyNetwork)

        # Verify forward pass works
        state = np.random.randn(state_dim).astype(np.float32)
        action, _log_prob = policy.get_action(state)
        assert action.shape == (action_dim,)
        assert np.all(np.isfinite(action))

    def test_dimension_inference(self, policy_checkpoint):
        """Dimensions are correctly inferred from the state dict."""
        ckpt_path, state_dim, hidden_dim, action_dim = policy_checkpoint
        policy = WeightBridge.load_policy_network(ckpt_path)

        # Verify the network architecture matches
        assert policy.shared[0].in_features == state_dim
        assert policy.shared[0].out_features == hidden_dim
        assert policy.mean_head.out_features == action_dim


class TestValidateCoherence:
    """Test coherence validation with mocked FlumePhysics."""

    @staticmethod
    def _make_mock_physics(mean_coherence: float, pct_within_bounds: float):
        """Create a mock FlumePhysics that returns controlled stats."""
        mock = MagicMock()
        # simulate_epochs_navigated returns evolved agents
        mock.simulate_epochs_navigated.return_value = np.random.randn(100, 256).astype(np.float32)
        mock.compute_batch_stats.return_value = {
            "mean_coherence": mean_coherence,
            "pct_within_bounds": pct_within_bounds,
        }
        return mock

    def test_valid_coherence(self):
        """Coherence in [0.3, 0.7] is marked valid."""
        mock_physics = self._make_mock_physics(0.50, 0.92)
        result = WeightBridge.validate_coherence(mock_physics, n_agents=50, n_epochs=10)

        assert result["valid"] is True
        assert result["mean_coherence"] == pytest.approx(0.50)
        assert result["pct_within_bounds"] == pytest.approx(0.92)

    def test_invalid_low_coherence(self):
        """Coherence below 0.3 is marked invalid."""
        mock_physics = self._make_mock_physics(0.10, 0.05)
        result = WeightBridge.validate_coherence(mock_physics, n_agents=50, n_epochs=10)

        assert result["valid"] is False
        assert result["mean_coherence"] == pytest.approx(0.10)

    def test_invalid_high_coherence(self):
        """Coherence above 0.7 is marked invalid."""
        mock_physics = self._make_mock_physics(0.85, 0.95)
        result = WeightBridge.validate_coherence(mock_physics, n_agents=50, n_epochs=10)

        assert result["valid"] is False

    def test_boundary_coherence(self):
        """Coherence at exact boundaries (0.3, 0.7) is valid."""
        for coh in (0.3, 0.7):
            mock_physics = self._make_mock_physics(coh, 0.80)
            result = WeightBridge.validate_coherence(mock_physics, n_agents=50, n_epochs=10)
            assert result["valid"] is True, f"coherence={coh} should be valid"

    def test_calls_physics_with_correct_agents(self):
        """validate_coherence passes correct shaped agents to physics engine."""
        mock_physics = self._make_mock_physics(0.50, 0.90)
        WeightBridge.validate_coherence(mock_physics, n_agents=100, n_epochs=50, seed=42)

        args = mock_physics.simulate_epochs_navigated.call_args
        agents = args[0][0]  # first positional arg
        n_epochs = args[0][1]  # second positional arg

        assert agents.shape == (100, 256)
        assert agents.dtype == np.float32
        assert n_epochs == 50


class TestPolicyToFlumePhysics:
    """Test full pipeline with mocked Rust extension."""

    def test_raises_when_rust_unavailable(self, policy_checkpoint):
        """Raises RuntimeError when cohezion_core_rs is not importable."""
        ckpt_path, *_ = policy_checkpoint
        with patch("cohezion.pipeline.weight_bridge._import_flume_physics", return_value=None):
            with pytest.raises(RuntimeError, match="cohezion_core_rs not available"):
                WeightBridge.policy_to_flume_physics(ckpt_path)

    def test_creates_physics_with_mock(self, policy_checkpoint):
        """Full pipeline constructs FlumePhysics with collapsed weights."""
        ckpt_path, state_dim, hidden_dim, action_dim = policy_checkpoint
        mock_cls = MagicMock()
        mock_instance = MagicMock()
        mock_cls.return_value = mock_instance

        with patch(
            "cohezion.pipeline.weight_bridge._import_flume_physics",
            return_value=mock_cls,
        ):
            result = WeightBridge.policy_to_flume_physics(
                ckpt_path, delta_scale=0.02, hiho_damping=0.03
            )

        assert result is mock_instance
        mock_cls.assert_called_once()
        call_kwargs = mock_cls.call_args
        # Verify positional args are numpy arrays with correct shapes
        w1 = call_kwargs[0][0]
        b1 = call_kwargs[0][1]
        w2 = call_kwargs[0][2]
        b2 = call_kwargs[0][3]
        gamma = call_kwargs[0][4]
        beta = call_kwargs[0][5]
        assert w1.shape == (hidden_dim, state_dim)
        assert b1.shape == (hidden_dim,)
        assert w2.shape == (action_dim, hidden_dim)
        assert b2.shape == (action_dim,)
        assert gamma.shape == (hidden_dim,)
        assert beta.shape == (hidden_dim,)
        assert call_kwargs[1]["delta_scale"] == 0.02
        assert call_kwargs[1]["hiho_damping"] == 0.03
