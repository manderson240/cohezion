"""Tests for SVD-based latent basis health monitor.

T1 — Structural: LatentBasisMonitor has the required interface.
T2 — Behavioral: collapsed latent codes → is_healthy=False; diverse → is_healthy=True.
"""

import pytest
import torch

from cohezion.flume.latent_health import LatentBasisMonitor


# ---------------------------------------------------------------------------
# T1: Structural
# ---------------------------------------------------------------------------


class TestLatentBasisMonitorStructural:
    """Verify the public interface contract."""

    def test_methods_exist(self):
        monitor = LatentBasisMonitor()
        assert callable(getattr(monitor, "update", None))
        assert callable(getattr(monitor, "compute_health", None))
        assert callable(getattr(monitor, "reset", None))

    def test_default_expected_rank_ratio(self):
        monitor = LatentBasisMonitor()
        assert monitor.expected_rank_ratio == 0.5

    def test_compute_health_return_keys(self):
        monitor = LatentBasisMonitor()
        monitor.update(torch.randn(5, 16))
        result = monitor.compute_health()
        assert set(result.keys()) == {
            "effective_rank",
            "rank_ratio",
            "is_healthy",
            "top_singular_values",
        }

    def test_compute_health_types(self):
        monitor = LatentBasisMonitor()
        monitor.update(torch.randn(5, 16))
        result = monitor.compute_health()
        assert isinstance(result["effective_rank"], float)
        assert isinstance(result["rank_ratio"], float)
        assert isinstance(result["is_healthy"], bool)
        assert isinstance(result["top_singular_values"], list)

    def test_compute_health_raises_without_samples(self):
        monitor = LatentBasisMonitor()
        with pytest.raises(ValueError, match="No samples accumulated"):
            monitor.compute_health()

    def test_reset_clears_samples(self):
        monitor = LatentBasisMonitor()
        monitor.update(torch.randn(4, 16))
        monitor.reset()
        with pytest.raises(ValueError):
            monitor.compute_health()

    def test_has_samples_property(self):
        monitor = LatentBasisMonitor()
        assert not monitor.has_samples
        monitor.update(torch.randn(2, 8))
        assert monitor.has_samples
        monitor.reset()
        assert not monitor.has_samples


# ---------------------------------------------------------------------------
# T2: Behavioral (discriminating)
# ---------------------------------------------------------------------------


class TestLatentBasisMonitorBehavioral:
    """Collapsed vs diverse latent codes produce different health verdicts."""

    def test_collapsed_latent_codes_unhealthy(self):
        """All-zero latent codes collapse to zero variance → is_healthy=False.

        With default expected_rank_ratio=0.5, even the edge-case effective_rank=1.0
        gives rank_ratio = 1/256 ≈ 0.004, far below 0.5.
        """
        monitor = LatentBasisMonitor(expected_rank_ratio=0.5)
        # All identical → after centering the matrix is zero → rank collapses.
        z_collapsed = torch.zeros(10, 256)
        monitor.update(z_collapsed)
        result = monitor.compute_health()

        assert not result["is_healthy"], (
            f"Collapsed codes must be unhealthy; got rank_ratio={result['rank_ratio']:.4f}"
        )
        # Effective rank must be near 1 (minimum possible — complete collapse).
        assert result["effective_rank"] <= 2.0, (
            f"Collapsed codes must have near-1 effective rank; got {result['effective_rank']:.3f}"
        )

    def test_diverse_latent_codes_healthy(self):
        """Random latent codes span many directions → rank_ratio > threshold → is_healthy=True.

        With N=10 samples in D=256, rank ≤ min(N-1, D) = 9, so
        rank_ratio ≤ 9/256 ≈ 0.035.  We use a test-appropriate threshold of 0.01
        that cleanly separates collapsed from diverse while respecting the
        sample-count-bounded rank ceiling.
        """
        # Threshold appropriate for the rank ceiling imposed by 10 samples in 256-D.
        monitor = LatentBasisMonitor(expected_rank_ratio=0.01)
        torch.manual_seed(42)
        z_diverse = torch.randn(10, 256)  # Random → many effective directions.
        monitor.update(z_diverse)
        result = monitor.compute_health()

        assert result["is_healthy"], (
            f"Diverse codes must be healthy; got rank_ratio={result['rank_ratio']:.4f}"
        )
        # Effective rank must be well above 1 — meaningful spread across dimensions.
        assert result["effective_rank"] > 2.0, (
            f"Diverse codes must have effective rank >> 1; got {result['effective_rank']:.3f}"
        )

    def test_rank_ratio_in_unit_interval(self):
        """rank_ratio must always be in [0, 1]."""
        monitor = LatentBasisMonitor()
        torch.manual_seed(7)
        monitor.update(torch.randn(20, 64))
        result = monitor.compute_health()
        assert 0.0 <= result["rank_ratio"] <= 1.0

    def test_top_singular_values_length(self):
        """top_singular_values has at most 5 entries."""
        monitor = LatentBasisMonitor()
        monitor.update(torch.randn(8, 256))
        result = monitor.compute_health()
        assert len(result["top_singular_values"]) <= 5

    def test_uses_linalg_svd_not_deprecated(self):
        """Smoke-test that torch.linalg.svd is called (not the deprecated torch.svd)."""
        import inspect

        from cohezion.flume import latent_health as lh

        src = inspect.getsource(lh.LatentBasisMonitor.compute_health)
        assert "torch.linalg.svd" in src, "Must use torch.linalg.svd, not deprecated torch.svd"
        assert "torch.svd(" not in src, "Must not use deprecated torch.svd()"


# ---------------------------------------------------------------------------
# FlumeVAE wiring smoke test
# ---------------------------------------------------------------------------


class TestFlumeVAELatentMonitorWiring:
    """Verify that FlumeVAE correctly wires into LatentBasisMonitor."""

    def test_latent_monitor_attribute_exists(self):
        from cohezion.flume.vae import FlumeVAE, FlumeVAEConfig

        model = FlumeVAE(FlumeVAEConfig(vocab_size=64, embed_dim=32, z_dim=16))
        assert hasattr(model, "latent_monitor")
        assert model.latent_monitor is None

    def test_get_latent_health_returns_none_without_monitor(self):
        from cohezion.flume.vae import FlumeVAE, FlumeVAEConfig

        model = FlumeVAE(FlumeVAEConfig(vocab_size=64, embed_dim=32, z_dim=16))
        assert model.get_latent_health() is None

    def test_encode_feeds_monitor(self):
        """Attaching a monitor and calling encode() should populate it."""
        from cohezion.flume.vae import FlumeVAE

        model = FlumeVAE(input_dim=32, latent_dim=16)
        model.latent_monitor = LatentBasisMonitor(expected_rank_ratio=0.01)

        torch.manual_seed(0)
        x = torch.randn(5, 32)
        model.encode(x)

        assert model.latent_monitor.has_samples
        health = model.get_latent_health()
        assert health is not None
        assert "effective_rank" in health
