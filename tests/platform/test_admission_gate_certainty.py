"""Placement inference may only RELAX a check when it is CERTAIN (user directive, 2026-10-23).

Default for every load whose placement is not certain: BOTH checks at FULL footprint, the
lemond cgroup budget (charged as CPU memory) and the system check (MemAvailable floor at the
host-cost factor, and the GTT cap). Certain means a FRESH catalog entry giving recipe and
backend (optionally overridden by the operator map), or an FLM model. A request-body
``*_backend`` field counts only on /v1/load and /api/v1/load, and only to make a load LESS
certain, never to route it away from a check.

Each class pins one finding from the prior review round (CE1-CE5 and the stall BLOCKER);
the executed counterexamples asserted the holes, these assert the safe outcome.
"""

from __future__ import annotations

import json

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform import admission_gate as ag
from cohezion.platform.admission_gate import (
    AdmissionGate,
    GateConfig,
    SystemMemory,
    request_options,
)
from cohezion.platform.admission_proxy import build_app


CHAT = "v1/chat/completions"
LOAD = "api/v1/load"

SYSTEM_INFO = {
    "recipes": {
        "llamacpp": {
            "default_backend": "cpu",
            "options": [{"name": "llamacpp_backend", "type_name": "BACKEND"}],
        },
        "sd-cpp": {
            "default_backend": "vulkan",
            "options": [{"name": "sd-cpp_backend", "type_name": "BACKEND"}],
        },
        "whispercpp": {
            "default_backend": "vulkan",
            "options": [{"name": "whispercpp_backend", "type_name": "BACKEND"}],
        },
    }
}
CATALOG: dict[str, dict[str, object]] = {
    "Gemma-4-E2B-it-GGUF": {
        "recipe": "llamacpp",
        "size": 3.81,
        "downloaded": True,
        "recipe_options": {"ctx_size": 16384, "llamacpp_backend": "cpu"},
    },
    "LFM2-8B-A1B-GGUF": {"recipe": "llamacpp", "size": 5.04, "recipe_options": {}},
    "Whisper-Large-v3-Turbo": {"recipe": "whispercpp", "size": 1.51, "recipe_options": {}},
}
# Host nearly out of memory, GTT at the desktop baseline: any load that faces the system
# check is refused; a CERTAIN cgroup load at baseline faces the cgroup check only.
LOW = SystemMemory(mem_available_gb=3.0, mem_total_gb=128.0, gtt_used_gb=0.8, gtt_total_gb=64.0)
AMPLE = SystemMemory(mem_available_gb=100.0, mem_total_gb=128.0, gtt_used_gb=0.8, gtt_total_gb=96.0)


def _gate(
    catalog: object = CATALOG,
    *,
    cgroup: tuple[float, float] | None = (2.0, 100.0),
    system: SystemMemory | None = LOW,
    system_info: object = SYSTEM_INFO,
    config: GateConfig | None = None,
) -> AdmissionGate:
    return AdmissionGate(
        config or GateConfig(),
        read_resident=lambda: [],
        read_cgroup=lambda: cgroup,
        read_catalog=catalog if callable(catalog) else (lambda: catalog),
        read_system=lambda: system,
        read_system_info=lambda: system_info,
    )


class TestControls:
    """The certain cases still relax: without these the suite could pass by refusing all."""

    def test_certain_cpu_pin_faces_the_cgroup_check_only(self) -> None:
        assert _gate().decide("Gemma-4-E2B-it-GGUF", CHAT).allow

    def test_certain_flm_faces_the_cgroup_check_only(self) -> None:
        g = _gate({"qwen3.5-4b-FLM": {"recipe": "flm", "size": 5.0, "recipe_options": {}}})
        assert g.decide("qwen3.5-4b-FLM", CHAT).allow


