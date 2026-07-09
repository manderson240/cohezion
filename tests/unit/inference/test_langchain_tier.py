"""Unit tests for LangChainTier — graceful degradation and structure."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from cohezion.inference.langchain_tier import (
    LangChainTier,
    LangChainTierResult,
    _langchain_available,
)


class TestLangChainAvailability:
    def test_returns_bool(self):
        result = _langchain_available()
        assert isinstance(result, bool)

    def test_graceful_when_unavailable(self):
        with patch.dict("sys.modules", {"langchain_core": None}):
            result = _langchain_available()
            assert result is False


class TestLangChainTierResult:
    def test_default_fields(self):
        r = LangChainTierResult(text="answer", primary_model="test", latency_ms=100.0)
        assert r.cost_usd == 0.0
        assert r.escalation_count == 0
        assert r.source_documents == []

    def test_with_source_documents(self):
        r = LangChainTierResult(
            text="answer",
            primary_model="rag",
            latency_ms=50.0,
            source_documents=["doc1.md", "doc2.md"],
        )
        assert len(r.source_documents) == 2


class TestLangChainTier:
    def test_init_with_defaults(self):
        tier = LangChainTier()
        assert tier.model_label == "langchain-rag"
        assert tier.timeout_s > 0

    def test_init_with_custom_label(self):
        tier = LangChainTier(model_label="custom-rag")
        assert tier.model_label == "custom-rag"

    def test_run_sync_returns_tuple(self):
        """run_sync() returns (text, metrics_dict) tuple compatible with execute_fn."""
        tier = LangChainTier()
        result = tier.run_sync("What is HIHO?")
        assert isinstance(result, tuple)
        assert len(result) == 2
        text, metrics = result
        assert isinstance(text, str)
        assert isinstance(metrics, dict)
        assert "model" in metrics

    def test_run_sync_metrics_has_cost_usd(self):
        """run_sync() metrics dict includes cost_usd."""
        tier = LangChainTier()
        _, metrics = tier.run_sync("test")
        assert "cost_usd" in metrics
        assert "latency_ms" in metrics

    @pytest.mark.asyncio
    async def test_run_async_returns_result(self):
        """run() is async wrapper that returns LangChainTierResult."""
        tier = LangChainTier()
        result = await tier.run("What is LENR?")
        assert isinstance(result, LangChainTierResult)
        assert isinstance(result.text, str)
        assert isinstance(result.latency_ms, float)

    def test_run_sync_with_mock_chain(self):
        """With a mock chain, run_sync extracts text from chain output."""
        mock_chain = MagicMock()
        mock_chain.invoke.return_value = {"result": "HIHO is equilibrium", "source_documents": []}
        tier = LangChainTier(chain=mock_chain)
        text, metrics = tier.run_sync("What is HIHO?")
        assert isinstance(text, str)
        assert isinstance(metrics, dict)
