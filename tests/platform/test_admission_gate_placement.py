"""Review findings F1-F12 (2026-10-23) on the GTT-aware gate: placement, pricing, floor.

Fixtures are copied from the live box on 2026-10-23 (never fetched inside a test):
  - GET :13315/api/v1/system-info  recipes[*].default_backend and the BACKEND option name.
  - GET :13315/api/v1/models?show_all=true  catalog entries (size, recipe, recipe_options).
Each test names the finding it pins. Measurement behind the host-share constant: Vulkan
Gemma-4-E2B-it-GGUF put anon 0.96 + file_mapped 1.26 = 2.22 GB in the lemond cgroup for a
5.84 GB footprint (GTT carried the rest).
"""

from __future__ import annotations

import httpx
import pytest
from fastapi.testclient import TestClient

from cohezion.platform import admission_gate as ag
from cohezion.platform.admission_gate import (
    AdmissionGate,
    GateConfig,
    SystemMemory,
    model_placement,
    parse_recipe_backends,
    request_options,
)
from cohezion.platform.admission_proxy import build_app


CHAT = "v1/chat/completions"
LOAD = "api/v1/load"

# Trimmed from live /api/v1/system-info (2026-10-23).
SYSTEM_INFO = {
    "recipes": {
        "llamacpp": {
            "default_backend": "cpu",
            "options": [{"name": "llamacpp_backend", "type_name": "BACKEND"}],
        },
        "llamacpp-hrx": {"default_backend": "hrx", "options": []},
        "flm": {"default_backend": "npu", "options": []},
        "sd-cpp": {
            "default_backend": "vulkan",
            "options": [{"name": "sd-cpp_backend", "type_name": "BACKEND"}],
        },
        "whispercpp": {
            "default_backend": "vulkan",
            "options": [{"name": "whispercpp_backend", "type_name": "BACKEND"}],
        },
        "vllm": {
            "default_backend": "rocm",
            "options": [{"name": "vllm_backend", "type_name": "BACKEND"}],
        },
        "kokoro": {"default_backend": "cpu", "options": []},
        "ryzenai-llm": {"options": []},  # no default_backend published
    }
}
RECIPES = parse_recipe_backends(SYSTEM_INFO)

# Trimmed from the live catalog (2026-10-23).
CATALOG: dict[str, dict[str, object]] = {
    "Gemma-4-E2B-it-GGUF": {
        "recipe": "llamacpp",
        "size": 3.81,
        "recipe_options": {"ctx_size": 16384, "llamacpp_backend": "cpu"},
    },
    "LFM2-8B-A1B-GGUF": {"recipe": "llamacpp", "size": 5.04, "recipe_options": {}},
    "Qwen3-Coder-30B-A3B-Instruct-GGUF": {
        "recipe": "llamacpp",
        "size": 17.3,
        "recipe_options": {"ctx_size": 16384},
        "max_context_window": 262144,
    },
    "Bonsai-8B-HRX": {"recipe": "llamacpp-hrx", "size": 1.08, "recipe_options": {}},
    "Z-Image-Turbo": {
        "recipe": "sd-cpp",
        "size": 19.3,
        "recipe_options": {"cfg_scale": 1.0, "height": 1024, "steps": 9, "width": 1024},
    },
    "Whisper-Large-v3-Turbo": {"recipe": "whispercpp", "size": 1.51, "recipe_options": {}},
    "LMX-Omni-52B-Halo": {"recipe": "collection.omni", "size": 44.77, "recipe_options": {}},
    "deepseek-r1-0528-8b-FLM": {
        "recipe": "flm",
        "size": 5.6,
        "recipe_options": {"ctx_size": 16384},
    },
    "kokoro-v1": {"recipe": "kokoro", "size": 0.34, "recipe_options": {}},
}

HEALTHY_GTT = SystemMemory(100.0, 122.8, gtt_used_gb=1.0, gtt_total_gb=96.0)


