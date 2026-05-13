"""Tests for semantic encoder using sentence-transformers."""

from unittest.mock import MagicMock, patch

import numpy as np
import pytest

from cohezion.cache.sentence_encoder import (
    SentenceTransformerEncoder,
    get_encoder,
)


class TestSentenceTransformerEncoder:
    """Test semantic encoder with sentence-transformers."""

    @pytest.fixture(autouse=True)
    def reset_singleton(self):
        """Reset singleton before each test."""
        SentenceTransformerEncoder.reset_instance()
        yield
        SentenceTransformerEncoder.reset_instance()

    def test_encode_with_mocked_model(self):
        """Happy path: Encode text with mocked model."""
        mock_model = MagicMock()
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_model.encode.return_value = mock_embedding

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            result = encoder.encode("test text")

            assert result.shape == (384,)
            assert result.dtype == np.float32
            mock_model.encode.assert_called_once()

    def test_encode_empty_string(self):
        """Edge-empty: Empty string returns zero vector."""
        mock_model = MagicMock()

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            result = encoder.encode("")

            assert result.shape == (384,)
            assert np.all(result == 0)
            mock_model.encode.assert_not_called()

    def test_encode_without_model(self):
        """Error-case: Encoding without loaded model returns zero vector."""
        with patch("sentence_transformers.SentenceTransformer", side_effect=ImportError):
            encoder = SentenceTransformerEncoder()
            assert encoder.model is None

            result = encoder.encode("test")
            assert result.shape == (384,)
            assert np.all(result == 0)

    def test_encode_batch(self):
        """Edge-max: Batch encoding multiple texts."""
        mock_model = MagicMock()
        mock_embeddings = np.random.rand(3, 384).astype(np.float32)
        mock_model.encode.return_value = mock_embeddings

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            texts = ["text1", "text2", "text3"]
            result = encoder.encode_batch(texts)

            assert result.shape == (3, 384)
            assert result.dtype == np.float32
            mock_model.encode.assert_called_once()
            call_args = mock_model.encode.call_args
            assert call_args[0][0] == texts
            assert call_args[1]["show_progress_bar"] is False

    def test_encode_batch_empty_list(self):
        """Edge-empty: Empty batch returns zero array."""
        mock_model = MagicMock()

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            result = encoder.encode_batch([])

            assert result.shape == (0, 384)
            assert result.dtype == np.float32

    def test_similarity_identical_vectors(self):
        """Integration: Similarity of identical vectors is 1.0."""
        encoder = SentenceTransformerEncoder()
        emb = np.random.rand(384).astype(np.float32)

        similarity = encoder.similarity(emb, emb)
        assert 0.99 <= similarity <= 1.0  # Allow for floating point errors

    def test_similarity_orthogonal_vectors(self):
        """Integration: Similarity of orthogonal vectors is ~0.0."""
        encoder = SentenceTransformerEncoder()
        emb1 = np.zeros(384, dtype=np.float32)
        emb1[:192] = 1.0
        emb2 = np.zeros(384, dtype=np.float32)
        emb2[192:] = 1.0

        similarity = encoder.similarity(emb1, emb2)
        assert similarity == 0.0

    def test_similarity_zero_vectors(self):
        """Edge-empty: Similarity with zero vectors returns 0.0."""
        encoder = SentenceTransformerEncoder()
        emb1 = np.zeros(384, dtype=np.float32)
        emb2 = np.zeros(384, dtype=np.float32)

        similarity = encoder.similarity(emb1, emb2)
        assert similarity == 0.0

    def test_similarity_none_vectors(self):
        """Error-case: Similarity with None vectors returns 0.0."""
        encoder = SentenceTransformerEncoder()

        similarity = encoder.similarity(None, None)
        assert similarity == 0.0

        emb = np.random.rand(384)
        similarity = encoder.similarity(emb, None)
        assert similarity == 0.0

    def test_get_instance_singleton(self):
        """Integration: get_instance returns same instance."""
        instance1 = SentenceTransformerEncoder.get_instance()
        instance2 = SentenceTransformerEncoder.get_instance()

        assert instance1 is instance2

    def test_get_encoder_function(self):
        """Integration: get_encoder() returns singleton."""
        encoder1 = get_encoder()
        encoder2 = get_encoder()

        assert encoder1 is encoder2
        assert isinstance(encoder1, SentenceTransformerEncoder)

    def test_reset_instance(self):
        """Integration: reset_instance clears singleton."""
        instance1 = SentenceTransformerEncoder.get_instance()
        SentenceTransformerEncoder.reset_instance()
        instance2 = SentenceTransformerEncoder.get_instance()

        assert instance1 is not instance2

    def test_get_embedding_dim(self):
        """Integration: get_embedding_dim returns 384."""
        mock_model = MagicMock()

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            dim = encoder.get_embedding_dim()

            assert dim == 384

    def test_get_embedding_dim_no_model(self):
        """Error-case: get_embedding_dim returns 0 when model unavailable."""
        with patch("sentence_transformers.SentenceTransformer", side_effect=ImportError):
            encoder = SentenceTransformerEncoder()
            dim = encoder.get_embedding_dim()

            assert dim == 0

    def test_repr_with_model(self):
        """Integration: __repr__ shows ready status when model loaded."""
        mock_model = MagicMock()

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            repr_str = repr(encoder)

            assert "all-MiniLM-L6-v2" in repr_str
            assert "✅ Ready" in repr_str
            assert "384D" in repr_str

    def test_repr_without_model(self):
        """Error-case: __repr__ shows unavailable status when model fails."""
        with patch("sentence_transformers.SentenceTransformer", side_effect=ImportError):
            encoder = SentenceTransformerEncoder()
            repr_str = repr(encoder)

            assert "all-MiniLM-L6-v2" in repr_str
            assert "❌ Unavailable" in repr_str

    def test_encode_with_normalization(self):
        """Integration: Normalized encoding returns unit vectors."""
        mock_model = MagicMock()
        # Return a non-normalized vector that will be normalized by the mock
        mock_embedding = np.random.rand(384).astype(np.float32)
        mock_embedding = mock_embedding / np.linalg.norm(mock_embedding)
        mock_model.encode.return_value = mock_embedding

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            encoder.encode("test", normalize=True)

            # Check that normalize_embeddings=True was passed
            call_kwargs = mock_model.encode.call_args[1]
            assert call_kwargs["normalize_embeddings"] is True

    def test_encode_exception_handling(self):
        """Error-case: Encoding exception returns zero vector."""
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("Encoding failed")

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            result = encoder.encode("test")

            assert result.shape == (384,)
            assert np.all(result == 0)

    def test_encode_batch_exception_handling(self):
        """Error-case: Batch encoding exception returns zero array."""
        mock_model = MagicMock()
        mock_model.encode.side_effect = RuntimeError("Batch encoding failed")

        with patch("sentence_transformers.SentenceTransformer") as MockST:
            MockST.return_value = mock_model

            encoder = SentenceTransformerEncoder()
            result = encoder.encode_batch(["text1", "text2"])

            assert result.shape == (2, 384)
            assert np.all(result == 0)
