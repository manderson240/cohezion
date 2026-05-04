"""Tests for FLUME VAE evaluation framework."""

from __future__ import annotations

import numpy as np
import torch


class TestReconstructionMetric:
    """Test cosine similarity reconstruction metric."""

    def test_perfect_reconstruction(self):
        """cos_sim should be 1.0 for identical inputs."""
        from cohezion.flume.evaluate_vae import reconstruction_cosine_similarity

        x = np.random.randn(10, 768).astype(np.float32)
        score = reconstruction_cosine_similarity(x, x)
        assert abs(score - 1.0) < 1e-5

    def test_random_reconstruction_below_one(self):
        """cos_sim should be < 1.0 for non-identical vectors."""
        from cohezion.flume.evaluate_vae import reconstruction_cosine_similarity

        x = np.random.randn(10, 768).astype(np.float32)
        recon = np.random.randn(10, 768).astype(np.float32)
        score = reconstruction_cosine_similarity(x, recon)
        assert score < 0.99

    def test_returns_float(self):
        """Should return a single float, not array."""
        from cohezion.flume.evaluate_vae import reconstruction_cosine_similarity

        x = np.random.randn(5, 768).astype(np.float32)
        score = reconstruction_cosine_similarity(x, x)
        assert isinstance(score, float)


class TestParaphraseDiscrimination:
    """Test paraphrase precision@1 metric."""

    def test_perfect_discrimination(self):
        """P@1 should be 1.0 when paraphrase pairs are closest neighbors."""
        from cohezion.flume.evaluate_vae import paraphrase_precision_at_1

        # Create embeddings where pairs (0,1), (2,3), (4,5) are close
        embeddings = np.zeros((6, 10), dtype=np.float32)
        embeddings[0] = [1, 0, 0, 0, 0, 0, 0, 0, 0, 0]
        embeddings[1] = [0.99, 0.01, 0, 0, 0, 0, 0, 0, 0, 0]
        embeddings[2] = [0, 1, 0, 0, 0, 0, 0, 0, 0, 0]
        embeddings[3] = [0.01, 0.99, 0, 0, 0, 0, 0, 0, 0, 0]
        embeddings[4] = [0, 0, 1, 0, 0, 0, 0, 0, 0, 0]
        embeddings[5] = [0, 0.01, 0.99, 0, 0, 0, 0, 0, 0, 0]

        pairs = [(0, 1), (2, 3), (4, 5)]
        p1 = paraphrase_precision_at_1(embeddings, pairs)
        assert p1 == 1.0

    def test_returns_float_between_0_and_1(self):
        """P@1 should be in [0, 1]."""
        from cohezion.flume.evaluate_vae import paraphrase_precision_at_1

        embeddings = np.random.randn(20, 10).astype(np.float32)
        pairs = [(0, 1), (2, 3), (4, 5)]
        p1 = paraphrase_precision_at_1(embeddings, pairs)
        assert 0.0 <= p1 <= 1.0


class TestKLHealthCheck:
    """Test KL collapse detection."""

    def test_healthy_kl(self):
        """Should report healthy when KL > threshold and active units high."""
        from cohezion.flume.evaluate_vae import kl_health_check

        result = kl_health_check(
            kl_value=0.5,
            active_units=200,
            total_units=256,
            kl_threshold=0.1,
            active_threshold=128,
        )
        assert result["healthy"] is True

    def test_kl_collapsed(self):
        """Should report unhealthy when KL < threshold."""
        from cohezion.flume.evaluate_vae import kl_health_check

        result = kl_health_check(
            kl_value=0.01,
            active_units=200,
            total_units=256,
            kl_threshold=0.1,
            active_threshold=128,
        )
        assert result["healthy"] is False
        assert "kl" in result["reason"].lower()

    def test_too_few_active_units(self):
        """Should report unhealthy when active units below threshold."""
        from cohezion.flume.evaluate_vae import kl_health_check

        result = kl_health_check(
            kl_value=0.5,
            active_units=50,
            total_units=256,
            kl_threshold=0.1,
            active_threshold=128,
        )
        assert result["healthy"] is False
        assert "active" in result["reason"].lower()


class TestSimilarityPreservation:
    """Test Spearman correlation between original and latent similarities."""

    def test_perfect_preservation(self):
        """Spearman ρ should be 1.0 when rank order is preserved."""
        from cohezion.flume.evaluate_vae import similarity_preservation_spearman

        # Original and latent are the same → perfect rank correlation
        embeddings = np.random.randn(20, 768).astype(np.float32)
        rho = similarity_preservation_spearman(embeddings, embeddings)
        assert abs(rho - 1.0) < 1e-3

    def test_returns_float(self):
        """Should return a single float."""
        from cohezion.flume.evaluate_vae import similarity_preservation_spearman

        orig = np.random.randn(10, 768).astype(np.float32)
        latent = np.random.randn(10, 256).astype(np.float32)
        rho = similarity_preservation_spearman(orig, latent)
        assert isinstance(rho, float)
        assert -1.0 <= rho <= 1.0


class TestVAEEvaluator:
    """Test the full evaluation suite."""

    def test_evaluate_returns_all_metrics(self):
        """Evaluator should return all red-flag metrics."""
        from cohezion.flume.evaluate_vae import VAEEvaluator
        from cohezion.flume.vae import FlumeVAE

        torch.manual_seed(42)
        from cohezion.flume.vae import FlumeVAEConfig

        config = FlumeVAEConfig(z_dim=256, embed_dim=256)
        model = FlumeVAE(config=config)

        # Small synthetic discrete token data (FlumeVAE expects integer token IDs)
        data = torch.randint(0, 1000, (50, 32))  # 50 sequences, 32 tokens each
        pairs = [(0, 1), (2, 3), (4, 5)]

        evaluator = VAEEvaluator(model)
        results = evaluator.evaluate(data, pairs)

        assert "reconstruction_cosine_sim" in results
        assert "kl_health" in results
        assert "active_units" in results
        assert "paraphrase_p_at_1" in results
        assert "similarity_spearman" in results
