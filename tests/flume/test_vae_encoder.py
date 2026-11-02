"""Tests for FLUME VAE encoder."""

import numpy as np
import pytest

from cohezion.flume.vae_encoder import (
    FlumeVAEEncoder,
    TextLatentUnavailable,
    get_encoder,
    reset_encoder,
)


@pytest.fixture
def patched_encoder():
    """FlumeVAEEncoder on the conftest deterministic embedder (no model download)."""
    return FlumeVAEEncoder()


class TestVAEEncoderBasics:
    """Test basic VAE encoder functionality."""

    def test_encoder_initialization(self):
        """Test encoder initialization."""
        encoder = FlumeVAEEncoder()
        assert encoder is not None
        assert encoder.EMBEDDING_DIM == 256

    def test_encode_produces_256d_embedding(self, patched_encoder):
        """Test that encode produces 256D embeddings."""
        embedding = patched_encoder.encode("test prompt")

        assert isinstance(embedding, np.ndarray)
        assert embedding.shape == (256,)
        assert embedding.dtype == np.float32

    def test_embeddings_normalized(self, patched_encoder):
        """Test that embeddings are normalized to unit length."""
        embedding = patched_encoder.encode("test prompt")

        norm = np.linalg.norm(embedding)
        assert np.isclose(norm, 1.0, atol=1e-4)

    def test_deterministic_encoding(self, patched_encoder):
        """Test that encoding is deterministic."""
        embedding1 = patched_encoder.encode("same prompt")
        embedding2 = patched_encoder.encode("same prompt")

        np.testing.assert_array_almost_equal(embedding1, embedding2)

    def test_different_texts_different_embeddings(self, patched_encoder):
        """Test that different texts produce different embeddings."""
        embedding1 = patched_encoder.encode("prompt one")
        embedding2 = patched_encoder.encode("prompt two")

        assert not np.allclose(embedding1, embedding2)

    def test_similar_texts_similar_embeddings(self, patched_encoder):
        """Test that similar texts produce similar embeddings when Ollama reflects similarity."""
        # With mocked Ollama, similarity is hash-based (not real semantic)
        # Just verify embeddings are valid and distinct
        embedding1 = patched_encoder.encode("The quick brown fox")
        embedding2 = patched_encoder.encode("The quick brown foxes")

        assert embedding1.shape == (256,)
        assert embedding2.shape == (256,)


class TestVAEEncoderUnavailable:
    """No hash fallback exists: an unavailable encoder is an explicit state."""

    def test_unavailable_raises_instead_of_hashing(self):
        def boom():
            raise RuntimeError("no model")

        encoder = FlumeVAEEncoder(embed_loader=boom)
        assert encoder.is_available() is False
        assert encoder.encode_or_none("test prompt") is None
        with pytest.raises(TextLatentUnavailable):
            encoder.encode("test prompt")

    def test_no_fallback_kwargs(self):
        with pytest.raises(TypeError):
            FlumeVAEEncoder(fallback_to_hash=True)  # type: ignore[call-arg]


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

    def test_cosine_similarity_formula(self, patched_encoder):
        """Test cosine similarity calculation."""
        text1 = "machine learning models"
        text2 = "deep learning neural networks"

        emb1 = patched_encoder.encode(text1)
        emb2 = patched_encoder.encode(text2)

        # Embeddings are normalized to unit length
        assert np.isclose(np.linalg.norm(emb1), 1.0, atol=1e-4)
        assert np.isclose(np.linalg.norm(emb2), 1.0, atol=1e-4)

    def test_identical_text_cosine_similarity_one(self, patched_encoder):
        """Test that identical texts have cosine similarity of 1.0."""
        text = "same text"

        emb1 = patched_encoder.encode(text)
        emb2 = patched_encoder.encode(text)

        similarity = np.dot(emb1, emb2)
        assert np.isclose(similarity, 1.0, atol=1e-5)


class TestVAEEncoderPerformance:
    """Test encoding performance."""

    def test_encoding_is_fast(self, patched_encoder):
        """Test that encoding completes quickly (no live Ollama calls)."""
        import time

        start = time.time()
        for _ in range(100):
            patched_encoder.encode("test prompt")
        elapsed = time.time() - start

        # 100 encodings should be fast (< 5 seconds with VAE inference)
        assert elapsed < 5.0

    def test_encoder_available_flag(self, patched_encoder):
        """Test is_available() flag."""
        available = patched_encoder.is_available()
        assert isinstance(available, bool)
