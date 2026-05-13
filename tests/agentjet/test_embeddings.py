"""Tests for EmbeddingOrchestrator, GeminiEmbeddingModel, and FlumeVAEEmbeddingModel."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import numpy as np
import pytest

from cohezion.agentjet.embeddings import (
    EmbeddingContext,
    EmbeddingOrchestrator,
    EmbeddingResult,
    FlumeVAEEmbeddingModel,
    GeminiEmbeddingModel,
)


# ---------------------------------------------------------------------------
# EmbeddingResult
# ---------------------------------------------------------------------------


def test_embedding_result_sets_dimension_from_vector() -> None:
    vec = np.zeros(256, dtype=np.float32)
    result = EmbeddingResult(vector=vec, model="test")
    assert result.dimension == 256


def test_embedding_result_gemini_dimension() -> None:
    vec = np.ones(768, dtype=np.float32)
    result = EmbeddingResult(vector=vec, model="gemini-embedding-2")
    assert result.dimension == 768


# ---------------------------------------------------------------------------
# EmbeddingOrchestrator routing
# ---------------------------------------------------------------------------


def test_orchestrator_vault_indexing_routes_to_gemini() -> None:
    mock_gemini = MagicMock()
    mock_flume = MagicMock()
    orch = EmbeddingOrchestrator(gemini_model=mock_gemini, flume_model=mock_flume)

    model = orch.get_model(EmbeddingContext.VAULT_INDEXING)
    assert model is mock_gemini


def test_orchestrator_runtime_routes_to_flume() -> None:
    mock_gemini = MagicMock()
    mock_flume = MagicMock()
    orch = EmbeddingOrchestrator(gemini_model=mock_gemini, flume_model=mock_flume)

    model = orch.get_model(EmbeddingContext.RUNTIME)
    assert model is mock_flume


def test_orchestrator_training_reward_routes_to_gemini() -> None:
    mock_gemini = MagicMock()
    mock_flume = MagicMock()
    orch = EmbeddingOrchestrator(gemini_model=mock_gemini, flume_model=mock_flume)

    model = orch.get_model(EmbeddingContext.TRAINING_REWARD)
    assert model is mock_gemini


def test_orchestrator_fast_routing_routes_to_flume() -> None:
    mock_gemini = MagicMock()
    mock_flume = MagicMock()
    orch = EmbeddingOrchestrator(gemini_model=mock_gemini, flume_model=mock_flume)

    model = orch.get_model(EmbeddingContext.FAST_ROUTING)
    assert model is mock_flume


# ---------------------------------------------------------------------------
# GeminiEmbeddingModel fallback when API key missing
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gemini_falls_back_when_api_key_missing() -> None:
    fallback_vec = np.zeros(256, dtype=np.float32)
    mock_fallback = AsyncMock()
    mock_fallback.encode = AsyncMock(return_value=EmbeddingResult(vector=fallback_vec, model="flume-vae-256d"))

    # No API key → _call_gemini_api raises ValueError
    model = GeminiEmbeddingModel(api_key="", fallback=mock_fallback)

    # Patch cache lookup to always miss
    with patch.object(model, "_cache_lookup", new_callable=AsyncMock, return_value=None):
        result = await model.encode("hello world")

    mock_fallback.encode.assert_called_once()
    assert result.model == "flume-vae-256d"


# ---------------------------------------------------------------------------
# GeminiEmbeddingModel cache hit
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_gemini_uses_cache_when_content_hash_matches() -> None:
    cached_vec = np.ones(768, dtype=np.float32)
    mock_fallback = MagicMock()
    model = GeminiEmbeddingModel(api_key="test-key", fallback=mock_fallback)

    with patch.object(model, "_cache_lookup", new_callable=AsyncMock, return_value=cached_vec):
        result = await model.encode("test text")

    assert result.cached is True
    assert result.model == "gemini-embedding-2"
    np.testing.assert_array_equal(result.vector, cached_vec)


# ---------------------------------------------------------------------------
# GeminiEmbeddingModel circuit breaker
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_circuit_breaker_activates_after_3_failures() -> None:
    fallback_vec = np.zeros(256, dtype=np.float32)
    mock_fallback = AsyncMock()
    mock_fallback.encode = AsyncMock(return_value=EmbeddingResult(vector=fallback_vec, model="flume-vae-256d"))

    model = GeminiEmbeddingModel(api_key="test-key", fallback=mock_fallback)

    # Patch cache always misses
    with patch.object(model, "_cache_lookup", new_callable=AsyncMock, return_value=None):
        with patch.object(model, "_cache_store", new_callable=AsyncMock):
            # Make API always fail
            with patch.object(
                model,
                "_call_gemini_api",
                new_callable=AsyncMock,
                side_effect=RuntimeError("api down"),
            ):
                for _ in range(3):
                    await model.encode(f"text {_}")

            # After 3 failures, circuit is open — API should NOT be called
            with patch.object(model, "_call_gemini_api", new_callable=AsyncMock) as mock_api:
                await model.encode("another text")
                mock_api.assert_not_called()


@pytest.mark.asyncio
async def test_circuit_breaker_resets_on_success() -> None:
    fallback_vec = np.zeros(256, dtype=np.float32)
    mock_fallback = AsyncMock()
    mock_fallback.encode = AsyncMock(return_value=EmbeddingResult(vector=fallback_vec, model="flume-vae-256d"))

    model = GeminiEmbeddingModel(api_key="test-key", fallback=mock_fallback)
    model._fail_count = 2  # 2 failures, not yet open

    good_vec = np.ones(768, dtype=np.float32)
    with patch.object(model, "_cache_lookup", new_callable=AsyncMock, return_value=None):
        with patch.object(model, "_cache_store", new_callable=AsyncMock):
            with patch.object(model, "_call_gemini_api", new_callable=AsyncMock, return_value=good_vec):
                result = await model.encode("text")

    assert model._fail_count == 0  # Reset on success
    assert result.model == "gemini-embedding-2"


# ---------------------------------------------------------------------------
# FlumeVAEEmbeddingModel hash fallback
# ---------------------------------------------------------------------------


def test_flume_hash_encode_returns_256d_vector() -> None:
    vec = FlumeVAEEmbeddingModel._hash_encode("test text")
    assert vec.shape == (256,)
    assert vec.dtype == np.float32


def test_flume_hash_encode_is_deterministic() -> None:
    v1 = FlumeVAEEmbeddingModel._hash_encode("consistent input")
    v2 = FlumeVAEEmbeddingModel._hash_encode("consistent input")
    np.testing.assert_array_equal(v1, v2)


def test_flume_hash_encode_normalized() -> None:
    vec = FlumeVAEEmbeddingModel._hash_encode("normalized text")
    norm = float(np.linalg.norm(vec))
    assert norm == pytest.approx(1.0, abs=1e-5)