class _Probe:
    """A system reader that counts its calls."""

    def __init__(self, reading: SystemMemory | None) -> None:
        self.reading = reading
        self.calls = 0

    def __call__(self) -> SystemMemory | None:
        self.calls += 1
        return self.reading


def _gate(
    system: SystemMemory | None,
    cgroup: tuple[float, float] | None = (2.0, 30.0),
    *,
    config: GateConfig | None = None,
    system_info: dict[str, object] | None = SYSTEM_INFO,
    sizes: dict[str, float] | None = None,
) -> tuple[AdmissionGate, _Probe]:
    probe = _Probe(system)
    gate = AdmissionGate(
        config=config or GateConfig(),
        read_resident=lambda: [],
        read_cgroup=lambda: cgroup,
        read_catalog=lambda: CATALOG,
        read_system_info=lambda: system_info,
        read_system=probe,
        **({"read_size_gb": lambda m: sizes.get(m)} if sizes is not None else {}),
    )
    return gate, probe


class TestF1RequestBodyBackend:
    """F1: /v1/load's llamacpp_backend overrides the saved pin; the gate must see it."""

    def test_request_options_extracts_backend_and_ctx(self) -> None:
        body = {"model_name": "x", "llamacpp_backend": "Vulkan", "ctx_size": 65536, "n": 1}
        assert request_options(body) == {"llamacpp_backend": "vulkan", "ctx_size": 65536}
        assert request_options([body]) == {}  # only a top-level object carries load options

    def test_body_backend_beats_a_cpu_catalog_pin(self) -> None:
        # The reviewer's counterexample: pin 'cpu', body 'vulkan', MemAvailable 18, GTT 60/96.
        g, probe = _gate(SystemMemory(18.0, 122.8, 60.0, 96.0))
        d = g.decide("Gemma-4-E2B-it-GGUF", LOAD, {"llamacpp_backend": "vulkan"})
        assert d.allow is False and "MemAvailable" in d.reason
        assert probe.calls == 1

    def test_without_the_body_the_cpu_pin_is_cgroup_placed(self) -> None:
        entry = CATALOG["Gemma-4-E2B-it-GGUF"]
        assert model_placement("Gemma-4-E2B-it-GGUF", entry, GateConfig(), RECIPES) == "cgroup"
        assert (
            model_placement(
                "Gemma-4-E2B-it-GGUF", entry, GateConfig(), RECIPES, {"llamacpp_backend": "vulkan"}
            )
            == "gtt"
        )

    @pytest.mark.parametrize("value", ["", "auto"])
    def test_empty_or_auto_body_backend_is_absent(self, value: str) -> None:
        entry = CATALOG["Gemma-4-E2B-it-GGUF"]
        opts = {"llamacpp_backend": value}
        assert model_placement("Gemma-4-E2B-it-GGUF", entry, GateConfig(), RECIPES, opts) == (
            "cgroup"
        )

    def test_larger_body_ctx_size_raises_the_footprint(self) -> None:
        g, _ = _gate(HEALTHY_GTT)
        name = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
        saved = g.footprint_gb(name)
        bigger = g.footprint_gb(name, {"ctx_size": 131072})
        smaller = g.footprint_gb(name, {"ctx_size": 4096})
        assert saved is not None and bigger is not None
        assert bigger > saved  # KV priced from the larger request ctx
        assert smaller == saved  # never priced below the saved ctx

    def test_proxy_passes_the_body_to_the_gate(self) -> None:
        # Consumption: a vulkan /v1/load under pressure must be refused through the proxy.
        # GTT is at the desktop baseline, so the same model on its saved cpu pin faces the
        # cgroup check only; the body alone flips the decision.
        g, _ = _gate(SystemMemory(18.0, 122.8, 0.84, 96.0))
        seen: list[httpx.Request] = []

        def handler(request: httpx.Request) -> httpx.Response:
            seen.append(request)
            return httpx.Response(200, json={"ok": True})

        client = httpx.AsyncClient(
            transport=httpx.MockTransport(handler), base_url="http://upstream.test"
        )
        with TestClient(build_app(g, client=client)) as c:
            refused = c.post(
                "/api/v1/load",
                json={"model_name": "Gemma-4-E2B-it-GGUF", "llamacpp_backend": "vulkan"},
            )
            plain = c.post("/api/v1/load", json={"model_name": "Gemma-4-E2B-it-GGUF"})
        assert refused.status_code == 503, refused.text
        assert plain.status_code == 200  # same model, saved cpu pin: cgroup check only
        assert len(seen) == 1


