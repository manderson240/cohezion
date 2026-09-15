"""Backend routing tests for ModelPoolManager — per-backend load dispatch, caps, eviction order.

Covers the fix for the hardcoded ``llamacpp_backend: rocm`` load payload: the pool
now classifies models via ``cohezion.inference.fabric`` and dispatches per backend
(NPU->'flm', IGPU->'rocm', CPU->'cpu'). Also covers per-backend residency caps
(refusal-as-success) and backend-preferred eviction order (iGPU -> CPU -> NPU).

All HTTP is mocked at module level (no network): ``httpx.AsyncClient`` per test and
``fabric.resident_by_backend`` (the census seam) via an autouse fixture.
"""

from __future__ import annotations

from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from cohezion.inference.fabric import Backend, backend_for_model, resident_by_backend
from cohezion.swarm.model_pool_config import ModelTierPolicy, PooledModel, TierConfig
from cohezion.swarm.model_pool_manager import (
    _BACKEND_EVICTION_ORDER,
    _FABRIC_TO_LLAMACPP,
    ModelPoolManager,
)


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------


def _mock_httpx_ok(json_data: dict | None = None) -> MagicMock:
    """Mock httpx response with a 200 status."""
    resp = MagicMock()
    resp.status_code = 200
    resp.raise_for_status = MagicMock()
    resp.json.return_value = json_data or {}
    return resp


def _make_pool(
    hot: list[str] | None = None,
    warm: list[str] | None = None,
    cold: list[str] | None = None,
    max_concurrent: int = 8,
    caps: dict[str, int] | None = None,
) -> ModelPoolManager:
    """Pool manager with MemoryBandwidthAnalyzer and LemonadeManager mocked."""
    kwargs: dict[str, Any] = {
        "hot_models": hot or [],
        "warm_models": warm or [],
        "cold_models": cold or [],
        "max_concurrent_loaded": max_concurrent,
    }
    if caps is not None:
        kwargs["per_backend_max_resident"] = caps
    config = TierConfig(**kwargs)
    with patch("cohezion.swarm.model_pool_manager.MemoryBandwidthAnalyzer") as MockAnalyzer:
        analyzer = MockAnalyzer.return_value
        analyzer.analyze_memory_pressure.return_value = 0.5
        mgr = ModelPoolManager(config=config, ollama_host="http://test:11434")
        mgr._memory = analyzer
    lemonade = AsyncMock()
    lemonade.host = "127.0.0.1"
    lemonade.port = 13307
    mgr.lemonade = lemonade
    return mgr


def _model(mgr: ModelPoolManager, name: str) -> PooledModel:
    """get_model with a non-None assert (typing + fail fast)."""
    model = mgr.get_model(name)
    assert model is not None, f"model {name} missing from pool"
    return model


@pytest.fixture(autouse=True)
def _stub_census(monkeypatch):
    """Stub the fabric residency census at module level (no HTTP)."""

    def _empty_census(*args: Any, **kwargs: Any) -> dict:
        return {}

    monkeypatch.setattr(
        "cohezion.swarm.model_pool_manager.resident_by_backend", _empty_census
    )
    return _empty_census


# Names routed through the Lemonade /api/v1/load branch: the is_lemonade
# heuristic matches "gemma4:26b-moe", while the suffix markers classify the
# model onto the NPU/CPU/CLOUD lanes.
_IGPU_NAME = "gemma4:26b-moe"
_NPU_NAME = "gemma4:26b-moe-FLM"
_CPU_NAME = "gemma4:26b-moe-CPU-32T"
_CLOUD_NAME = "gemma4:26b-moe:cloud"


class _PostCapture:
    """Context manager: patches httpx.AsyncClient, records every POST (url, payload)."""

    def __init__(self) -> None:
        self.posts: list[tuple[str, dict]] = []
        self._patcher: Any = None

    def __enter__(self) -> "_PostCapture":
        self._patcher = patch("httpx.AsyncClient")
        mock_client_cls = self._patcher.__enter__()
        client = AsyncMock()
        mock_client_cls.return_value.__aenter__ = AsyncMock(return_value=client)
        mock_client_cls.return_value.__aexit__ = AsyncMock(return_value=False)

        def _capture(url: str, json: dict | None = None, **kwargs: Any) -> MagicMock:
            self.posts.append((url, json or {}))
            return _mock_httpx_ok({})

        client.post = AsyncMock(side_effect=_capture)
        return self

    def __exit__(self, *exc_info: Any) -> None:
        if self._patcher is not None:
            self._patcher.__exit__(*exc_info)


