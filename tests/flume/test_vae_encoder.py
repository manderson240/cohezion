"""Tests for FLUME VAE encoder."""

import numpy as np
import pytest

from cohezion.flume.vae_encoder import FlumeVAEEncoder, get_encoder, reset_encoder


class TestVAEEncoderBasics:
    """Test basic VAE encoder functionality."""

    def test_encoder_initialization(self):
        """Test encoder initialization."""
        encoder = FlumeVAEEncoder(fallback_to_hash=True)
        assert encoder is not None
        assert encoder.EMBEDDING_DIM == 256

    def test_encode_produces_256d_embedding(self):
        """Test that encode produces 256D embeddings."""
        encoder = FlumeVAEEncoder()
        embedding = encoder.encode("test prompt")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (256,)
        assert embedding.dtype == np.float32

    def test_embeddings_normalized(self):
        """Test that embeddings are normalized to unit length."""
        encoder = FlumeVAEEncoder()
        embedding = encoder.encode("test prompt")

        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-5)

    def test_deterministic_encoding(self):
        """Test that encoding is deterministic."""
        encoder = FlumeVAEEncoder()

        embedding1 = encoder.encode("same prompt")
        embedding2 = encoder.encode("same prompt")

        np.testing.assert_array_almost_equal(embedding1, embedding2)

    def test_different_texts_different_embeddings(self):
        """Test that different texts produce different embeddings."""
        encoder = FlumeVAEEncoder()

        embedding1 = encoder.encode("prompt one")
        embedding2 = encoder.encode("prompt two")

        assert not np.allclose(embedding1, embedding2)

    def test_similar_texts_similar_embeddings(self):
        """Test that similar texts produce similar embeddings."""
        encoder = FlumeVAEEncoder()

        embedding1 = encoder.encode("The quick brown fox")
        embedding2 = encoder.encode("The quick brown foxes")

        similarity = np.dot(embedding1, embedding2)
        assert similarity > 0.7  # Should be reasonably similar


class TestVAEEncoderFallback:
    """Test fallback behavior."""

    def test_fallback_to_hash_enabled(self):
        """Test fallback to hash when encoder unavailable."""
        encoder = FlumeVAEEncoder(
            model_path=None,  # Non-existent path
            fallback_to_hash=True,
        )

        # Should use hash fallback without error
        embedding = encoder.encode("test prompt")
        assert embedding.shape == (256,)

    def test_fallback_hash_produces_valid_embedding(self):
        """Test that hash fallback produces valid embeddings."""
        encoder = FlumeVAEEncoder(
            model_path=None,
            fallback_to_hash=True,
        )

        embedding = encoder.encode("test")
        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-5)


class TestVAEEncoderSingleton:
    """Test singleton pattern."""

    def test_get_encoder_returns_same_instance(self):
        """Test that get_encoder returns the same instance."""
        reset_encoder()

        encoder1 = get_encoder()
        encoder2 = get_encoder()

        assert encoder1 is encoder2

    def test_reset_encoder_clears_instance(self):
        """Test that reset_encoder creates new instance."""
        encoder1 = get_encoder()
        reset_encoder()
        encoder2 = get_encoder()

        assert encoder1 is not encoder2


class TestVAEEncoderCosineSimilarity:
    """Test cosine similarity between embeddings."""

    def test_cosine_similarity_formula(self):
        """Test cosine similarity calculation."""
        encoder = FlumeVAEEncoder()

        text1 = "machine learning models"
        text2 = "deep learning neural networks"

        emb1 = encoder.encode(text1)
        emb2 = encoder.encode(text2)

        similarity = np.dot(emb1, emb2)

        # Embeddings are normalized, so dot product IS cosine similarity
        assert 0.0 <= similarity <= 1.0

    def test_identical_text_cosine_similarity_one(self):
        """Test that identical texts have cosine similarity of 1.0."""
        encoder = FlumeVAEEncoder()

        text = "same text"

        emb1 = encoder.encode(text)
        emb2 = encoder.encode(text)

        similarity = np.dot(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)


class TestVAEEncoderPerformance:
    """Test encoding performance."""

    def test_encoding_is_fast(self):
        """Test that encoding completes quickly."""
        import time

        encoder = FlumeVAEEncoder()

        start = time.time()
        for _ in range(100):
            encoder.encode("test prompt")
        elapsed = time.time() - start

        # 100 encodings should be fast (< 1 second even with hash fallback)
        assert elapsed < 1.0

    def test_encoder_available_flag(self):
        """Test is_available() flag."""
        encoder = FlumeVAEEncoder()
        # Should be available if torch is installed
        available = encoder.is_available()
        assert isinstance(available, bool)
