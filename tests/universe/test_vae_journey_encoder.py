"""Tests for VAE Journey Encoder."""

import numpy as np

from cohezion.universe.engine import AxiomaticState, TrajectoryPoint
from cohezion.universe.vae_journey_encoder import VAEJourneyEncoder


class TestVAEJourneyEncoder:
    """Test VAE Journey Encoder."""

    def test_encoder_initialization(self):
        """Should initialize encoder with fallback enabled."""
        encoder = VAEJourneyEncoder()
        assert encoder is not None
        # Should have VAE encoder (may fall back to hash)
        assert hasattr(encoder, "vae_encoder")

    def test_encode_trajectory_returns_256d_vector(self):
        """Should encode trajectory to 256D vector."""
        encoder = VAEJourneyEncoder()

        # Create simple trajectory
        trajectory = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(),
                latent=None,  # type: ignore[arg-type]
                coherence=0.5,
                action_taken="init",
            ),
            TrajectoryPoint(
                step_number=1,
                timestamp=1.0,
                axiomatic=AxiomaticState(spatial_x=0.1),
                latent=None,  # type: ignore[arg-type]
                coherence=0.52,
                action_taken="move",
            ),
        ]

        embedding = encoder.encode_trajectory(trajectory)
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (256,)
        assert embedding.dtype == np.float64 or embedding.dtype == np.float32

    def test_encode_empty_trajectory(self):
        """Should handle empty trajectory gracefully."""
        encoder = VAEJourneyEncoder()
        embedding = encoder.encode_trajectory([])
        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (256,)

    def test_deterministic_encoding(self):
        """Same trajectory should produce same embedding."""
        encoder = VAEJourneyEncoder()

        trajectory = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(spatial_x=0.5, spatial_y=0.3),
                latent=None,  # type: ignore[arg-type]
                coherence=0.6,
                action_taken="step-0",
            )
        ]

        embedding1 = encoder.encode_trajectory(trajectory)
        embedding2 = encoder.encode_trajectory(trajectory)

        np.testing.assert_array_equal(embedding1, embedding2)

    def test_different_trajectories_different_embeddings(self):
        """Different trajectories should produce different embeddings."""
        encoder = VAEJourneyEncoder()

        traj1 = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(spatial_x=0.0),
                latent=None,  # type: ignore[arg-type]
                coherence=0.5,
                action_taken="a",
            )
        ]

        traj2 = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(spatial_x=1.0),
                latent=None,  # type: ignore[arg-type]
                coherence=0.5,
                action_taken="b",
            )
        ]

        emb1 = encoder.encode_trajectory(traj1)
        emb2 = encoder.encode_trajectory(traj2)

        # Should be different (not exactly equal)
        assert not np.array_equal(emb1, emb2)

    def test_text_serialization(self):
        """Should serialize trajectory to structured text."""
        encoder = VAEJourneyEncoder()

        trajectory = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(spatial_x=0.5, physics=0.6),
                latent=None,  # type: ignore[arg-type]
                coherence=0.55,
                action_taken="init",
            ),
            TrajectoryPoint(
                step_number=1,
                timestamp=1.0,
                axiomatic=AxiomaticState(spatial_x=0.6, physics=0.5),
                latent=None,  # type: ignore[arg-type]
                coherence=0.50,
                action_taken="adjust",
            ),
        ]

        text = encoder._serialize_trajectory(trajectory)
        # Should contain step numbers, coherence, action
        assert "step:0" in text
        assert "step:1" in text
        assert "coherence:0.55" in text
        assert "coherence:0.50" in text or "coherence:0.5" in text
        assert "action:init" in text
        assert "action:adjust" in text

    def test_fallback_to_hash_encoding(self):
        """Should fall back to hash encoding if VAE unavailable."""
        # Even without VAE checkpoint, should produce valid embeddings
        encoder = VAEJourneyEncoder()

        trajectory = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(),
                latent=None,  # type: ignore[arg-type]
                coherence=0.5,
                action_taken="test",
            )
        ]

        embedding = encoder.encode_trajectory(trajectory)
        # Should get hash-based encoding (still 256D)
        assert embedding.shape == (256,)
        # Hash encoding is deterministic
        embedding2 = encoder.encode_trajectory(trajectory)
        np.testing.assert_array_equal(embedding, embedding2)

    def test_normalized_embeddings(self):
        """Embeddings should be normalized (unit length)."""
        encoder = VAEJourneyEncoder()

        trajectory = [
            TrajectoryPoint(
                step_number=0,
                timestamp=0.0,
                axiomatic=AxiomaticState(),
                latent=None,  # type: ignore[arg-type]
                coherence=0.5,
                action_taken="test",
            )
        ]

        embedding = encoder.encode_trajectory(trajectory)
        norm = np.linalg.norm(embedding)
        # Should be approximately unit length (normalized)
        np.testing.assert_allclose(norm, 1.0, rtol=1e-5)