# ---------------------------------------------------------------------------
# fabric classification
# ---------------------------------------------------------------------------


class TestBackendForModel:
    """fabric.backend_for_model classification used by the pool manager."""

    def test_flm_name_is_npu(self):
        assert backend_for_model("deepseek-r1-0528-8b-FLM") is Backend.NPU

    def test_flm_mtp_variant_is_npu(self):
        assert backend_for_model("qwen3.6-moe-35b-a3b-FLM-MTP") is Backend.NPU

    def test_cloud_suffix_is_cloud(self):
        assert backend_for_model("deepseek-v4-pro:cloud") is Backend.CLOUD

    def test_cpu_marker_is_cpu(self):
        assert backend_for_model("Phi-4-mini-3.8B-CPU-32T") is Backend.CPU

    def test_plain_gguf_name_is_igpu(self):
        assert backend_for_model("qwen3-coder:30b") is Backend.IGPU

    def test_empty_name_defaults_to_igpu(self):
        assert backend_for_model("") is Backend.IGPU


class TestBackendMappingTables:
    """Module-level Backend -> payload / eviction-order mappings."""

    def test_payload_mapping_covers_local_lanes(self):
        assert _FABRIC_TO_LLAMACPP == {
            Backend.NPU: "flm",
            Backend.IGPU: "rocm",
            Backend.CPU: "cpu",
        }

    def test_payload_mapping_excludes_cloud(self):
        assert Backend.CLOUD not in _FABRIC_TO_LLAMACPP

    def test_eviction_order_prefers_igpu_then_cpu_then_npu(self):
        assert _BACKEND_EVICTION_ORDER == {"igpu": 0, "cpu": 1, "npu": 2}


# ---------------------------------------------------------------------------
# Per-backend load dispatch (the hardcoded-rocm regression)
# ---------------------------------------------------------------------------


class TestLoadDispatch:
    """_load_model sends the classified backend in the Lemonade load payload."""

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("model_name", "expected_backend"),
        [
            (_IGPU_NAME, "rocm"),
            (_NPU_NAME, "flm"),
            (_CPU_NAME, "cpu"),
        ],
    )
    async def test_load_payload_carries_classified_backend(
        self, model_name, expected_backend
    ):
        mgr = _make_pool(hot=[model_name])
        with _PostCapture() as cap:
            assert await mgr._load_model(model_name, ModelTierPolicy.HOT) is True

        assert cap.posts, "expected an HTTP load call"
        url, payload = cap.posts[0]
        assert "/api/v1/load" in url
        assert payload["model_name"] == model_name
        assert payload["llamacpp_backend"] == expected_backend

    @pytest.mark.asyncio
    async def test_flm_model_not_sent_down_rocm_lane(self):
        """Regression: an FLM model must NOT get the old hardcoded rocm lane."""
        mgr = _make_pool(hot=[_NPU_NAME])
        with _PostCapture() as cap:
            await mgr._load_model(_NPU_NAME, ModelTierPolicy.HOT)

        _, payload = cap.posts[0]
        assert payload["llamacpp_backend"] != "rocm"
        assert payload["llamacpp_backend"] == "flm"

    @pytest.mark.asyncio
    async def test_ensure_loaded_stamps_npu_backend_field(self):
        mgr = _make_pool(hot=[_NPU_NAME])
        with _PostCapture():
            assert await mgr.ensure_loaded(_NPU_NAME) is True
        assert _model(mgr, _NPU_NAME).backend == "npu"

    @pytest.mark.asyncio
    async def test_ensure_loaded_stamps_igpu_backend_field(self):
        mgr = _make_pool(hot=["qwen3-coder:30b"])
        with _PostCapture():
            assert await mgr.ensure_loaded("qwen3-coder:30b") is True
        assert _model(mgr, "qwen3-coder:30b").backend == "igpu"

    @pytest.mark.asyncio
    async def test_cloud_classified_model_never_loads_via_lemonade(self):
        mgr = _make_pool(hot=[_CLOUD_NAME])
        with _PostCapture() as cap:
            result = await mgr.ensure_loaded(_CLOUD_NAME)
        assert result is False
        assert cap.posts == []

    def test_pooled_model_default_backend_is_igpu(self):
        m = PooledModel(name=_IGPU_NAME, tier=ModelTierPolicy.HOT, size_gb=0.0)
        assert m.backend == "igpu"


# ---------------------------------------------------------------------------
# Per-backend residency caps — refusal-as-success
# ---------------------------------------------------------------------------


