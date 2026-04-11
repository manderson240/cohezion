"""Tests for FLUME EmbeddingProvider — Ollama + hash fallback + LRU cache."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import numpy as np
import pytest


class TestOllamaEmbeddingProvider:
    """Test Ollama-backed embedding provider."""

    def test_embed_returns_768d_vector(self):
        """Ollama provider should return 768-dimensional embedding."""
        from cohezion.flume.embedding_provider import OllamaEmbeddingProvider

        fake_response = {"embeddings": [list(np.random.randn(768))]}
        with patch("cohezion.flume.embedding_provider.requests") as mock_req:
            mock_req.post.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=fake_response)
            )
            provider = OllamaEmbeddingProvider()
            result = provider.embed("deploy the API")

        assert isinstance(result, np.ndarray)
        assert result.shape == (768,)
        assert result.dtype == np.float32

    def test_embed_is_normalized(self):
        """Output should be L2-normalized."""
        from cohezion.flume.embedding_provider import OllamaEmbeddingProvider

        raw = np.random.randn(768).tolist()
        fake_response = {"embeddings": [raw]}
        with patch("cohezion.flume.embedding_provider.requests") as mock_req:
            mock_req.post.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=fake_response)
            )
            provider = OllamaEmbeddingProvider()
            result = provider.embed("test text")

        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-5, f"Expected unit norm, got {norm}"

    def test_embed_batch_returns_correct_shapes(self):
        """Batch embedding should return N x 768 array."""
        from cohezion.flume.embedding_provider import OllamaEmbeddingProvider

        texts = ["deploy API", "run tests", "check logs"]
        fake_response = {"embeddings": [list(np.random.randn(768)) for _ in texts]}
        with patch("cohezion.flume.embedding_provider.requests") as mock_req:
            mock_req.post.return_value = MagicMock(
                status_code=200, json=MagicMock(return_value=fake_response)
            )
            provider = OllamaEmbeddingProvider()
            result = provider.embed_batch(texts)

        assert isinstance(result, np.ndarray)
        assert result.shape == (3, 768)

    def test_raises_on_ollama_failure(self):
        """Should raise ConnectionError when Ollama is unreachable."""
        from cohezion.flume.embedding_provider import OllamaEmbeddingProvider

        with patch("cohezion.flume.embedding_provider.requests") as mock_req:
            mock_req.post.side_effect = Exception("Connection refused")
            provider = OllamaEmbeddingProvider()
            with pytest.raises(ConnectionError):
                provider.embed("test")


class TestHashFallbackProvider:
    """Test deterministic hash-based fallback provider."""

    def test_embed_returns_256d_vector(self):
        """Hash fallback should return 256-dimensional embedding."""
        from cohezion.flume.embedding_provider import HashFallbackProvider

        provider = HashFallbackProvider()
        result = provider.embed("deploy the API")

        assert isinstance(result, np.ndarray)
        assert result.shape == (256,)
        assert result.dtype == np.float32

    def test_embed_is_deterministic(self):
        """Same input should produce same output."""
        from cohezion.flume.embedding_provider import HashFallbackProvider

        provider = HashFallbackProvider()
        a = provider.embed("deploy the API")
        b = provider.embed("deploy the API")
        np.testing.assert_array_equal(a, b)

    def test_different_texts_produce_different_embeddings(self):
        """Different inputs should produce different outputs."""
        from cohezion.flume.embedding_provider import HashFallbackProvider

        provider = HashFallbackProvider()
        a = provider.embed("deploy the API")
        b = provider.embed("run the tests")
        assert not np.array_equal(a, b)

    def test_embed_is_normalized(self):
        """Hash fallback output should be L2-normalized."""
        from cohezion.flume.embedding_provider import HashFallbackProvider

        provider = HashFallbackProvider()
        result = provider.embed("test")
        norm = np.linalg.norm(result)
        assert abs(norm - 1.0) < 1e-5


class TestCachedEmbeddingProvider:
    """Test LRU-cached embedding provider wrapper."""

    def test_cache_hit_avoids_second_call(self):
        """Cached provider should not call underlying provider twice for same text."""
        from cohezion.flume.embedding_provider import CachedEmbeddingProvider

        mock_inner = MagicMock()
        mock_inner.embed.return_value = np.random.randn(768).astype(np.float32)
        mock_inner.embedding_dim = 768

        provider = CachedEmbeddingProvider(mock_inner, max_size=100)
        _ = provider.embed("deploy API")
        _ = provider.embed("deploy API")

        assert mock_inner.embed.call_count == 1

    def test_cache_miss_calls_underlying(self):
        """Different texts should each call the underlying provider."""
        from cohezion.flume.embedding_provider import CachedEmbeddingProvider

        mock_inner = MagicMock()
        mock_inner.embed.return_value = np.random.randn(768).astype(np.float32)
        mock_inner.embedding_dim = 768

        provider = CachedEmbeddingProvider(mock_inner, max_size=100)
        _ = provider.embed("deploy API")
        _ = provider.embed("run tests")

        assert mock_inner.embed.call_count == 2

    def test_lru_eviction(self):
        """Cache should evict oldest when max_size reached."""
        from cohezion.flume.embedding_provider import CachedEmbeddingProvider

        mock_inner = MagicMock()
        mock_inner.embed.return_value = np.random.randn(768).astype(np.float32)
        mock_inner.embedding_dim = 768

        provider = CachedEmbeddingProvider(mock_inner, max_size=2)
        _ = provider.embed("a")
        _ = provider.embed("b")
        _ = provider.embed("c")  # evicts "a"
        _ = provider.embed("a")  # should re-call

        assert mock_inner.embed.call_count == 4

    def test_embedding_dim_passthrough(self):
        """Cached provider should expose inner provider's embedding_dim."""
        from cohezion.flume.embedding_provider import CachedEmbeddingProvider

        mock_inner = MagicMock()
        mock_inner.embedding_dim = 768

        provider = CachedEmbeddingProvider(mock_inner, max_size=100)
        assert provider.embedding_dim == 768


class TestEmbeddingProviderFactory:
    """Test the factory function that creates the best available provider."""

    def test_creates_provider_with_fallback(self):
        """Factory should return a provider (Ollama or hash fallback)."""
        from cohezion.flume.embedding_provider import create_embedding_provider

        provider = create_embedding_provider(use_cache=False, require_ollama=False)
        assert hasattr(provider, "embed")
        assert hasattr(provider, "embedding_dim")

    def test_cached_provider_wraps_inner(self):
        """Factory with use_cache=True should return CachedEmbeddingProvider."""
        from cohezion.flume.embedding_provider import (
            CachedEmbeddingProvider,
            create_embedding_provider,
        )

        provider = create_embedding_provider(use_cache=True, require_ollama=False)
        assert isinstance(provider, CachedEmbeddingProvider)
