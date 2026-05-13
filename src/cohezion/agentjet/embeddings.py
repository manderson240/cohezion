"""Gemini Embedding 2 integration with local FLUME VAE fallback.

Models: GeminiEmbeddingModel (cloud + SurrealDB cache), FlumeVAEEmbeddingModel (local 256D).
EmbeddingDistiller: knowledge distillation stub (Phase 2).
EmbeddingOrchestrator: context-aware routing.
"""

from __future__ import annotations

import asyncio
import hashlib
import logging
import os
from dataclasses import dataclass
from enum import Enum, auto
from pathlib import Path
from typing import Protocol, runtime_checkable

import numpy as np


logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Data types
# ---------------------------------------------------------------------------


@dataclass
class EmbeddingResult:
    """Result of an embedding operation."""

    vector: np.ndarray  # The embedding vector
    model: str  # Which model produced it
    cached: bool = False  # Whether this came from cache
    dimension: int = 0  # Vector dimension (set from vector.shape[0])

    def __post_init__(self) -> None:
        self.dimension = len(self.vector)


class EmbeddingContext(Enum):
    """Routing context for embedding requests."""

    VAULT_INDEXING = auto()  # Offline, one-time — use Gemini cloud
    RUNTIME = auto()  # Online hot path — use local FLUME VAE
    TRAINING_REWARD = auto()  # Offline for distillation — use Gemini cloud
    FAST_ROUTING = auto()  # Hot path — use hash fallback


# ---------------------------------------------------------------------------
# Protocol
# ---------------------------------------------------------------------------


@runtime_checkable
class EmbeddingModel(Protocol):
    """Protocol for embedding models — sync and async encode."""

    async def encode(self, text: str) -> EmbeddingResult: ...
    def encode_sync(self, text: str) -> EmbeddingResult: ...


# ---------------------------------------------------------------------------
# FLUME VAE local model
# ---------------------------------------------------------------------------


class FlumeVAEEmbeddingModel:
    """Local FLUME VAE embedding (256D). Used for runtime inference."""

    DIMENSION = 256

    def __init__(self) -> None:
        self._encoder = None  # Lazy load

    def _get_encoder(self):  # type: ignore[return]
        if self._encoder is None:
            from cohezion.flume.vae_encoder import get_encoder

            self._encoder = get_encoder()
        return self._encoder

    async def encode(self, text: str) -> EmbeddingResult:
        """Encode text using FLUME VAE (runs in thread to avoid blocking loop)."""
        loop = asyncio.get_running_loop()
        vector = await loop.run_in_executor(None, self._encode_blocking, text)
        return EmbeddingResult(vector=vector, model="flume-vae-256d")

    def encode_sync(self, text: str) -> EmbeddingResult:
        """Synchronous encode using FLUME VAE."""
        vector = self._encode_blocking(text)
        return EmbeddingResult(vector=vector, model="flume-vae-256d")

    def _encode_blocking(self, text: str) -> np.ndarray:
        try:
            encoder = self._get_encoder()
            return encoder.encode(text)
        except Exception as exc:
            logger.warning("FLUME VAE encode failed, using hash fallback: %s", exc)
            return self._hash_encode(text)

    @staticmethod
    def _hash_encode(text: str) -> np.ndarray:
        """Deterministic 256D hash fallback."""
        h = hashlib.sha256(text.encode()).digest()
        embedding = np.array([h[i % len(h)] / 255.0 for i in range(256)], dtype=np.float32)
        norm = np.linalg.norm(embedding)
        if norm > 0:
            embedding /= norm
        return embedding


# ---------------------------------------------------------------------------
# Gemini cloud model
# ---------------------------------------------------------------------------


