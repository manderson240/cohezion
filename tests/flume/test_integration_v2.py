"""Integration tests for FLUME VAE v2 with vae_encoder and journey_tracker."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock

import numpy as np
import torch


class TestVAEEncoderV2Integration:
    """Test vae_encoder.py with new VAE model."""

    def test_canonical_encoder_produces_256d_output(self):
        """The facade yields a unit 256-d vector (no checkpoint/model_path argument any more)."""
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        result = FlumeVAEEncoder().encode("deploy the API")
        assert result.shape == (256,)
        assert abs(np.linalg.norm(result) - 1.0) < 1e-4

    def test_public_interface(self):
        from cohezion.flume.vae_encoder import FlumeVAEEncoder

        encoder = FlumeVAEEncoder()
        assert encoder.EMBEDDING_DIM == 256
        assert encoder.encode("test").shape == (256,)


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

        # Mock FLUME encoder with deterministic category vectors for reliable assertions
        def mock_encode(text: str) -> np.ndarray:
            if "deploy" in text.lower() or "deployment" in text.lower():
                v = np.zeros(256, dtype=np.float32)
                v[:128] = 1.0
            elif "test" in text.lower():
                v = np.zeros(256, dtype=np.float32)
                v[128:] = 1.0
            else:
                v = np.zeros(256, dtype=np.float32)
                v[64:192] = 1.0
            return v / np.linalg.norm(v)

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