class TestF2F5F10PlacementFromBackend:
    """F2/F5/F10: placement follows the backend, not the recipe family."""

    @pytest.mark.parametrize(
        "model",
        [
            "Bonsai-8B-HRX",
            "Z-Image-Turbo",
            "Whisper-Large-v3-Turbo",
            "LMX-Omni-52B-Halo",  # collection recipe: unknown backend fails closed
        ],
    )
    def test_gpu_default_recipes_are_gtt(self, model: str) -> None:
        assert model_placement(model, CATALOG[model], GateConfig(), RECIPES) == "gtt"

    @pytest.mark.parametrize("model", ["deepseek-r1-0528-8b-FLM", "kokoro-v1"])
    def test_cpu_and_npu_recipes_stay_cgroup(self, model: str) -> None:
        assert model_placement(model, CATALOG[model], GateConfig(), RECIPES) == "cgroup"

    def test_unknown_recipe_without_system_info_fails_closed(self) -> None:
        entry = CATALOG["Z-Image-Turbo"]
        assert model_placement("Z-Image-Turbo", entry, GateConfig(), {}) == "gtt"
        hrx = CATALOG["Bonsai-8B-HRX"]
        assert model_placement("Bonsai-8B-HRX", hrx, GateConfig(), {}) == "gtt"

    def test_non_llamacpp_pin_key_comes_from_system_info(self) -> None:
        entry = {"recipe": "sd-cpp", "recipe_options": {"sd-cpp_backend": "cpu"}}
        assert model_placement("sd", entry, GateConfig(), RECIPES) == "cgroup"
        assert model_placement("sd", entry, GateConfig(), RECIPES, {"sd-cpp_backend": "rocm"}) == (
            "gtt"
        )

    def test_reviewer_counterexample_flux_is_refused_below_the_floor(self) -> None:
        g, probe = _gate(SystemMemory(10.0, 122.8, 80.0, 96.0))
        d = g.decide("Z-Image-Turbo", "api/v1/images/generations")
        assert d.allow is False
        assert probe.calls == 1

    def test_hrx_counterexample_is_refused(self) -> None:
        g, _ = _gate(SystemMemory(10.0, 122.8, 80.0, 96.0))
        assert g.decide("Bonsai-8B-HRX", CHAT).allow is False


class TestF6F11FollowLemonadeDefault:
    """F6/F11: lemonade's published llamacpp default beats the env default."""

    def test_unpinned_llamacpp_follows_system_info_vulkan(self) -> None:
        recipes = parse_recipe_backends(
            {"recipes": {"llamacpp": {"default_backend": "vulkan", "options": []}}}
        )
        entry = CATALOG["LFM2-8B-A1B-GGUF"]
        assert model_placement("LFM2-8B-A1B-GGUF", entry, GateConfig(), recipes) == "gtt"

    def test_env_default_applies_only_without_system_info(self) -> None:
        entry = CATALOG["LFM2-8B-A1B-GGUF"]
        assert model_placement("LFM2-8B-A1B-GGUF", entry, GateConfig(), {}) == "cgroup"
        assert (
            model_placement("LFM2-8B-A1B-GGUF", entry, GateConfig(gguf_backend="vulkan"), {})
            == "gtt"
        )

    def test_gate_reads_system_info_with_the_catalog(self) -> None:
        info = {"recipes": {"llamacpp": {"default_backend": "vulkan", "options": []}}}
        g, probe = _gate(SystemMemory(18.0, 122.8, 1.0, 96.0), system_info=info)
        d = g.decide("LFM2-8B-A1B-GGUF", CHAT)
        assert probe.calls == 1
        assert d.allow is False and "MemAvailable" in d.reason

    def test_injected_catalog_without_system_info_reader_makes_no_network_call(self) -> None:
        def boom() -> dict[str, object]:
            raise AssertionError("must not fetch system-info when the catalog is injected")

        with pytest.MonkeyPatch.context() as mp:
            mp.setattr(AdmissionGate, "_fetch_system_info", lambda self: boom())
            g = AdmissionGate(
                config=GateConfig(),
                read_resident=lambda: [],
                read_cgroup=lambda: (2.0, 30.0),
                read_catalog=lambda: CATALOG,
                read_system=lambda: HEALTHY_GTT,
            )
            assert g.decide("deepseek-r1-0528-8b-FLM", CHAT).allow is True