class GeminiEmbeddingModel:
    """Gemini Embedding 2 with content-hash SurrealDB cache and FLUME VAE fallback."""

    GEMINI_API_URL = "https://generativelanguage.googleapis.com/v1beta/models/text-embedding-004:embedContent"
    DIMENSION = 768  # Gemini Embedding 2 output dimension
    _CIRCUIT_FAIL_LIMIT = 3

    def __init__(
        self,
        api_key: str | None = None,
        fallback: EmbeddingModel | None = None,
        surreal_url: str = "ws://localhost:8001",
    ) -> None:
        self._api_key = api_key or os.environ.get("GEMINI_API_KEY", "")
        self._fallback = fallback or FlumeVAEEmbeddingModel()
        self._surreal_url = surreal_url
        self._fail_count = 0  # Simple circuit-breaker counter
        self._surreal: object | None = None  # Lazy SurrealDB handle

    # --- Public interface ---------------------------------------------------

    async def encode(self, text: str) -> EmbeddingResult:
        """Encode with cache-first strategy."""
        key = self._content_hash(text)

        # 1. Cache lookup
        cached_vector = await self._cache_lookup(key)
        if cached_vector is not None:
            return EmbeddingResult(vector=cached_vector, model="gemini-embedding-2", cached=True)

        # 2. Circuit breaker: skip API if too many recent failures
        if self._fail_count >= self._CIRCUIT_FAIL_LIMIT:
            logger.warning("Gemini circuit open (%d failures), routing to fallback", self._fail_count)
            return await self._fallback.encode(text)

        # 3. Call Gemini API
        try:
            vector = await self._call_gemini_api(text)
            self._fail_count = 0  # Reset on success
            await self._cache_store(key, vector)
            return EmbeddingResult(vector=vector, model="gemini-embedding-2")
        except Exception as exc:
            self._fail_count += 1
            logger.warning(
                "Gemini API error (%d/%d): %s — falling back to FLUME VAE",
                self._fail_count,
                self._CIRCUIT_FAIL_LIMIT,
                exc,
            )
            return await self._fallback.encode(text)

    def encode_sync(self, text: str) -> EmbeddingResult:
        """Synchronous wrapper for async encode."""
        try:
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # Called from within an async context — run in thread
                import concurrent.futures

                with concurrent.futures.ThreadPoolExecutor(max_workers=1) as pool:
                    future = pool.submit(asyncio.run, self.encode(text))
                    return future.result()
            return loop.run_until_complete(self.encode(text))
        except RuntimeError:
            return asyncio.run(self.encode(text))

    # --- Internal helpers ---------------------------------------------------

    @staticmethod
    def _content_hash(text: str) -> str:
        return hashlib.sha256(text.encode()).hexdigest()

    async def _call_gemini_api(self, text: str) -> np.ndarray:
        """Call Gemini Embedding 2 API. Raises on any error."""
        try:
            import aiohttp
        except ImportError as exc:
            raise RuntimeError("aiohttp required for Gemini API calls") from exc

        if not self._api_key:
            raise ValueError("GEMINI_API_KEY not set")

        url = f"{self.GEMINI_API_URL}?key={self._api_key}"
        payload = {"model": "models/text-embedding-004", "content": {"parts": [{"text": text}]}}

        async with (
            aiohttp.ClientSession() as session,
            session.post(url, json=payload, timeout=aiohttp.ClientTimeout(total=10)) as resp,
        ):
            if resp.status != 200:
                body = await resp.text()
                raise RuntimeError(f"Gemini API {resp.status}: {body[:200]}")
            data = await resp.json()

        values = data["embedding"]["values"]
        vector = np.array(values, dtype=np.float32)
        norm = np.linalg.norm(vector)
        if norm > 0:
            vector /= norm
        return vector

    async def _cache_lookup(self, key: str) -> np.ndarray | None:
        """Check SurrealDB for a cached embedding vector."""
        try:
            import aiohttp

            url = "http://localhost:8001/sql"
            query = f"SELECT vector FROM embedding_cache WHERE content_hash = '{key}' LIMIT 1;"
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    data=query,
                    headers={"Accept": "application/json", "NS": "cohezion", "DB": "embeddings"},
                    auth=aiohttp.BasicAuth(
                        os.environ.get("SURREAL_USER", "root"),
                        os.environ.get("SURREAL_PASS", "root"),
                    ),
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as resp,
            ):
                if resp.status != 200:
                    return None
                result = await resp.json()
                rows = result[0].get("result", []) if result else []
                if rows and rows[0].get("vector"):
                    return np.array(rows[0]["vector"], dtype=np.float32)
        except Exception as exc:
            logger.debug("Cache lookup skipped: %s", exc)
        return None

    async def _cache_store(self, key: str, vector: np.ndarray) -> None:
        """Store embedding vector in SurrealDB cache."""
        try:
            import aiohttp

            vector_list = vector.tolist()
            query = f"CREATE embedding_cache CONTENT {{content_hash: '{key}', vector: {vector_list}}};"
            url = "http://localhost:8001/sql"
            async with (
                aiohttp.ClientSession() as session,
                session.post(
                    url,
                    data=query,
                    headers={"Accept": "application/json", "NS": "cohezion", "DB": "embeddings"},
                    auth=aiohttp.BasicAuth(
                        os.environ.get("SURREAL_USER", "root"),
                        os.environ.get("SURREAL_PASS", "root"),
                    ),
                    timeout=aiohttp.ClientTimeout(total=2),
                ) as resp,
            ):
                if resp.status != 200:
                    logger.debug("Cache store returned %d", resp.status)
        except Exception as exc:
            logger.debug("Cache store skipped (non-critical): %s", exc)


# ---------------------------------------------------------------------------
# Distiller
# ---------------------------------------------------------------------------


class EmbeddingDistiller:
    """Distills Gemini teacher embeddings into local FLUME VAE student (Phase 2 stub)."""

    def __init__(
        self,
        teacher: GeminiEmbeddingModel,
        student_vae_path: Path | None = None,
    ) -> None:
        self._teacher = teacher
        self._student_vae_path = student_vae_path

    async def distill(
        self,
        corpus: list[str],
        epochs: int = 10,
        output_path: Path | None = None,
    ) -> Path:
        """Fine-tune FLUME VAE to minimize distance to Gemini vectors (Phase 2 stub)."""
        logger.warning(
            "EmbeddingDistiller.distill() is a Phase 2 stub. "
            "corpus=%d texts, epochs=%d. Full FLUME VAE training API not yet implemented.",
            len(corpus),
            epochs,
        )
        return output_path or Path("")


# ---------------------------------------------------------------------------
# Orchestrator
# ---------------------------------------------------------------------------


class EmbeddingOrchestrator:
    """Routes embedding requests to the right model based on context.

    VAULT_INDEXING / TRAINING_REWARD -> Gemini cloud.
    RUNTIME / FAST_ROUTING           -> FLUME VAE local.
    """

    def __init__(
        self,
        gemini_model: GeminiEmbeddingModel | None = None,
        flume_model: FlumeVAEEmbeddingModel | None = None,
    ) -> None:
        self._gemini = gemini_model or GeminiEmbeddingModel()
        self._flume = flume_model or FlumeVAEEmbeddingModel()

    def get_model(self, context: EmbeddingContext) -> EmbeddingModel:
        """Return the appropriate model for the given context."""
        if context in (EmbeddingContext.VAULT_INDEXING, EmbeddingContext.TRAINING_REWARD):
            return self._gemini
        # RUNTIME and FAST_ROUTING both use local FLUME VAE
        return self._flume

    async def encode(
        self,
        text: str,
        context: EmbeddingContext = EmbeddingContext.RUNTIME,
    ) -> EmbeddingResult:
        """Encode text using the model appropriate for the given context."""
        model = self.get_model(context)
        return await model.encode(text)
