"""Tests for ModelPoolManager — 3-tier hot/warm/cold lifecycle management."""

from __future__ import annotations

import time
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.swarm.model_pool_config import (
    ModelTierPolicy,
    PooledModel,
    TierConfig,
)
from cohezion.swarm.model_pool_manager import (
    ModelPoolManager,
    get_pool_manager,
    reset_pool_manager,
)


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def tier_config() -> TierConfig:
    """Minimal tier config for testing."""
    return TierConfig(
        hot_models=["hot-model:latest"],
        warm_models=["warm-model:latest"],
        cold_models=["cold-model:latest"],
        max_concurrent_loaded=2,
        memory_pressure_threshold=0.80,
    )


@pytest.fixture
def pool(tier_config: TierConfig) -> ModelPoolManager:
    """Pool manager with mocked MemoryBandwidthAnalyzer."""
    with patch("cohezion.swarm.model_pool_manager.MemoryBandwidthAnalyzer") as MockAnalyzer:
        mock_analyzer = MockAnalyzer.return_value
        mock_analyzer.analyze_memory_pressure.return_value = 0.5  # 50% pressure
        mock_analyzer.total_memory_gb = 128.0
        mock_analyzer.available_memory_gb = 64.0
        mgr = ModelPoolManager(config=tier_config, ollama_host="http://test:11434")
    # Replace the analyzer with our mock after init
    mgr._memory = mock_analyzer
    return mgr