class TestPerBackendCaps:
    """TierConfig.per_backend_max_resident enforced BEFORE _load_model."""

    def test_default_caps(self):
        config = TierConfig()
        assert config.per_backend_max_resident == {"npu": 5, "igpu": 2, "cpu": 3}

    @pytest.mark.asyncio
    async def test_cap_refusal_returns_false_without_load_call(self, monkeypatch):
        """At-cap backend refuses: log + return False; the pool loop must not crash."""
        mgr = _make_pool(hot=["qwen3-coder:30b"], caps={"igpu": 1})
        monkeypatch.setattr(
            "cohezion.swarm.model_pool_manager.resident_by_backend",
            lambda *a, **k: {Backend.IGPU: ["resident-igpu"]},
        )
        with patch(
            "cohezion.swarm.model_pool_manager.ModelPoolManager._load_model",
            new_callable=AsyncMock,
        ) as mock_load:
            result = await mgr.ensure_loaded("qwen3-coder:30b")

        assert result is False
        mock_load.assert_not_called()

    @pytest.mark.asyncio
    async def test_cap_with_room_admits_load(self, monkeypatch):
        mgr = _make_pool(hot=["qwen3-coder:30b"], caps={"igpu": 2})
        monkeypatch.setattr(
            "cohezion.swarm.model_pool_manager.resident_by_backend",
            lambda *a, **k: {Backend.IGPU: ["one-resident"]},
        )
        with _PostCapture():
            assert await mgr.ensure_loaded("qwen3-coder:30b") is True

    @pytest.mark.asyncio
    async def test_cap_refusal_does_not_evict_for_the_capped_backend(self, monkeypatch):
        """No cap-bypassing eviction: refusal happens before the eviction block."""
        mgr = _make_pool(hot=["qwen3-coder:30b"], warm=["warm-igpu:latest"], caps={"igpu": 1})
        monkeypatch.setattr(
            "cohezion.swarm.model_pool_manager.resident_by_backend",
            lambda *a, **k: {Backend.IGPU: ["resident"]},
        )
        with patch(
            "cohezion.swarm.model_pool_manager.ModelPoolManager.evict_model",
            new_callable=AsyncMock,
        ) as mock_evict:
            result = await mgr.ensure_loaded("qwen3-coder:30b")

        assert result is False
        mock_evict.assert_not_called()

    @pytest.mark.asyncio
    async def test_backend_missing_from_caps_is_uncapped(self, monkeypatch):
        """A backend absent from per_backend_max_resident has no cap."""
        mgr = _make_pool(hot=[_CPU_NAME], caps={})
        monkeypatch.setattr(
            "cohezion.swarm.model_pool_manager.resident_by_backend",
            lambda *a, **k: {Backend.CPU: [f"r{i}" for i in range(9)]},
        )
        with _PostCapture():
            assert await mgr.ensure_loaded(_CPU_NAME) is True

    @pytest.mark.asyncio
    async def test_npu_cap_counts_only_npu_residents(self, monkeypatch):
        """iGPU residents must not count against the NPU cap (and vice versa)."""
        mgr = _make_pool(hot=[_NPU_NAME], caps={"npu": 1, "igpu": 2})
        monkeypatch.setattr(
            "cohezion.swarm.model_pool_manager.resident_by_backend",
            lambda *a, **k: {Backend.IGPU: ["igpu-1", "igpu-2"]},
        )
        with _PostCapture():
            # NPU cap is 1 with 0 NPU residents -> the load must be admitted.
            assert await mgr.ensure_loaded(_NPU_NAME) is True


# ---------------------------------------------------------------------------
# Eviction preference: iGPU -> CPU -> NPU
# ---------------------------------------------------------------------------


async def _async_true(name: str) -> bool:
    return True


