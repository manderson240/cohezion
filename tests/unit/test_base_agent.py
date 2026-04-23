"""Tests for the base agent module (cohezion.agents.base)."""

from __future__ import annotations

import hashlib
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest


# ---------------------------------------------------------------------------
# AgentResponse tests (requires no heavy imports)
# ---------------------------------------------------------------------------


class TestAgentResponse:
    """Test AgentResponse, a str subclass with metadata."""

    def _make(self, content="hello", **kwargs):
        from cohezion.agents.base import AgentResponse

        return AgentResponse(content, **kwargs)

    def test_is_string(self):
        r = self._make("hello world")
        assert isinstance(r, str)
        assert r == "hello world"

    def test_metadata_attributes(self):
        r = self._make("ok", phi_score=0.9, confidence=0.8)
        assert r.phi_score == 0.9
        assert r.confidence == 0.8

    def test_missing_attribute_returns_none(self):
        r = self._make("ok")
        assert r.nonexistent_field is None

    def test_string_operations(self):
        r = self._make("hello")
        assert r.upper() == "HELLO"
        assert r + " world" == "hello world"
        assert len(r) == 5


# ---------------------------------------------------------------------------
# BaseAgent tests — everything mocked
# ---------------------------------------------------------------------------

# Module-level imports in base.py (can be patched on cohezion.agents.base)
_MODULE_LEVEL_PATCHES = {
    "cohezion.agents.base.SurrealClient": MagicMock,
    "cohezion.agents.base.get_credit_manager": MagicMock,
    "cohezion.agents.base.PromptGuard": MagicMock,
    "cohezion.agents.base.OutputFilter": MagicMock,
    "cohezion.agents.base.UniverseSimulationEngine": MagicMock,
    "cohezion.agents.base.RewardSystem": MagicMock,
    "cohezion.agents.base.OffloadManager": MagicMock,
    "cohezion.agents.base.ContextHarness": MagicMock,
    "cohezion.agents.base.BatchManager": MagicMock,
    "cohezion.agents.base.SemanticCache": MagicMock,
    "cohezion.agents.base.CompoundLogicEngine": MagicMock,
    "cohezion.agents.base.get_pool": MagicMock,
    "cohezion.agents.base.get_resource_monitor": MagicMock,
    "cohezion.agents.base.get_time_keeper": MagicMock,
}

# Local imports inside functions/methods — must be patched at their source modules
# (FlumeEncoder is imported lazily inside BaseAgent, and at module level only
# under `if TYPE_CHECKING:`, so patching cohezion.agents.base.FlumeEncoder fails.)
_LOCAL_IMPORT_PATCHES = {
    "cohezion.flume.autoencoder.FlumeEncoder": MagicMock,
    "cohezion.registry.capability_registry.CapabilityRegistry": MagicMock,
    "cohezion.swarm.journey_narrator.JourneyNarrator": MagicMock,
    "cohezion.swarm.redundancy_suppression.RedundancyManager": MagicMock,
}


def _make_agent(tmp_path: Path):
    """Create a TestableAgent with ALL dependencies mocked."""
    from cohezion.agents.base import BaseAgent

    class TestableAgent(BaseAgent):
        async def process(self, *args, **kwargs):
            return "test response"

    patchers = []
    for target in {**_MODULE_LEVEL_PATCHES, **_LOCAL_IMPORT_PATCHES}:
        p = patch(target, MagicMock())
        p.start()
        patchers.append(p)

    from cohezion.swarm.swarm_types import SwarmConfig

    config = SwarmConfig(mrp_sync=False, cache_ttl_seconds=3600)
    agent = TestableAgent(model_name="test-model", config=config, cache_dir=tmp_path / "cache")

    return agent, patchers


def _cleanup(patchers):
    for p in patchers:
        p.stop()


class TestBaseAgentInit:
    def test_model_name_set(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            assert agent.model_name == "test-model"
        finally:
            _cleanup(patchers)

    def test_metrics_initialized(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            assert agent._metrics["total_calls"] == 0
            assert agent._metrics["cache_hits"] == 0
            assert agent._metrics["total_latency_ms"] == 0
            assert agent._metrics["errors"] == 0
        finally:
            _cleanup(patchers)

    def test_cache_dir_created(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            assert agent.cache_dir.exists()
        finally:
            _cleanup(patchers)


class TestCacheKey:
    def test_deterministic(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            k1 = agent._cache_key("hello world")
            k2 = agent._cache_key("hello world")
            assert k1 == k2
        finally:
            _cleanup(patchers)

    def test_different_prompts_different_keys(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            k1 = agent._cache_key("hello")
            k2 = agent._cache_key("world")
            assert k1 != k2
        finally:
            _cleanup(patchers)

    def test_images_affect_key(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            k1 = agent._cache_key("prompt")
            k2 = agent._cache_key("prompt", images=["img1.png"])
            assert k1 != k2
        finally:
            _cleanup(patchers)

    def test_key_is_sha256(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            key = agent._cache_key("test")
            expected = hashlib.sha256(b"test-model:test").hexdigest()
            assert key == expected
        finally:
            _cleanup(patchers)


class TestCacheRoundTrip:
    @pytest.mark.asyncio
    async def test_set_and_get_cached(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            agent._encoder = None  # Skip semantic cache

            await agent._set_cached("test prompt", "test response")

            result = await agent._get_cached("test prompt")
            assert result is not None
            assert result["response"] == "test response"
            assert result["model"] == "test-model"
        finally:
            _cleanup(patchers)

    @pytest.mark.asyncio
    async def test_get_cached_miss(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            agent._encoder = None
            result = await agent._get_cached("nonexistent prompt")
            assert result is None
        finally:
            _cleanup(patchers)

    @pytest.mark.asyncio
    async def test_cache_expired(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            agent._encoder = None
            agent.config.cache_ttl_seconds = 0  # Immediate expiry

            await agent._set_cached("prompt", "response")
            result = await agent._get_cached("prompt")
            assert result is None
        finally:
            _cleanup(patchers)


class TestGetMetrics:
    def test_returns_expected_keys(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            tk_mock = MagicMock()
            tk_mock.now_iso = "2026-02-06T00:00:00"
            with patch("cohezion.agents.base.get_time_keeper", return_value=tk_mock):
                metrics = agent.get_metrics()

            assert "model" in metrics
            assert "cache_hit_rate" in metrics
            assert "avg_latency_ms" in metrics
            assert "timestamp" in metrics
            assert metrics["model"] == "test-model"
        finally:
            _cleanup(patchers)

    def test_cache_hit_rate_zero_calls(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            tk_mock = MagicMock()
            tk_mock.now_iso = "2026-02-06T00:00:00"
            with patch("cohezion.agents.base.get_time_keeper", return_value=tk_mock):
                metrics = agent.get_metrics()
            assert metrics["cache_hit_rate"] == 0.0
        finally:
            _cleanup(patchers)


class TestDelegateTask:
    @pytest.mark.asyncio
    async def test_delegate_no_target_no_match(self, tmp_path):
        agent, patchers = _make_agent(tmp_path)
        try:
            agent.registry.find = MagicMock(return_value=[])
            tk_mock = MagicMock()
            tk_mock.log_event = AsyncMock()
            with patch("cohezion.agents.base.get_time_keeper", return_value=tk_mock):
                result = await agent.delegate_task("some query")
            assert result is None
        finally:
            _cleanup(patchers)
