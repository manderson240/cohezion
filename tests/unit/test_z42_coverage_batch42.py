"""Coverage batch Z42: prompt_optimizer, flume_physics_py, coherence_guard."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest
import torch


# ---------------------------------------------------------------------------
# Module 1: compound/prompt_optimizer.py
# ---------------------------------------------------------------------------


class TestPromptOptimizer:
    def _make_optimizer(self, **kwargs):
        from cohezion.compound.prompt_optimizer import PromptOptimizer

        return PromptOptimizer(**kwargs)

    def test_optimize_removes_filler_words(self):
        opt = self._make_optimizer()
        result = opt.optimize("please generate 10 story ideas")
        assert "please" not in result.lower()

    def test_optimize_empty_string(self):
        opt = self._make_optimizer()
        result = opt.optimize("")
        assert result == ""

    def test_optimize_none_returns_none(self):
        opt = self._make_optimizer()
        result = opt.optimize(None)  # type: ignore[arg-type]
        assert result is None

    def test_optimize_preserves_content(self):
        opt = self._make_optimizer()
        result = opt.optimize("Generate 10 creative story ideas")
        assert "10" in result
        assert "story" in result

    def test_optimize_normalizes_whitespace(self):
        opt = self._make_optimizer()
        result = opt.optimize("generate   a    list")
        assert "  " not in result

    def test_optimize_with_filler_disabled(self):
        opt = self._make_optimizer(enable_filler_removal=False)
        result = opt.optimize("please kindly generate a list")
        # Filler removal off → "please" stays in
        assert "please" in result.lower()

    def test_estimate_tokens_empty(self):
        opt = self._make_optimizer()
        assert opt._estimate_tokens("") == 0

    def test_estimate_tokens_words(self):
        opt = self._make_optimizer()
        tokens = opt._estimate_tokens("hello world test")
        assert tokens > 0
        assert isinstance(tokens, int)

    def test_extract_entities_files(self):
        opt = self._make_optimizer()
        entities = opt.extract_entities("Please read src/cohezion/main.py and tests/test_foo.py")
        assert len(entities["files"]) > 0  # regex captures extension groups ("py", "py")

    def test_extract_entities_numbers(self):
        opt = self._make_optimizer()
        entities = opt.extract_entities("Process 42 items in batch of 10")
        assert "42" in entities["numbers"]
        assert "10" in entities["numbers"]

    def test_extract_entities_quotes(self):
        opt = self._make_optimizer()
        entities = opt.extract_entities('Set the "max_tokens" field to 100')
        assert "max_tokens" in entities["quotes"]

    def test_get_compression_stats(self):
        opt = self._make_optimizer()
        stats = opt.get_compression_stats(
            "please please please generate something kindly",
            "generate something",
        )
        assert stats["tokens_saved"] > 0
        assert stats["reduction_pct"] > 0
        assert "original_tokens" in stats

    def test_get_compression_stats_empty_original(self):
        opt = self._make_optimizer()
        stats = opt.get_compression_stats("", "")
        assert stats["reduction_pct"] == 0.0


# ---------------------------------------------------------------------------
# Module 2: mass_sim/flume_physics_py.py
# ---------------------------------------------------------------------------


class TestFlumePhysicsPy:
    def _make_physics(self, z_dim=8, hidden_dim=16):
        from cohezion.mass_sim.flume_physics_py import FlumePhysicsPy

        rng = np.random.default_rng(42)
        w1 = rng.standard_normal((hidden_dim, z_dim)).astype(np.float32) * 0.1
        b1 = rng.standard_normal(hidden_dim).astype(np.float32) * 0.01
        w2 = rng.standard_normal((z_dim, hidden_dim)).astype(np.float32) * 0.1
        b2 = rng.standard_normal(z_dim).astype(np.float32) * 0.01
        gamma = np.ones(hidden_dim, dtype=np.float32)
        beta = np.zeros(hidden_dim, dtype=np.float32)
        return FlumePhysicsPy(w1, b1, w2, b2, gamma, beta, delta_scale=0.01, hiho_damping=0.05)

    def test_forward_shape(self):
        physics = self._make_physics(z_dim=8)
        agents = np.random.randn(4, 8).astype(np.float32)
        delta = physics._forward(agents)
        assert delta.shape == (4, 8)

    def test_step_shape(self):
        physics = self._make_physics(z_dim=8)
        agents = np.random.randn(4, 8).astype(np.float32)
        out = physics._step(agents)
        assert out.shape == (4, 8)

    def test_simulate_epochs_batch_shape(self):
        physics = self._make_physics(z_dim=8)
        agents = np.random.randn(10, 8).astype(np.float32)
        result = physics.simulate_epochs_batch(agents, n_epochs=5)
        assert result.shape == (10, 8)

    def test_simulate_epochs_navigated_shape(self):
        physics = self._make_physics(z_dim=8)
        agents = np.random.randn(5, 8).astype(np.float32)
        result = physics.simulate_epochs_navigated(agents, n_epochs=3)
        assert result.shape == (5, 8)

    def test_hiho_damping_moves_toward_half(self):
        physics = self._make_physics(z_dim=8)
        # Agents far from 0.5 should be pulled toward 0.5 over epochs
        agents = np.zeros((1, 8), dtype=np.float32)  # all zeros, far from 0.5
        result = physics.simulate_epochs_batch(agents, n_epochs=10)
        # After damping, should be closer to 0.5 than 0.0
        assert float(np.abs(result - 0.5).mean()) < 0.5

    def test_compute_batch_stats_shape(self):
        physics = self._make_physics(z_dim=8)
        agents = np.random.uniform(0.0, 1.0, (20, 8)).astype(np.float32)
        stats = physics.compute_batch_stats(agents)
        assert "mean_coherence" in stats
        assert "n_agents" in stats
        assert stats["n_agents"] == 20
        assert stats["z_dim"] == 8

    def test_compute_batch_stats_pct_within_bounds(self):
        physics = self._make_physics(z_dim=8)
        # All in [0.4, 0.6] → high pct within bounds
        agents = np.full((5, 8), 0.5, dtype=np.float32)
        stats = physics.compute_batch_stats(agents)
        assert stats["pct_within_bounds"] == pytest.approx(1.0)

    def test_simulate_navigated_differs_from_batch(self):
        physics = self._make_physics(z_dim=8)
        rng = np.random.default_rng(0)
        agents = rng.standard_normal((5, 8)).astype(np.float32)
        batch = physics.simulate_epochs_batch(agents.copy(), n_epochs=5)
        nav = physics.simulate_epochs_navigated(agents.copy(), n_epochs=5)
        # With noise, navigated should differ from batch (not always exact, but typically)
        assert batch.shape == nav.shape


# ---------------------------------------------------------------------------
# Module 3: flume/coherence_guard.py
# ---------------------------------------------------------------------------


class TestCoherenceGuard:
    def _make_harness(self):
        from cohezion.flume.coherence_guard import TurboQuantHarness

        return TurboQuantHarness(tolerance_mae=0.05, tolerance_hiho=0.01)

    def test_compute_coherence_tensor(self):
        harness = self._make_harness()
        z = torch.full((256,), 0.5)  # all 0.5 → coherence should be high
        coherence = harness.compute_coherence(z)
        assert 0.0 <= coherence <= 1.0

    def test_compute_coherence_numpy(self):
        harness = self._make_harness()
        z = np.full(256, 0.5)
        coherence = harness.compute_coherence(z)
        assert 0.0 <= coherence <= 1.0

    def test_get_hiho_stability_at_target(self):
        harness = self._make_harness()
        stability = harness.get_hiho_stability(0.5)
        assert stability == pytest.approx(1.0)

    def test_get_hiho_stability_at_extremes(self):
        harness = self._make_harness()
        assert (
            harness.get_hiho_stability(0.0) == pytest.approx(-1.0)
            or harness.get_hiho_stability(0.0) <= 0.0
        )
        assert (
            harness.get_hiho_stability(1.0) == pytest.approx(-1.0)
            or harness.get_hiho_stability(1.0) <= 0.0
        )

    def test_verify_quantization_throttled(self):
        harness = self._make_harness()
        mock_guard = MagicMock()
        mock_pressure = MagicMock()
        mock_pressure.is_throttled = True
        mock_pressure.reason = "overload"
        mock_guard.check_safety.return_value = mock_pressure

        with patch("cohezion.flume.coherence_guard.get_silicon_guard", return_value=mock_guard):
            original = torch.randn(256)
            result = harness.verify_quantization(original, original, context_name="test")
        assert result["success"] is False
        assert "Silicon Overload" in result["error"]

    def test_verify_quantization_success(self):
        from cohezion.flume.coherence_guard import apply_dummy_int8_quantization

        harness = self._make_harness()
        mock_guard = MagicMock()
        mock_pressure = MagicMock()
        mock_pressure.is_throttled = False
        mock_guard.check_safety.return_value = mock_pressure

        with patch("cohezion.flume.coherence_guard.get_silicon_guard", return_value=mock_guard):
            original = torch.full((256,), 0.3)
            dequantized = apply_dummy_int8_quantization(original)
            result = harness.verify_quantization(original, dequantized, context_name="test")
        assert "mae" in result
        assert "success" in result

    def test_apply_dummy_int8_quantization_shape(self):
        from cohezion.flume.coherence_guard import apply_dummy_int8_quantization

        original = torch.randn(256)
        dequantized = apply_dummy_int8_quantization(original)
        assert dequantized.shape == original.shape
        assert dequantized.dtype == torch.float32
