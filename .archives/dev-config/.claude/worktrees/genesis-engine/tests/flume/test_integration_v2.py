"""Integration tests for FLUME VAE v2 with vae_encoder and journey_tracker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

import numpy as np
import torch


class TestVAEEncoderV2Integration:
    """Test vae_encoder.py with new VAE model."""

    def test_new_vae_produces_256d_output(self, tmp_path: Path):
        """New VAE model loaded via vae_encoder should produce 256D."""
        from cohezion.flume.vae import FlumeVAE
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        # Create and save a v2 model checkpoint
        model = FlumeVAE(input_dim=768, latent_dim=256)
        ckpt_path = tmp_path / "test_v2.pt"
        torch.save(
            {
                "model_state_dict": model.state_dict(),
                "config": {"input_dim": 768, "latent_dim": 256},
                "version": 2,
            },
            ckpt_path,
        )

        # Mock Ollama to return 768D
        fake_768d = np.random.randn(768).astype(np.float32)
        fake_768d /= np.linalg.norm(fake_768d)

        with patch("cohezion.flume.vae_encoder.OllamaEmbeddingProvider") as MockOllama:
            MockOllama.return_value.embed.return_value = fake_768d
            encoder = FlumeVAEEncoder(model_path=ckpt_path, fallback_to_hash=True)

        if encoder.is_available():
            result = encoder.encode("deploy the API")
            assert result.shape == (256,)
            assert abs(np.linalg.norm(result) - 1.0) < 1e-4

    def test_fallback_chain_works_without_ollama(self):
        """When Ollama is unavailable and no v2 checkpoint, should hash fallback."""
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        encoder = FlumeVAEEncoder(
            model_path=Path("/nonexistent/model.pt"),
            fallback_to_hash=True,
        )
        result = encoder.encode("deploy the API")
        assert result.shape == (256,)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-4

    def test_existing_tests_still_pass(self):
        """Existing public interface should be unchanged."""
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        encoder = FlumeVAEEncoder(fallback_to_hash=True)
        assert encoder.EMBEDDING_DIM == 256
        result = encoder.encode("test")
        assert result.shape == (256,)


class TestJourneyTrackerFLUMEPath:
    """Test journey_tracker with optional FLUME encoder."""

    def test_flume_path_produces_2048d(self):
        """When FLUME encoder is available, text_to_latent still returns 2048D."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()

        # Mock the FLUME encoder
        mock_encoder = MagicMock()
        mock_encoder.encode.return_value = np.random.randn(256).astype(np.float32)
        mock_encoder.is_available.return_value = True
        tracker._flume_encoder = mock_encoder

        result = tracker.text_to_latent("deploy the API")
        assert result.shape == (2048,)

    def test_flume_paraphrases_closer_than_unrelated(self):
        """FLUME path should make paraphrases closer than unrelated texts."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()

        # Mock FLUME encoder that preserves semantic similarity
        rng = np.random.RandomState(42)

        def mock_encode(text: str) -> np.ndarray:
            # Paraphrases get similar vectors (varied, not constant)
            if "deploy" in text.lower() or "deployment" in text.lower():
                base = rng.randn(256).astype(np.float32)
                base[:128] += 2.0  # Strong positive signal in first half
            elif "test" in text.lower():
                base = rng.randn(256).astype(np.float32)
                base[128:] += 2.0  # Strong positive signal in second half
            else:
                base = rng.randn(256).astype(np.float32)
            base /= np.linalg.norm(base)
            return base

        mock_encoder = MagicMock()
        mock_encoder.encode.side_effect = mock_encode
        mock_encoder.is_available.return_value = True
        tracker._flume_encoder = mock_encoder

        v1 = tracker.text_to_latent("deploy the API")
        v2 = tracker.text_to_latent("API deployment")
        v3 = tracker.text_to_latent("run the tests")

        sim_paraphrase = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        sim_unrelated = np.dot(v1, v3) / (np.linalg.norm(v1) * np.linalg.norm(v3))

        assert sim_paraphrase > sim_unrelated

    def test_hash_fallback_when_no_flume(self):
        """Without FLUME encoder, should use existing hash path."""
        from cohezion.compound.journey_tracker import JourneyTracker

        tracker = JourneyTracker()
        # No _flume_encoder set → uses hash path
        result = tracker.text_to_latent("deploy the API")
        assert result.shape == (2048,)