class TestCE1StrayBackendOnCatalogMiss:
    """CE1: on a catalog miss a foreign *_backend field must not make a GPU model cgroup-only."""

    OPTS = request_options({"model_name": "Flux-2-Klein-9B-GGUF", "llamacpp_backend": "cpu"})

    def test_refused_below_the_floor(self) -> None:
        d = _gate({}).decide("Flux-2-Klein-9B-GGUF", LOAD, self.OPTS)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_refused_with_the_cgroup_unreadable(self) -> None:
        d = _gate({}, cgroup=None).decide("Flux-2-Klein-9B-GGUF", LOAD, self.OPTS)
        assert d.allow is False, d.reason


class TestStallChargesFullFootprint:
    """BLOCKER: a stalled catalog must not price cpu-pinned large models at the GTT share."""

    @pytest.mark.parametrize(
        "model",
        ["Gemma-4-26B-A4B-it-GGUF", "Gemma-4-31B-it-GGUF", "Qwen3-Coder-30B-A3B-Instruct-GGUF"],
    )
    def test_cgroup_refuses_at_full_size(self, model: str) -> None:
        # 10 + 18..19.5 GB > 27 GB budget; at the 0.38 share it would read ~17.5 and pass.
        d = _gate(lambda: None, cgroup=(10.0, 30.0), system=AMPLE).decide(model, CHAT)
        assert d.allow is False and "cgroup" in d.reason, d.reason

    def test_stale_catalog_is_a_miss(self) -> None:
        g = _gate()
        g._catalog_at = (g._catalog_at or 0.0) - ag.CATALOG_FRESH_S - 1
        d = g.decide("Gemma-4-E2B-it-GGUF", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason


class TestCE2BackendOnlyOnLoadRoutes:
    """CE2: lemonade honours *_backend only on /v1/load; elsewhere it must change nothing."""

    def test_transcription_field_does_not_flip_a_gpu_model(self) -> None:
        d = _gate().decide(
            "Whisper-Large-v3-Turbo", "api/v1/audio/transcriptions", {"whispercpp_backend": "cpu"}
        )
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_load_route_field_cannot_route_away_from_a_check(self) -> None:
        d = _gate().decide("Whisper-Large-v3-Turbo", LOAD, {"whispercpp_backend": "cpu"})
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_chat_field_does_not_make_a_cpu_pin_uncertain(self) -> None:
        d = _gate().decide("Gemma-4-E2B-it-GGUF", CHAT, {"llamacpp_backend": "vulkan"})
        assert d.allow, d.reason


class TestEnvDefaultIsNotCertain:
    def test_unpinned_llamacpp_without_system_info_faces_both_checks(self) -> None:
        d = _gate(system_info=None).decide("LFM2-8B-A1B-GGUF", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_unpinned_llamacpp_with_system_info_cpu_is_certain(self) -> None:
        assert _gate().decide("LFM2-8B-A1B-GGUF", CHAT).allow


def _upstream() -> tuple[httpx.AsyncClient, list[str]]:
    hits: list[str] = []

    def handler(req: httpx.Request) -> httpx.Response:
        hits.append(req.url.path)
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://up")
    return client, hits


MCP_CALL = {
    "jsonrpc": "2.0",
    "id": 1,
    "method": "tools/call",
    "params": {"name": "lemonade_generate_image", "arguments": {"prompt": "x"}},
}


class TestCE3McpAutoSelect:
    """CE3: an MCP tools/call naming no model lets lemonade pick and load one. The gate
    bounds it as an uncertain load of the largest downloaded, non-resident model."""

    def _post(self, gate: AdmissionGate, body: object) -> tuple[int, list[str]]:
        client, hits = _upstream()
        with TestClient(build_app(gate, client=client)) as c:
            r = c.post(
                "/mcp", content=json.dumps(body), headers={"content-type": "application/json"}
            )
        return r.status_code, hits

    def test_refused_when_the_largest_download_does_not_fit(self) -> None:
        catalog = {
            "small-GGUF": {"recipe": "llamacpp", "size": 2.0, "downloaded": True},
            "big-GGUF": {"recipe": "llamacpp", "size": 20.0, "downloaded": True},
            "huge-GGUF": {"recipe": "llamacpp", "size": 90.0, "downloaded": False},
        }
        status, hits = self._post(_gate(catalog, cgroup=(10.0, 30.0), system=AMPLE), MCP_CALL)
        assert status == 503 and hits == []

    def test_forwarded_when_every_download_fits(self) -> None:
        catalog = {"small-GGUF": {"recipe": "llamacpp", "size": 2.0, "downloaded": True}}
        status, hits = self._post(_gate(catalog, cgroup=(10.0, 30.0), system=AMPLE), MCP_CALL)
        assert status == 200 and hits == ["/mcp"]

    def test_refused_when_no_fresh_catalog_bounds_it(self) -> None:
        status, hits = self._post(_gate(lambda: None, system=AMPLE), MCP_CALL)
        assert status == 503 and hits == []

    def test_refused_when_a_candidate_size_is_unknown(self) -> None:
        catalog = {
            "small-GGUF": {"recipe": "llamacpp", "size": 2.0, "downloaded": True},
            "mystery-model": {"recipe": "kokoro", "downloaded": True},
        }
        status, hits = self._post(_gate(catalog, system=AMPLE), MCP_CALL)
        assert status == 503 and hits == []

    def test_mcp_call_naming_a_model_is_gated_by_that_model(self) -> None:
        body = json.loads(json.dumps(MCP_CALL))
        body["params"]["arguments"]["model"] = "Gemma-4-E2B-it-GGUF"
        status, hits = self._post(_gate(system=AMPLE), body)
        assert status == 200 and hits == ["/mcp"]


class TestCE4SavedOptionsInvalidate:
    """CE4: a saved backend change is invisible until the catalog refreshes, so the model's
    placement is uncertain from the write until a catalog read that STARTED after it."""

    def test_options_write_makes_the_next_load_uncertain(self) -> None:
        reads = {"n": 0}

        def read_catalog() -> dict[str, dict[str, object]] | None:
            reads["n"] += 1
            return CATALOG if reads["n"] == 1 else None  # later refreshes stall

        g = _gate(read_catalog)
        client, _ = _upstream()
        with TestClient(build_app(g, client=client)) as c:
            c.post(
                "/api/v1/models/Gemma-4-E2B-it-GGUF/options", json={"llamacpp_backend": "vulkan"}
            )
        g.refresh_catalog()
        d = g.decide("Gemma-4-E2B-it-GGUF", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_a_refresh_that_started_after_the_write_restores_certainty(self) -> None:
        g = _gate()
        g.invalidate("Gemma-4-E2B-it-GGUF")
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow is False
        g.refresh_catalog()
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow

    def test_a_refresh_racing_the_write_does_not_restore_certainty(self) -> None:
        holder: dict[str, AdmissionGate] = {}

        def read_catalog() -> dict[str, dict[str, object]]:
            if "g" in holder:  # the write lands while this read is in flight
                holder["g"].invalidate("Gemma-4-E2B-it-GGUF")
            return CATALOG

        g = _gate(read_catalog)
        holder["g"] = g
        g.refresh_catalog()
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow is False

    def test_save_options_on_load_invalidates(self) -> None:
        g = _gate()
        client, hits = _upstream()
        with TestClient(build_app(g, client=client)) as c:
            r = c.post(
                "/api/v1/load",
                json={
                    "model_name": "Gemma-4-E2B-it-GGUF",
                    "llamacpp_backend": "cpu",
                    "save_options": True,
                },
            )
        assert r.status_code == 503 and hits == []


class TestCE5NullBackend:
    """CE5: an explicit null skips the saved pin in lemonade; the gate must not trust it."""

    def test_request_options_keeps_null(self) -> None:
        assert request_options({"llamacpp_backend": None}) == {"llamacpp_backend": None}

    def test_null_backend_on_load_is_uncertain(self) -> None:
        d = _gate().decide("Gemma-4-E2B-it-GGUF", LOAD, {"llamacpp_backend": None})
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_repeating_the_pin_on_load_stays_certain(self) -> None:
        assert _gate().decide("Gemma-4-E2B-it-GGUF", LOAD, {"llamacpp_backend": "cpu"}).allow


# -- Round 3 (2026-10-23): each class reproduces one adversarial finding as a red test. --

VK = "Vk-GGUF"  # a vulkan-pinned (certain GTT) model
VK_CATALOG: dict[str, dict[str, object]] = {
    **CATALOG,
    VK: {
        "recipe": "llamacpp",
        "size": 12.0,
        "recipe_options": {"ctx_size": 4096, "llamacpp_backend": "vulkan"},
    },
}


class TestA1BackendOnV0LoadRoutes:
    """A1: /v0/load and /api/v0/load carry a body backend too; it must not keep a cpu pin certain."""

    @pytest.mark.parametrize("route", ["api/v0/load", "v0/load"])
    def test_disagreeing_backend_on_v0_load_is_uncertain(self, route: str) -> None:
        d = _gate().decide("Gemma-4-E2B-it-GGUF", route, {"llamacpp_backend": "vulkan"})
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_v0_unload_is_not_a_load(self) -> None:
        assert _gate().decide("Gemma-4-E2B-it-GGUF", "v0/unload").reason == "not load-triggering"


class TestA2OffloadOptionsBreakGttCertainty:
    """A2: llamacpp_args / llamacpp_device can keep a vulkan load's weights on the host."""

    def _decide(self, catalog: object = VK_CATALOG, opts: dict[str, object] | None = None):
        # Full footprint 16 + ~12.6 > 27 budget; at the 0.38 host share it would fit.
        return _gate(catalog, cgroup=(16.0, 30.0), system=AMPLE).decide(VK, LOAD, opts)

    def test_control_certain_gtt_pays_only_the_host_share(self) -> None:
        assert self._decide().allow

    @pytest.mark.parametrize(
        "opts",
        [
            {"llamacpp_args": "--device none"},
            {"llamacpp_args": "--cpu-moe"},
            {"llamacpp_device": "none"},
        ],
    )
    def test_request_offload_option_is_charged_in_full(self, opts: dict[str, object]) -> None:
        d = self._decide(opts=request_options(opts))
        assert d.allow is False and "cgroup" in d.reason, d.reason

    def test_saved_device_option_is_charged_in_full(self) -> None:
        entry = json.loads(json.dumps(VK_CATALOG[VK]))
        entry["recipe_options"]["llamacpp_device"] = "none"
        d = self._decide({**VK_CATALOG, VK: entry})
        assert d.allow is False and "cgroup" in d.reason, d.reason


class TestA3CatalogMissIsRefused:
    """A3: a model missing from a FRESH catalog with no known size must not be admitted."""

    @pytest.mark.parametrize(
        ("model", "route"),
        [("my-alias", CHAT), ("user.Llama-3.3-70B-GGUF", LOAD)],
    )
    def test_refused(self, model: str, route: str) -> None:
        d = _gate(system=AMPLE).decide(model, route)
        assert d.allow is False and "not in lemonade's catalog" in d.reason, d.reason


class TestCgroupUnreadableKeepsTheFloor:
    """A certain cgroup load with the cgroup unreadable still faces the MemAvailable floor
    while GTT holds models (above the desktop baseline)."""

    def test_refused_below_the_floor_with_gtt_resident(self) -> None:
        sysmem = SystemMemory(3.0, 128.0, 10.0, 96.0)
        d = _gate(cgroup=None, system=sysmem).decide("Gemma-4-E2B-it-GGUF", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_control_gtt_at_baseline_keeps_the_fail_open(self) -> None:
        assert _gate(cgroup=None).decide("Gemma-4-E2B-it-GGUF", CHAT).allow


class TestA4CatalogRecipeBeatsTheFlmSuffix:
    def test_llamacpp_vulkan_entry_named_flm_is_not_certain_cgroup(self) -> None:
        catalog = {
            "Big-FLM": {
                "recipe": "llamacpp",
                "size": 20.0,
                "recipe_options": {"llamacpp_backend": "vulkan"},
            }
        }
        d = _gate(catalog, cgroup=None).decide("Big-FLM", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason, d.reason


class TestUnknownBackendIsUncertain:
    """Only known GPU backends are certain GTT; an unknown name falls back to lemond's default."""

    def test_unknown_backend_is_charged_in_full(self) -> None:
        catalog = {
            "Odd-GGUF": {
                "recipe": "llamacpp",
                "size": 15.0,
                "recipe_options": {"ctx_size": 4096, "llamacpp_backend": "cpu-avx512"},
            }
        }
        d = _gate(catalog, cgroup=(16.0, 30.0), system=AMPLE).decide("Odd-GGUF", CHAT)
        assert d.allow is False and "cgroup" in d.reason, d.reason


class TestA5NullCtxIsAuto:
    def test_null_ctx_is_priced_like_auto_not_the_saved_size(self) -> None:
        catalog = {
            "Small-GGUF": {
                "recipe": "llamacpp",
                "size": 3.0,
                "max_context_window": 131072,
                "recipe_options": {"ctx_size": 4096, "llamacpp_backend": "cpu"},
            }
        }
        g = _gate(catalog)
        saved = g.footprint_gb("Small-GGUF")
        auto = g.footprint_gb("Small-GGUF", {"ctx_size": -1})
        null = g.footprint_gb("Small-GGUF", request_options({"ctx_size": None}))
        assert saved is not None and auto is not None and auto > saved
        assert null == auto


class TestEmptyCatalogPricesKv:
    def test_curated_model_before_any_catalog_read_includes_kv(self) -> None:
        g = _gate(lambda: None)
        fp = g.footprint_gb("Gemma-4-26B-A4B-it-GGUF")
        assert fp is not None and fp > ag.MODEL_FOOTPRINT_GB["Gemma-4-26B-A4B-it-GGUF"] + 1.0


class TestCollectionsSizedFromComponents:
    CATALOG = {
        **CATALOG,
        # Keyed as _fetch_catalog keys it: normalized, without the "user." prefix.
        "cohezion-router": {
            "recipe": "collection.router",
            "components": ["Gemma-4-E2B-it-GGUF", "LFM2-8B-A1B-GGUF"],
            "recipe_options": {},
        },
    }

    def test_router_is_sized_from_its_largest_component(self) -> None:
        g = _gate(self.CATALOG, system=AMPLE)
        assert g.footprint_gb("user.cohezion-router") == max(
            g.footprint_gb("Gemma-4-E2B-it-GGUF") or 0.0, g.footprint_gb("LFM2-8B-A1B-GGUF") or 0.0
        )
        assert g.decide("user.cohezion-router", CHAT).allow

    def test_router_with_an_unknown_component_is_refused(self) -> None:
        catalog = json.loads(json.dumps(self.CATALOG))
        catalog["cohezion-router"]["components"].append("ghost-GGUF")
        d = _gate(catalog, system=AMPLE).decide("user.cohezion-router", CHAT)
        assert d.allow is False and "has not been read" not in d.reason, d.reason


class TestA9TruncatedWalkFailsClosed:
    def test_padded_batch_is_refused(self) -> None:
        call = json.loads(json.dumps(MCP_CALL))
        call["params"]["arguments"]["model"] = "Whisper-Large-v3-Turbo"
        pad = [
            {"jsonrpc": "2.0", "id": i, "method": "tools/list"} for i in range(ag._WALK_MAX_NODES)
        ]
        client, hits = _upstream()
        with TestClient(build_app(_gate(), client=client)) as c:
            r = c.post("/mcp", json=[*pad, call])
        assert r.status_code == 503 and hits == []

    def test_control_unpadded_call_is_refused_by_the_model_check(self) -> None:
        call = json.loads(json.dumps(MCP_CALL))
        call["params"]["arguments"]["model"] = "Whisper-Large-v3-Turbo"
        client, hits = _upstream()
        with TestClient(build_app(_gate(), client=client)) as c:
            r = c.post("/mcp", json=[call])
        assert hits == []
        assert r.status_code == 503 and "MemAvailable" in r.json()["error"]["message"]


def _proxy_call(gate: AdmissionGate, method: str, path: str, body: object = None, during=None):
    def handler(req: httpx.Request) -> httpx.Response:
        if during is not None:
            during()
        return httpx.Response(200, json={"ok": True})

    client = httpx.AsyncClient(transport=httpx.MockTransport(handler), base_url="http://up")
    with TestClient(build_app(gate, client=client)) as c:
        return c.request(method, path, json=body)


class TestA7ConfigWritesInvalidate:
    @pytest.mark.parametrize(
        ("method", "path"),
        [
            ("POST", "/v0/models/Gemma-4-E2B-it-GGUF/options"),
            ("DELETE", "/v0/models/Gemma-4-E2B-it-GGUF/options"),
            ("POST", "/api/v0/models/Gemma-4-E2B-it-GGUF/options"),
        ],
    )
    def test_options_write_on_every_prefix_invalidates(self, method: str, path: str) -> None:
        g = _gate()
        _proxy_call(g, method, path, {"llamacpp_backend": "vulkan"} if method == "POST" else None)
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow is False

    @pytest.mark.parametrize(
        "path", ["/v1/models/register", "/api/v0/models/register", "/internal/set", "/v1/pull"]
    )
    def test_config_write_invalidates_every_placement(self, path: str) -> None:
        g = _gate()
        _proxy_call(g, "POST", path, {"model_name": "user.Other-GGUF", "recipe": "llamacpp"})
        for model in ("Gemma-4-E2B-it-GGUF", "LFM2-8B-A1B-GGUF"):
            d = g.decide(model, CHAT)
            assert d.allow is False and "MemAvailable" in d.reason, d.reason

    def test_a_later_refresh_restores_certainty(self) -> None:
        g = _gate()
        _proxy_call(g, "POST", "/internal/set", {"llamacpp": {"backend": "vulkan"}})
        g.refresh_catalog()
        assert g.decide("LFM2-8B-A1B-GGUF", CHAT).allow

    def test_get_does_not_invalidate(self) -> None:
        g = _gate()
        _proxy_call(g, "GET", "/v0/models/Gemma-4-E2B-it-GGUF/options")
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow


class TestA8InvalidationOutlivesAnInFlightRefresh:
    def test_refresh_during_the_write_does_not_restore_certainty(self) -> None:
        g = _gate()
        _proxy_call(
            g,
            "POST",
            "/api/v1/models/Gemma-4-E2B-it-GGUF/options",
            {"llamacpp_backend": "vulkan"},
            during=g.refresh_catalog,
        )
        assert g.decide("Gemma-4-E2B-it-GGUF", CHAT).allow is False

    def test_global_write_during_refresh(self) -> None:
        g = _gate()
        _proxy_call(g, "POST", "/internal/set", {"x": 1}, during=g.refresh_catalog)
        assert g.decide("LFM2-8B-A1B-GGUF", CHAT).allow is False


class TestWalkLimitIgnoresScalars:
    """A scalar cannot hold a model key: long input/token arrays must not trip the A9 limit."""

    @pytest.mark.parametrize(
        "body",
        [
            {"model": "Gemma-4-E2B-it-GGUF", "input": ["x"] * 25000},
            {"model": "Gemma-4-E2B-it-GGUF", "prompt": list(range(32768))},
        ],
    )
    def test_large_scalar_array_is_forwarded(self, body: dict[str, object]) -> None:
        client, hits = _upstream()
        with TestClient(build_app(_gate(), client=client)) as c:
            r = c.post("/v1/embeddings", json=body)
        assert r.status_code == 200 and hits == ["/v1/embeddings"], r.text


class TestNonConfigInternalWrites:
    @pytest.mark.parametrize("path", ["/internal/telemetry/flush", "/internal/pin"])
    def test_do_not_invalidate(self, path: str) -> None:
        g = _gate()
        _proxy_call(g, "POST", path, {})
        assert g.decide("LFM2-8B-A1B-GGUF", CHAT).allow


class TestNestedCollections:
    def test_cycle_is_unknown_not_a_recursion_error(self) -> None:
        catalog = {
            "a": {"recipe": "collection.router", "components": ["b"]},
            "b": {"recipe": "collection.router", "components": ["a"]},
        }
        d = _gate(catalog, system=AMPLE).decide("a", CHAT)
        assert d.allow is False, d.reason
