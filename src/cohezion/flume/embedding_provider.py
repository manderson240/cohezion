# deferred imports for circular-dep workarounds
"""Embedding providers for FLUME VAE input.

Three providers with fallback chain:
  1. OllamaEmbeddingProvider — 768D via nomic-embed-text (best quality)
  2. HashFallbackProvider — 256D via SHA-256 (always available, no semantics)
  3. CachedEmbeddingProvider — LRU cache wrapper around any provider
"""

from __future__ import annotations

import hashlib
import logging
from collections import OrderedDict
from typing import Protocol

import numpy as np
import requests


logger = logging.getLogger(__name__)


class EmbeddingProvider(Protocol):
    """Protocol for embedding providers."""

    @property
    def embedding_dim(self) -> int: ...

    def embed(self, text: str) -> np.ndarray: ...

    def embed_batch(self, texts: list[str]) -> np.ndarray: ...


class OllamaEmbeddingProvider:
    """Embed text via Ollama nomic-embed-text (768D)."""

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def embedding_dim(self) -> int:
        return 768

    def embed(self, text: str) -> np.ndarray:
        """Embed single text to 768D normalized vector."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": text},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            vec = np.array(data["embeddings"][0], dtype=np.float32)
            norm = np.linalg.norm(vec)
            if norm > 0:
                vec /= norm
            return vec
        except Exception as e:
            raise ConnectionError(f"Ollama embedding failed: {e}") from e

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed batch of texts. Falls back to one-at-a-time on timeout."""
        try:
            resp = requests.post(
                f"{self.base_url}/api/embed",
                json={"model": self.model, "input": texts},
                timeout=self.timeout,
            )
            resp.raise_for_status()
            data = resp.json()
            vecs = np.array(data["embeddings"], dtype=np.float32)
            norms = np.linalg.norm(vecs, axis=1, keepdims=True)
            norms = np.where(norms > 0, norms, 1.0)
            return vecs / norms
        except Exception:
            # Batch too large or timeout — fall back to one-at-a-time
            logger.info("Batch embed failed, falling back to sequential (%d texts)", len(texts))
            return np.stack([self.embed(t) for t in texts])


class HashFallbackProvider:
    """Deterministic SHA-256 hash embedding (256D). No semantic meaning."""

    @property
    def embedding_dim(self) -> int:
        return 256

    def embed(self, text: str) -> np.ndarray:
        """Embed text to 256D via SHA-256 hash expansion."""
        hash_bytes = hashlib.sha256(text.encode()).digest()
        vec = np.zeros(256, dtype=np.float32)
        for i in range(256):
            vec[i] = hash_bytes[i % len(hash_bytes)] / 255.0
        norm = np.linalg.norm(vec)
        if norm > 0:
            vec /= norm
        return vec

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed batch of texts. Returns (N, 256) array."""
        return np.stack([self.embed(t) for t in texts])


class CachedEmbeddingProvider:
    """LRU cache wrapper around any EmbeddingProvider."""

    def __init__(self, inner: EmbeddingProvider, max_size: int = 10_000) -> None:
        self._inner = inner
        self._max_size = max_size
        self._cache: OrderedDict[str, np.ndarray] = OrderedDict()

    @property
    def embedding_dim(self) -> int:
        return self._inner.embedding_dim

    def embed(self, text: str) -> np.ndarray:
        if text in self._cache:
            self._cache.move_to_end(text)
            return self._cache[text]
        result = self._inner.embed(text)
        self._cache[text] = result
        if len(self._cache) > self._max_size:
            self._cache.popitem(last=False)
        return result

    def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Batch embed with cache: only call inner.embed_batch for cache misses."""
        results: list[np.ndarray | None] = [None] * len(texts)
        uncached_indices: list[int] = []
        uncached_texts: list[str] = []

        for i, text in enumerate(texts):
            if text in self._cache:
                self._cache.move_to_end(text)
                results[i] = self._cache[text]
            else:
                uncached_indices.append(i)
                uncached_texts.append(text)

        if uncached_texts:
            batch_result = self._inner.embed_batch(uncached_texts)
            for j, idx in enumerate(uncached_indices):
                vec = batch_result[j]
                self._cache[texts[idx]] = vec
                results[idx] = vec
                if len(self._cache) > self._max_size:
                    self._cache.popitem(last=False)

        return np.stack(results)  # type: ignore[arg-type]


def create_embedding_provider(
    *,
    use_cache: bool = True,
    cache_size: int = 10_000,
    require_ollama: bool = False,
) -> EmbeddingProvider:
    """Create the best available embedding provider.

    Tries Ollama first, falls back to hash if unavailable.
    """
    provider: EmbeddingProvider
    if require_ollama:
        provider = OllamaEmbeddingProvider()
    else:
        try:
            ollama = OllamaEmbeddingProvider()
            # Quick probe to check availability
            ollama.embed("test")
            provider = ollama
            logger.info("Using Ollama nomic-embed-text (768D)")
        except Exception:
            provider = HashFallbackProvider()
            logger.info("Ollama unavailable, using hash fallback (256D)")

    if use_cache:
        provider = CachedEmbeddingProvider(provider, max_size=cache_size)

    return provider


import httpx


class AsyncOllamaEmbeddingProvider:
    """Async-enabled Ollama embedding provider using httpx.

    Use this in async contexts to avoid blocking I/O.
    Sync code should continue using OllamaEmbeddingProvider.
    """

    def __init__(
        self,
        model: str = "nomic-embed-text",
        base_url: str = "http://localhost:11434",
        timeout: float = 300.0,
    ) -> None:
        self.model = model
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    @property
    def embedding_dim(self) -> int:
        return 768

    async def embed(self, text: str) -> np.ndarray:
        """Embed single text to 768D normalized vector (async)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": text},
                )
                resp.raise_for_status()
                data = resp.json()
                vec = np.array(data["embeddings"][0], dtype=np.float32)
                norm = np.linalg.norm(vec)
                if norm > 0:
                    vec /= norm
                return vec
        except Exception as e:
            raise ConnectionError(f"Ollama embedding failed: {e}") from e

    async def embed_batch(self, texts: list[str]) -> np.ndarray:
        """Embed batch of texts. Falls back to one-at-a-time on timeout (async)."""
        try:
            async with httpx.AsyncClient(timeout=self.timeout) as client:
                resp = await client.post(
                    f"{self.base_url}/api/embed",
                    json={"model": self.model, "input": texts},
                )
                resp.raise_for_status()
                data = resp.json()
                vecs = np.array(data["embeddings"], dtype=np.float32)
                norms = np.linalg.norm(vecs, axis=1, keepdims=True)
                norms = np.where(norms > 0, norms, 1.0)
                return vecs / norms
        except Exception:
            # Batch too large or timeout — fall back to one-at-a-time
            logger.info("Batch embed failed, falling back to sequential (%d texts)", len(texts))
            return np.stack([await self.embed(t) for t in texts])