class TestEvictionPreference:
    """demote_under_pressure prefers iGPU residents, then CPU, then NPU."""

    @staticmethod
    def _pressure_pool() -> ModelPoolManager:
        names = ["igpu-a:latest", "igpu-b:latest", "cpu-a:latest", "npu-a-FLM", "npu-b-FLM"]
        mgr = _make_pool(warm=names, max_concurrent=16, caps={"npu": 5, "igpu": 2, "cpu": 3})
        labels = {
            "igpu-a:latest": "igpu",
            "igpu-b:latest": "igpu",
            "cpu-a:latest": "cpu",
            "npu-a-FLM": "npu",
            "npu-b-FLM": "npu",
        }
        for i, name in enumerate(names):
            model = _model(mgr, name)
            model.loaded = True
            model.healthy = True
            model.backend = labels[name]
            model.last_used = 100.0 + i  # deterministic LRU within each group
        return mgr

    @staticmethod
    def _evict_all_patcher():
        return patch(
            "cohezion.swarm.model_pool_manager.ModelPoolManager.evict_model",
            new_callable=AsyncMock,
        )

    @pytest.mark.asyncio
    async def test_igpu_evicted_before_cpu_and_npu(self, monkeypatch):
        mgr = self._pressure_pool()
        monkeypatch.setattr(mgr._memory, "analyze_memory_pressure", lambda: 0.95, raising=True)
        with self._evict_all_patcher() as mock_evict:
            mock_evict.side_effect = _async_true
            evicted = await mgr.demote_under_pressure()

        assert len(evicted) == 5
        # iGPU first (LRU within the group), then CPU, then NPU last
        assert evicted[0] == "igpu-a:latest"
        assert evicted[1] == "igpu-b:latest"
        assert evicted[2] == "cpu-a:latest"
        assert evicted[3] == "npu-a-FLM"
        assert evicted[4] == "npu-b-FLM"

    @pytest.mark.asyncio
    async def test_cpu_evicted_before_npu(self, monkeypatch):
        mgr = self._pressure_pool()
        # Drop the iGPU models from candidacy
        _model(mgr, "igpu-a:latest").loaded = False
        _model(mgr, "igpu-b:latest").loaded = False
        monkeypatch.setattr(mgr._memory, "analyze_memory_pressure", lambda: 0.95, raising=True)
        with self._evict_all_patcher() as mock_evict:
            mock_evict.side_effect = _async_true
            evicted = await mgr.demote_under_pressure()

        assert evicted[0] == "cpu-a:latest"
        assert evicted[1] == "npu-a-FLM"

    @pytest.mark.asyncio
    async def test_npu_survives_when_pressure_resolves(self, monkeypatch):
        """When pressure drops after evicting the iGPU models, NPU models survive."""
        mgr = self._pressure_pool()
        # Call order: threshold check, per-candidate check (igpu-a), (igpu-b),
        # then (cpu-a) reads 0.4 -> below threshold -> loop breaks.
        readings = iter([0.95, 0.95, 0.95, 0.4])

        def _pressure() -> float:
            return next(readings)

        monkeypatch.setattr(mgr._memory, "analyze_memory_pressure", _pressure, raising=True)
        with self._evict_all_patcher() as mock_evict:
            mock_evict.side_effect = _async_true
            evicted = await mgr.demote_under_pressure()

        assert evicted == ["igpu-a:latest", "igpu-b:latest"]
        assert _model(mgr, "npu-a-FLM").loaded is True
        assert _model(mgr, "npu-b-FLM").loaded is True
        assert _model(mgr, "cpu-a:latest").loaded is True

    @pytest.mark.asyncio
    async def test_hot_never_evicted_even_if_igpu(self, monkeypatch):
        mgr = self._pressure_pool()
        _model(mgr, "igpu-a:latest").tier = ModelTierPolicy.HOT
        monkeypatch.setattr(mgr._memory, "analyze_memory_pressure", lambda: 0.95, raising=True)
        with self._evict_all_patcher() as mock_evict:
            mock_evict.side_effect = _async_true
            evicted = await mgr.demote_under_pressure()

        assert "igpu-a:latest" not in evicted  # HOT excluded despite preferred backend
        assert evicted[0] == "igpu-b:latest"  # remaining iGPU is still the first victim

    @pytest.mark.asyncio
    async def test_no_eviction_below_pressure_threshold(self, monkeypatch):
        mgr = self._pressure_pool()
        monkeypatch.setattr(mgr._memory, "analyze_memory_pressure", lambda: 0.5, raising=True)
        evicted = await mgr.demote_under_pressure()
        assert evicted == []


# ---------------------------------------------------------------------------
# Census helper contract (degraded path, fully hermetic)
# ---------------------------------------------------------------------------


def test_resident_by_backend_degraded_returns_empty_dict(monkeypatch):
    """Census returns {} (never raises) when Lemonade health is unreachable."""
    import cohezion.inference.fabric as fabric

    monkeypatch.setattr(fabric, "_get", lambda *a, **k: None)
    result = resident_by_backend("http://127.0.0.1:1")
    assert result == {}


def test_backend_enum_values_match_fabric_lanes():
    """The enum's runtime values are Lemonade's lane identifiers (StrEnum)."""
    assert Backend.NPU.value == "flm"
    assert Backend.IGPU.value == "llamacpp-vulkan"
    assert Backend.CPU.value == "llamacpp-cpu"
    assert Backend.CLOUD.value == "cloud"