class TestF3F7HostShare:
    """F3/F7: a GTT load is charged only its measured host-side share in the cgroup."""

    def test_share_traces_to_the_measurement(self) -> None:
        assert pytest.approx((0.96 + 1.26) / 5.84, abs=0.01) == ag.GTT_HOST_SHARE

    def test_mid_size_vulkan_load_is_not_refused_for_cgroup_headroom(self) -> None:
        # Live working set 19.49 GB. gpt-oss-20b (15.6 GB footprint) on vulkan:
        # full charge 35.1 > 27 (old refusal); share 19.49 + 5.9 = 25.4 <= 27.
        cfg = GateConfig(backend_overrides=(("gpt-oss-20b-mxfp4-gguf", "vulkan"),))
        g, _ = _gate(
            HEALTHY_GTT, cgroup=(19.49, 30.0), config=cfg, sizes={"gpt-oss-20b-mxfp4-GGUF": 15.6}
        )
        d = g.decide("gpt-oss-20b-mxfp4-GGUF", CHAT)
        assert d.allow is True, d.reason

    def test_large_vulkan_load_still_needs_its_host_share(self) -> None:
        # 19.49 + 0.38 * 20.1 = 27.1 > 27: the measured share still refuses this one.
        cfg = GateConfig(backend_overrides=(("qwen3-coder-30b-a3b-instruct-gguf", "vulkan"),))
        name = "Qwen3-Coder-30B-A3B-Instruct-GGUF"
        g, _ = _gate(HEALTHY_GTT, cgroup=(19.49, 30.0), config=cfg, sizes={name: 20.1})
        d = g.decide(name, CHAT)
        assert d.allow is False and "cgroup" in d.reason

    def test_inflight_gtt_reservation_counts_at_its_share_in_the_cgroup(self) -> None:
        # GTT load of 10 GB reserved -> 3.8 GB host share. FLM 10 GB on (14, 30):
        # 14 + 3.8 + 10 = 27.8 > 27 refused; ignoring the GTT reservation gives 24 (admit).
        cfg = GateConfig(backend_overrides=(("big-gguf", "vulkan"),))
        g, _ = _gate(
            HEALTHY_GTT, cgroup=(14.0, 30.0), config=cfg, sizes={"big-GGUF": 10.0, "x-FLM": 10.0}
        )
        assert g.decide("big-GGUF", CHAT).allow is True
        d = g.decide("x-FLM", CHAT)
        assert d.allow is False and "cgroup" in d.reason


class TestF9FloorHostCost:
    """F9: the floor prices a GTT load at footprint x (1 + host share), not footprint."""

    def test_reviewer_counterexample_is_refused(self) -> None:
        # MemAvailable 22, E2B footprint 5.84: 22 - 5.84 = 16.2 (old admit);
        # 22 - 5.84 * 1.38 = 13.9 < 16 refused.
        cfg = GateConfig(backend_overrides=(("gemma-4-e2b-it-gguf", "vulkan"),))
        g, _ = _gate(
            SystemMemory(22.0, 122.8, 1.0, 96.0), config=cfg, sizes={"Gemma-4-E2B-it-GGUF": 5.84}
        )
        d = g.decide("Gemma-4-E2B-it-GGUF", CHAT)
        assert d.allow is False and "MemAvailable" in d.reason