def _mock_httpx_ok(json_data: dict | None = None):
    """Create a mock httpx response with 200 status."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data or {}
    return resp


# ---------------------------------------------------------------------------
# TestPooledModel
# ---------------------------------------------------------------------------


class TestPooledModel:
    """Tests for the PooledModel dataclass."""

    def test_creation(self):
        m = PooledModel(name="test:latest", tier=ModelTierPolicy.WARM, size_gb=5.0)
        assert m.name == "test:latest"
        assert m.tier == ModelTierPolicy.WARM
        assert m.loaded is False
        assert m.healthy is False
        assert m.error_count == 0

    def test_mark_used(self):
        m = PooledModel(name="test:latest", tier=ModelTierPolicy.HOT, size_gb=1.0)
        old_time = m.last_used
        time.sleep(0.01)
        m.mark_used()
        assert m.last_used > old_time

    def test_record_health_success(self):
        m = PooledModel(name="test:latest", tier=ModelTierPolicy.WARM, size_gb=5.0)
        m.record_health(healthy=True, latency_ms=100.0)
        assert m.healthy is True
        assert m.error_count == 0
        assert m.avg_latency_ms > 0

    def test_record_health_failure_increments_errors(self):
        m = PooledModel(name="test:latest", tier=ModelTierPolicy.WARM, size_gb=5.0)
        m.record_health(healthy=False)
        assert m.healthy is False
        assert m.error_count == 1
        m.record_health(healthy=False)
        assert m.error_count == 2

    def test_record_health_success_resets_errors(self):
        m = PooledModel(name="test:latest", tier=ModelTierPolicy.WARM, size_gb=5.0)
        m.error_count = 3
        m.record_health(healthy=True, latency_ms=50.0)
        assert m.error_count == 0


# ---------------------------------------------------------------------------
# TestModelPoolManager — Core lifecycle
# ---------------------------------------------------------------------------


class TestModelPoolManager:
    """Tests for ModelPoolManager lifecycle operations."""

    @pytest.mark.asyncio
    async def test_initialize_marks_loaded_models(self, pool: ModelPoolManager):
        """Initialize should reconcile with Ollama and mark running models."""
        tags_resp = _mock_httpx_ok({"models": [{"name": "hot-model:latest", "size": 5 * 1024**3}]})
        ps_resp = _mock_httpx_ok({"models": [{"name": "hot-model:latest"}]})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=[tags_resp, ps_resp])

            await pool.initialize()

        hot = pool.get_model("hot-model:latest")
        assert hot is not None
        assert hot.loaded is True
        assert hot.healthy is True
        assert hot.size_gb == pytest.approx(5.0, rel=0.01)

    @pytest.mark.asyncio
    async def test_ensure_loaded_fast_path(self, pool: ModelPoolManager):
        """Already loaded + healthy model should return True immediately."""
        model = pool.get_model("hot-model:latest")
        model.loaded = True
        model.healthy = True

        result = await pool.ensure_loaded("hot-model:latest")
        assert result is True

    @pytest.mark.asyncio
    async def test_ensure_loaded_unknown_model(self, pool: ModelPoolManager):
        """Unknown model should return False."""
        result = await pool.ensure_loaded("nonexistent:latest")
        assert result is False

    @pytest.mark.asyncio
    async def test_ensure_loaded_triggers_load(self, pool: ModelPoolManager):
        """Cold model not loaded should trigger load + health check."""
        load_resp = _mock_httpx_ok({"response": ""})
        health_resp = _mock_httpx_ok({"response": "OK"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=[load_resp, health_resp])

            result = await pool.ensure_loaded("cold-model:latest")

        assert result is True
        model = pool.get_model("cold-model:latest")
        assert model.loaded is True

    @pytest.mark.asyncio
    async def test_ensure_loaded_evicts_when_at_capacity(self, pool: ModelPoolManager):
        """When at max_concurrent_loaded, should evict a lower-priority model."""
        # Pre-load warm + cold to hit capacity (max=2)
        pool.get_model("warm-model:latest").loaded = True
        pool.get_model("warm-model:latest").healthy = True
        pool.get_model("cold-model:latest").loaded = True
        pool.get_model("cold-model:latest").healthy = True

        evict_resp = _mock_httpx_ok({"response": ""})
        load_resp = _mock_httpx_ok({"response": ""})
        health_resp = _mock_httpx_ok({"response": "OK"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=[evict_resp, load_resp, health_resp])

            result = await pool.ensure_loaded("hot-model:latest")

        assert result is True
        # Cold model should have been evicted (lowest priority)
        assert pool.get_model("cold-model:latest").loaded is False

    @pytest.mark.asyncio
    async def test_health_check_success(self, pool: ModelPoolManager):
        """Successful health check should mark model healthy."""
        pool.get_model("warm-model:latest").loaded = True

        resp = _mock_httpx_ok({"response": "OK"})
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=resp)

            result = await pool.health_check("warm-model:latest")

        assert result is True
        assert pool.get_model("warm-model:latest").healthy is True

    @pytest.mark.asyncio
    async def test_health_check_failure(self, pool: ModelPoolManager):
        """Failed health check should mark model unhealthy."""
        model = pool.get_model("warm-model:latest")
        model.loaded = True
        model.healthy = True

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=Exception("Connection refused"))

            result = await pool.health_check("warm-model:latest")

        assert result is False
        assert model.healthy is False
        assert model.error_count == 1

    @pytest.mark.asyncio
    async def test_evict_hot_model_refused(self, pool: ModelPoolManager):
        """HOT models must never be evicted."""
        pool.get_model("hot-model:latest").loaded = True
        result = await pool.evict_model("hot-model:latest")
        assert result is False
        assert pool.get_model("hot-model:latest").loaded is True

    @pytest.mark.asyncio
    async def test_evict_warm_model(self, pool: ModelPoolManager):
        """WARM models should be evictable."""
        pool.get_model("warm-model:latest").loaded = True

        resp = _mock_httpx_ok({"response": ""})
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(return_value=resp)

            result = await pool.evict_model("warm-model:latest")

        assert result is True
        assert pool.get_model("warm-model:latest").loaded is False

    @pytest.mark.asyncio
    async def test_promote_cold_to_warm(self, pool: ModelPoolManager):
        """Promoting cold -> warm should update tier and trigger load."""
        load_resp = _mock_httpx_ok({"response": ""})
        health_resp = _mock_httpx_ok({"response": "OK"})

        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.post = AsyncMock(side_effect=[load_resp, health_resp])

            await pool.promote("cold-model:latest", ModelTierPolicy.WARM)

        model = pool.get_model("cold-model:latest")
        assert model.tier == ModelTierPolicy.WARM
        assert model.loaded is True

    def test_get_available_models(self, pool: ModelPoolManager):
        """get_available_models should only return loaded + healthy models."""
        pool.get_model("hot-model:latest").loaded = True
        pool.get_model("hot-model:latest").healthy = True
        pool.get_model("warm-model:latest").loaded = True
        pool.get_model("warm-model:latest").healthy = False  # unhealthy
        pool.get_model("cold-model:latest").loaded = False

        available = pool.get_available_models()
        assert len(available) == 1
        assert available[0].name == "hot-model:latest"

    def test_get_pool_status(self, pool: ModelPoolManager):
        """Pool status should reflect current state."""
        pool.get_model("hot-model:latest").loaded = True
        pool.get_model("hot-model:latest").healthy = True
        pool.get_model("hot-model:latest").size_gb = 3.0

        status = pool.get_pool_status()
        assert "hot-model:latest" in status.loaded_models
        assert "hot-model:latest" in status.healthy_models
        assert status.total_memory_gb == pytest.approx(3.0)
        assert 0.0 <= status.memory_pressure <= 1.0


# ---------------------------------------------------------------------------
# TestPoolManagerIntegration — with CostAwareRouter
# ---------------------------------------------------------------------------


class TestPoolManagerIntegration:
    """Test ModelPoolManager integration with CostAwareRouter."""

    def test_router_uses_pool_for_availability(self):
        """CostAwareRouter should fall back when preferred model unavailable."""
        from cohezion.swarm.cost_aware_router import CostAwareRouter

        # Create pool with only phi3:mini available
        config = TierConfig(
            hot_models=["phi3:mini"],
            warm_models=[],
            cold_models=[],
        )
        with patch("cohezion.swarm.model_pool_manager.MemoryBandwidthAnalyzer"):
            pool_mgr = ModelPoolManager(config=config)

        pool_mgr.get_model("phi3:mini").loaded = True
        pool_mgr.get_model("phi3:mini").healthy = True

        router = CostAwareRouter(pool_manager=pool_mgr)
        decision, _can_proceed = router.select_model("Design a complex distributed system")

        # Should fall back to phi3:mini since it's the only available model
        assert decision.model == "phi3:mini"

    def test_router_without_pool_unchanged(self):
        """CostAwareRouter without pool_manager should behave identically."""
        from cohezion.swarm.cost_aware_router import CostAwareRouter

        router = CostAwareRouter(pool_manager=None)
        decision, _can_proceed = router.select_model("What is Python?")

        # Normal routing, no pool interference
        assert decision.model in ("phi3:mini", "qwen3-coder:32b", "deepseek-r1:8b")


# ---------------------------------------------------------------------------
# TestPoolManagerEdgeCases
# ---------------------------------------------------------------------------


class TestPoolManagerEdgeCases:
    """Edge case tests for ModelPoolManager."""

    @pytest.mark.asyncio
    async def test_all_models_unhealthy(self, pool: ModelPoolManager):
        """get_available_models should return empty when all unhealthy."""
        for m in pool._pool.values():
            m.loaded = True
            m.healthy = False

        assert pool.get_available_models() == []

    @pytest.mark.asyncio
    async def test_high_memory_pressure_eviction(self, pool: ModelPoolManager):
        """Under high memory pressure, cold and warm should be evicted."""
        pool._memory.analyze_memory_pressure.return_value = 0.95
        pool.get_model("warm-model:latest").loaded = True
        pool.get_model("cold-model:latest").loaded = True

        evict_resp = _mock_httpx_ok({"response": ""})
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            # Need to keep returning OK for evictions, but pressure stays high
            mock_client.post = AsyncMock(return_value=evict_resp)

            evicted = await pool.demote_under_pressure()

        assert len(evicted) >= 1
        # Cold should be evicted first
        assert "cold-model:latest" in evicted

    @pytest.mark.asyncio
    async def test_ollama_unreachable_on_initialize(self, pool: ModelPoolManager):
        """Pool should handle Ollama being down at initialization."""
        with patch("httpx.AsyncClient") as MockClient:
            mock_client = AsyncMock()
            MockClient.return_value.__aenter__ = AsyncMock(return_value=mock_client)
            MockClient.return_value.__aexit__ = AsyncMock(return_value=False)
            mock_client.get = AsyncMock(side_effect=Exception("Connection refused"))

            await pool.initialize()

        # All models should be marked as not loaded
        for m in pool._pool.values():
            assert m.loaded is False

    def test_singleton_lifecycle(self):
        """get_pool_manager / reset_pool_manager should manage singleton."""
        reset_pool_manager()
        with patch("cohezion.swarm.model_pool_manager.MemoryBandwidthAnalyzer"):
            mgr1 = get_pool_manager()
            mgr2 = get_pool_manager()
        assert mgr1 is mgr2

        reset_pool_manager()
        with patch("cohezion.swarm.model_pool_manager.MemoryBandwidthAnalyzer"):
            mgr3 = get_pool_manager()
        assert mgr3 is not mgr1

    @pytest.mark.asyncio
    async def test_health_check_on_unloaded_model(self, pool: ModelPoolManager):
        """Health checking an unloaded model should return False without network call."""
        result = await pool.health_check("cold-model:latest")
        assert result is False

    @pytest.mark.asyncio
    async def test_promote_invalid_direction_raises(self, pool: ModelPoolManager):
        """Promoting to a lower or equal tier should raise ValueError."""
        with pytest.raises(ValueError, match="must be strictly higher"):
            await pool.promote("hot-model:latest", ModelTierPolicy.COLD)

    @pytest.mark.asyncio
    async def test_promote_same_tier_raises(self, pool: ModelPoolManager):
        """Promoting to the same tier should raise ValueError."""
        with pytest.raises(ValueError, match="must be strictly higher"):
            await pool.promote("warm-model:latest", ModelTierPolicy.WARM)