class TestF4F8FloorForCgroupLoads:
    """F4/F8: once GTT holds models outside the cgroup, cgroup loads face the floor too."""

    def test_cpu_load_with_resident_gtt_is_refused_below_the_floor(self) -> None:
        g, probe = _gate(SystemMemory(18.0, 122.8, 60.0, 96.0), sizes={"cpu-GGUF": 20.1})
        d = g.decide("cpu-GGUF", CHAT)
        assert probe.calls == 1
        assert d.allow is False and "MemAvailable" in d.reason

    def test_flm_load_with_resident_gtt_is_refused_below_the_floor(self) -> None:
        g, _ = _gate(SystemMemory(5.0, 122.8, 80.0, 96.0))
        assert g.decide("deepseek-r1-0528-8b-FLM", CHAT).allow is False

    def test_cgroup_load_at_desktop_gtt_baseline_keeps_the_cgroup_check_only(self) -> None:
        # GTT at the measured desktop baseline (0.84): the 2026-10-21 decision stands.
        g, _ = _gate(SystemMemory(18.0, 122.8, 0.84, 96.0), sizes={"cpu-GGUF": 5.0})
        assert g.decide("cpu-GGUF", CHAT).allow is True

    def test_cgroup_load_fails_open_when_system_memory_is_unreadable(self) -> None:
        g, _ = _gate(None, sizes={"cpu-GGUF": 5.0})
        assert g.decide("cpu-GGUF", CHAT).allow is True

    def test_gtt_reservation_in_flight_turns_the_floor_on(self) -> None:
        # The GTT reading is still at baseline, but a 30 GB GPU load was just admitted and
        # is loading: its bytes are coming, so the next cgroup load must face the floor.
        cfg = GateConfig(backend_overrides=(("big-gguf", "vulkan"),))
        g, _ = _gate(
            SystemMemory(60.0, 122.8, 0.84, 96.0),
            cgroup=(0.0, 100.0),
            config=cfg,
            sizes={"big-GGUF": 30.0, "cpu-GGUF": 10.0},
        )
        assert g.decide("big-GGUF", CHAT).allow is True  # 60 - 30 * 1.38 = 18.6 >= 16
        refused = g.decide("cpu-GGUF", CHAT)  # 60 - 41.4 - 10 = 8.6 < 16
        assert refused.allow is False and "MemAvailable" in refused.reason


class TestF12LegacyFloor:
    def test_legacy_floor_name_is_honoured_as_the_larger_value(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("COHEZION_ADMISSION_MEMAVAIL_FLOOR_GB", raising=False)
            mp.setenv("COHEZION_ADMISSION_FLOOR_GB", "25.0")
            assert GateConfig.from_env().mem_available_floor_gb == 25.0
            mp.setenv("COHEZION_ADMISSION_MEMAVAIL_FLOOR_GB", "30")
            assert GateConfig.from_env().mem_available_floor_gb == 30.0
            mp.setenv("COHEZION_ADMISSION_MEMAVAIL_FLOOR_GB", "12")
            assert GateConfig.from_env().mem_available_floor_gb == 25.0

    def test_default_floor_without_either_name(self) -> None:
        with pytest.MonkeyPatch.context() as mp:
            mp.delenv("COHEZION_ADMISSION_MEMAVAIL_FLOOR_GB", raising=False)
            mp.delenv("COHEZION_ADMISSION_FLOOR_GB", raising=False)
            assert GateConfig.from_env().mem_available_floor_gb == ag.DEFAULT_MEMAVAIL_FLOOR_GB
