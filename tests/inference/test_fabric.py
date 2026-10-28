"""Unified-fabric accounting tests — admission must REFUSE, never load blind.

The dangerous failure here mirrors hotswap's (HS1-HS7): not an exception but
loading anyway. An mmap load that "succeeds" still page-storms the box, and on
the iGPU the GTT aperture is the documented 2026-09-14 OOM channel. So the
discriminating tests assert the gate refuses: an implementation that skipped a
check either calls nothing (and must still refuse) or would call load (which
this suite never stubs as reachable — `_get` is the only HTTP seam and every
test drives it explicitly).

No test performs real HTTP: the autouse fixture replaces `fabric._get` with a
boom-stub that only answers from the canned `http` map, and `MemAvailable` is
stubbed at `fabric._mem_available_gb`.
"""

from __future__ import annotations

import pytest

from cohezion.inference import fabric
from cohezion.inference.fabric import (
    BACKEND_BUDGETS,
    Backend,
    admission_ok,
    backend_for_model,
    resident_by_backend,
)


BASE = "http://localhost:13305"


@pytest.fixture(autouse=True)
def _no_real_http(monkeypatch):
    """Fail loudly on any unstubbed network seam, in tests and module alike."""

    def _boom(url, timeout=fabric.DEFAULT_TIMEOUT_S):  # pragma: no cover
        raise AssertionError(f"unstubbed HTTP call in fabric test: {url}")

    monkeypatch.setattr(fabric, "_get", _boom)
    monkeypatch.setattr(fabric, "_mem_available_gb", lambda: 100.0)


@pytest.fixture()
def http(monkeypatch):
    """Canned HTTP answers keyed by URL suffix; boom on anything else.

    Defaults: healthy empty fleet, a small catalog, plenty of RAM.
    Tests mutate the returned dict to script each scenario.
    """

    state = {
        "health": {"all_models_loaded": []},
        "models": {
            "data": [
                {"id": "Gemma-4-E4B-it-GGUF", "size": 5.56},
                {"id": "Qwen3-Coder-30B-A3B-Instruct-GGUF", "size": 22.10},
                {"id": "Phi-4-mini-3.8B-CPU-32T", "size": 2.8},
                {"id": "llama3.2-1b-FLM", "size": 1.2},
            ]
        },
        "mem_gb": 100.0,
    }

    def _stub(url, timeout=fabric.DEFAULT_TIMEOUT_S):
        if url.endswith("/api/v1/health"):
            return state["health"]
        if url.endswith("/api/v1/models"):
            return state["models"]
        raise AssertionError(f"unstubbed HTTP call in fabric test: {url}")

    monkeypatch.setattr(fabric, "_get", _stub)
    monkeypatch.setattr(fabric, "_mem_available_gb", lambda: state["mem_gb"])
    return state


def _residents(*names: str) -> dict:
    """Health payload with every named model resident and idle."""
    return {
        "all_models_loaded": [{"model_name": n, "loaded": True, "is_busy": False} for n in names]
    }


# ── backend_for_model: classification rules ────────────────────────────────


class TestClassification:
    def test_flm_suffix_routes_to_npu(self):
        assert backend_for_model("deepseek-r1-0528-8b-FLM") is Backend.NPU
        assert backend_for_model("llama3.2-1b-FLM") is Backend.NPU
        assert backend_for_model("qwen3.6-moe-35b-a3b-FLM") is Backend.NPU

    def test_flm_tag_anywhere_routes_to_npu(self):
        """The convention is the FLM tag, not one exact suffix spelling."""
        assert backend_for_model("gemma3-4b-FLM-mtp") is Backend.NPU
        assert backend_for_model("FLM-Qwen3-4b") is Backend.NPU

    def test_cloud_suffix_routes_to_cloud(self):
        assert backend_for_model("deepseek-v4-pro:cloud") is Backend.CLOUD
        assert backend_for_model("glm-5.3-flash:cloud") is Backend.CLOUD
        assert backend_for_model("qwen3.5-397b-cloud") is Backend.CLOUD

    def test_cpu_marker_routes_to_cpu(self):
        assert backend_for_model("Phi-4-mini-3.8B-CPU-32T") is Backend.CPU
        assert backend_for_model("DeepSeek-R1-Distill-Qwen-8B-CPU") is Backend.CPU

    def test_gguf_and_unmarked_names_fall_to_igpu(self):
        assert backend_for_model("Qwen3-Coder-30B-A3B-Instruct-GGUF") is Backend.IGPU
        assert backend_for_model("Gemma-4-E4B-it-GGUF") is Backend.IGPU
        assert backend_for_model("Gemma-4-31B-it-GGUF") is Backend.IGPU

    def test_cloud_precedes_cpu_marker(self):
        """:cloud wins over any embedded lane marker — it loads nothing locally."""
        assert backend_for_model("Phi-4-mini-CPU-32T:cloud") is Backend.CLOUD

    def test_flm_precedes_cloud_and_cpu(self):
        """A name cannot be both FLM and cloud; the FLM tag is the NPU convention."""
        assert backend_for_model("llama3.2-1b-FLM-CPU") is Backend.NPU

    def test_empty_name_falls_to_igpu_not_crash(self):
        assert backend_for_model("") is Backend.IGPU


# ── resident_by_backend ────────────────────────────────────────────────────


class TestResidentByBackend:
    def test_groups_by_backend(self, http):
        http["health"] = _residents(
            "llama3.2-1b-FLM", "Gemma-4-E4B-it-GGUF", "Phi-4-mini-3.8B-CPU-32T"
        )
        got = resident_by_backend(BASE)
        assert got[Backend.NPU] == ["llama3.2-1b-FLM"]
        assert got[Backend.IGPU] == ["Gemma-4-E4B-it-GGUF"]
        assert got[Backend.CPU] == ["Phi-4-mini-3.8B-CPU-32T"]
        assert Backend.CLOUD not in got

    def test_degraded_health_returns_empty_dict(self, monkeypatch):
        monkeypatch.setattr(fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: None)
        assert resident_by_backend(BASE) == {}

    def test_never_raises_on_malformed_health(self, monkeypatch):
        monkeypatch.setattr(
            fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: {"nope": 1}
        )
        assert resident_by_backend(BASE) == {}

    def test_skips_unloaded_and_nameless_entries(self, http):
        http["health"] = {
            "all_models_loaded": [
                {"model_name": "ghost", "loaded": False},
                {"loaded": True},
                {"model_name": "Gemma-4-E4B-it-GGUF", "loaded": True},
                "garbage",
            ]
        }
        assert resident_by_backend(BASE) == {Backend.IGPU: ["Gemma-4-E4B-it-GGUF"]}


# ── budgets table invariants ───────────────────────────────────────────────


class TestBudgets:
    def test_budget_values_match_the_incident_record(self):
        assert BACKEND_BUDGETS[Backend.NPU].max_resident == 5
        assert BACKEND_BUDGETS[Backend.NPU].budget_gb == 16.0  # FLM SRAM cap ~15.6G
        assert BACKEND_BUDGETS[Backend.IGPU].max_resident == 2
        assert BACKEND_BUDGETS[Backend.IGPU].budget_gb == 48.0  # GTT gate
        assert BACKEND_BUDGETS[Backend.CPU].max_resident == 3
        assert BACKEND_BUDGETS[Backend.CPU].budget_gb == 24.0

    def test_cloud_has_no_budget_line(self):
        assert Backend.CLOUD not in BACKEND_BUDGETS


# ── admission: happy paths ─────────────────────────────────────────────────


class TestAdmissionHappyPath:
    def test_igpu_load_admitted_on_empty_fleet(self, http):
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert ok, why
        assert "IGPU" in why

    def test_already_resident_is_noop_even_over_cap(self, http):
        """An already-resident model needs no slot and no bytes — mirrors HS1."""
        http["health"] = _residents("Gemma-4-E4B-it-GGUF", "Qwen3-Coder-30B-A3B-Instruct-GGUF")
        http["mem_gb"] = 10.0  # would fail the RAM floor if this were a fresh load
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert ok and "already resident" in why

    def test_cloud_admission_never_touches_http(self, monkeypatch):
        """Cloud loads nothing locally: the boom-stub proves no HTTP happens."""

        def _boom(url, timeout=fabric.DEFAULT_TIMEOUT_S):  # pragma: no cover
            raise AssertionError(f"cloud admission must not make HTTP calls: {url}")

        monkeypatch.setattr(fabric, "_get", _boom)
        ok, why = admission_ok("deepseek-v4-pro:cloud", 8192)
        assert ok and "cloud" in why


# ── admission: per-backend count cap ───────────────────────────────────────


class TestAdmissionCap:
    def test_igpu_cap_refusal_at_2_resident(self, http):
        http["health"] = _residents("Gemma-4-E4B-it-GGUF", "Qwen3-Coder-30B-A3B-Instruct-GGUF")
        ok, why = admission_ok("Gemma-4-31B-it-GGUF", 8192)
        assert not ok
        assert "IGPU residency cap" in why and "2/2" in why

    def test_cpu_cap_refusal_at_3_resident(self, http):
        http["health"] = _residents(
            "Phi-4-mini-3.8B-CPU-32T",
            "DeepSeek-R1-Distill-Qwen-8B-CPU",
            "qwen3-coder-30b-CPU",
        )
        http["models"]["data"].append({"id": "qwen3-coder-30b-CPU", "size": 3.0})
        ok, why = admission_ok("another-model-CPU", 4096)
        assert not ok
        assert "CPU residency cap" in why and "3/3" in why

    def test_npu_cap_refusal_at_5_resident(self, http):
        http["health"] = _residents(*[f"m{i}-FLM" for i in range(1, 6)])
        ok, why = admission_ok("llama3.2-1b-FLM", 4096)
        assert not ok
        assert "NPU residency cap" in why and "5/5" in why

    def test_full_igpu_does_not_block_a_cpu_load(self, http):
        """Budgets are per-backend lines over one pool, not shared compartments."""
        http["health"] = _residents("Gemma-4-E4B-it-GGUF", "Qwen3-Coder-30B-A3B-Instruct-GGUF")
        http["mem_gb"] = 40.0
        ok, why = admission_ok("Phi-4-mini-3.8B-CPU-32T", 4096)
        assert ok, why

    def test_cap_counts_only_same_backend_residents(self, http):
        http["health"] = _residents(
            "Gemma-4-E4B-it-GGUF",
            "Qwen3-Coder-30B-A3B-Instruct-GGUF",
            "llama3.2-1b-FLM",
            "Phi-4-mini-3.8B-CPU-32T",
        )
        # IGPU is full (2/2), but an NPU load only sees 1/5 NPU residents.
        http["models"]["data"].append({"id": "qwen3.5-4b-FLM", "size": 2.5})
        ok, why = admission_ok("qwen3.5-4b-FLM", 4096)
        assert ok, why


# ── admission: per-backend byte budget ─────────────────────────────────────


class TestAdmissionBudget:
    def test_igpu_budget_refusal_when_weights_do_not_fit(self, http):
        http["mem_gb"] = 100.0  # RAM floor would pass; the BUDGET gate must refuse
        # One 30G iGPU resident: cap is 1/2 (not full) but only 18G of line remains.
        http["models"]["data"].append({"id": "BIG-IGPU-GGUF", "size": 30.0})
        http["health"] = _residents("BIG-IGPU-GGUF")
        ok, why = admission_ok("Qwen3-Coder-30B-A3B-Instruct-GGUF", 16384)
        assert not ok
        assert "IGPU budget exceeded" in why
        assert "KV" in why  # reason names the weights+KV accounting

    def test_kv_overhead_grows_with_ctx(self, http):
        """+KV is prorated: the same weights must cost more at MAX_CTX."""
        http["mem_gb"] = 100.0
        # 22.1G weights (>10G -> KV base 3.0); one 24.0G resident -> room 24.0.
        http["models"]["data"].append({"id": "FILLER-IGPU-GGUF", "size": 24.0})
        http["health"] = _residents("FILLER-IGPU-GGUF")
        # ctx 1024: KV = 3.0 * 0.25 = 0.75 -> needed 22.85 <= 24.0 -> FITS
        ok_small, why_small = admission_ok("Qwen3-Coder-30B-A3B-Instruct-GGUF", 1024)
        assert ok_small, why_small
        # ctx 16384: KV = 3.0 -> needed 25.1 > 24.0 -> REFUSED by the same line
        ok_big, why = admission_ok("Qwen3-Coder-30B-A3B-Instruct-GGUF", 16384)
        assert not ok_big
        assert "budget exceeded" in why

    def test_budget_refusal_discriminating(self, http):
        """A load that fits nowhere in the iGPU line even with an empty fleet."""
        http["mem_gb"] = 100.0
        http["models"]["data"].append({"id": "GRANITE-HUGE-GGUF", "size": 50.0})
        ok, why = admission_ok("GRANITE-HUGE-GGUF", 16384)
        assert not ok
        assert "IGPU budget exceeded" in why and "50.00GB" in why

    def test_cpu_budget_refusal(self, http):
        http["mem_gb"] = 100.0
        http["health"] = _residents("Phi-4-mini-3.8B-CPU-32T")
        # A -CPU-marked 30.7G model: needed 33.7 > 24 - 2.8 = 21.2 room.
        http["models"]["data"].append({"id": "Gemma-4-31B-it-CPU", "size": 30.7})
        ok, why = admission_ok("Gemma-4-31B-it-CPU", 16384)
        assert not ok
        assert "CPU budget exceeded" in why

    def test_resident_sizes_unknown_count_as_zero_but_ram_floor_still_applies(self, http):
        """Unknown RESIDENT sizes are tolerated in the line; the floor still guards."""
        http["health"] = _residents("UNLISTED-MODEL-GGUF")
        http["mem_gb"] = 25.0
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 4096)
        assert ok, why  # 5.56 + ~1 KV fits 48 - 0 with one unknown resident
        http["mem_gb"] = 20.0
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 4096)
        assert not ok and "RAM floor" in why  # 20 - ~6.6 < 16

    def test_npu_budget_refusal(self, http):
        http["mem_gb"] = 100.0
        http["models"]["data"].append({"id": "big-flm", "size": 12.0})
        http["health"] = _residents("small-FLM")
        http["models"]["data"].append({"id": "small-FLM", "size": 5.0})
        ok, why = admission_ok("big-flm", 16384)
        assert not ok
        assert "NPU budget exceeded" in why  # 12+3=15 > 16-5=11


# ── admission: fail-closed paths ───────────────────────────────────────────


class TestAdmissionFailClosed:
    def test_unknown_size_refuses_blind_cold_load(self, http):
        """The catalog has no size for this model => refuse, never guess."""
        ok, why = admission_ok("UNLISTED-MODEL-GGUF", 8192)
        assert not ok
        assert "unknown model size" in why and "fail closed" in why

    def test_health_down_refuses(self, monkeypatch):
        monkeypatch.setattr(fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: None)
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert not ok
        assert "unreachable" in why and "fail closed" in why

    def test_health_unreachable_names_degraded_health_in_reason(self, monkeypatch):
        """Degraded health must fail ADMISSION closed, naming health in the reason."""
        monkeypatch.setattr(fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: None)
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert ok is False
        assert "health" in why.lower() and "degraded" in why.lower()

    def test_health_unreachable_census_still_empty_dict_no_raise(self, monkeypatch):
        """Census contract is unchanged: degraded health -> {} (never raises)."""
        monkeypatch.setattr(fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: None)
        assert resident_by_backend(BASE) == {}  # does not raise

    def test_health_malformed_body_refuses_admission_but_census_empty(self, http):
        """A malformed (answered) health body is degraded, NOT a zero-resident fleet.

        This is the wedge that opened the iGPU cap: an answered health body
        without a well-formed `all_models_loaded` list must refuse admission —
        while the census keeps returning {} per its contract.
        """
        http["health"] = {"status": "ok"}  # answered, but no all_models_loaded list
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert ok is False
        assert "health" in why.lower() and "degraded" in why.lower()
        assert resident_by_backend(BASE) == {}  # census contract intact, no raise

    def test_health_malformed_entry_types_refuse_admission_census_empty(self, http):
        """`all_models_loaded` as a non-list (e.g. a string) is degraded too."""
        http["health"] = {"all_models_loaded": "garbage"}
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert ok is False and "degraded" in why.lower()
        assert resident_by_backend(BASE) == {}

    def test_resident_state_distinguishes_degraded_from_empty(self, http, monkeypatch):
        """The seam admission uses: None on degraded, {} on answered-and-empty."""
        assert fabric._resident_state(BASE) == {}  # healthy, empty fleet

        monkeypatch.setattr(fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: None)
        assert fabric._resident_state(BASE) is None  # unreachable

        monkeypatch.setattr(
            fabric, "_get", lambda url, timeout=fabric.DEFAULT_TIMEOUT_S: {"nope": 1}
        )
        assert fabric._resident_state(BASE) is None  # malformed body

    def test_models_catalog_down_fails_closed(self, http, monkeypatch):
        """Health up but catalog down: size unverifiable -> refuse."""
        calls = {"n": 0}

        def _partial(url, timeout=fabric.DEFAULT_TIMEOUT_S):
            if url.endswith("/api/v1/health"):
                return {"all_models_loaded": []}
            calls["n"] += 1
            return None

        monkeypatch.setattr(fabric, "_get", _partial)
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 8192)
        assert not ok and calls["n"] == 1
        assert "unknown model size" in why

    def test_implausible_size_refuses(self, http):
        """A 35B model reporting 1.68GB is bad metadata, not a small model."""
        http["models"]["data"].append({"id": "Qwen3.6-35B-A3B-GGUF", "size": 1.68})
        ok, why = admission_ok("Qwen3.6-35B-A3B-GGUF", 4096)
        assert not ok
        assert "implausible catalog size" in why

    def test_meminfo_unreadable_refuses(self, http, monkeypatch):
        http["mem_unreadable"] = True
        monkeypatch.setattr(fabric, "_mem_available_gb", lambda: None)
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 4096)
        assert not ok
        assert "MemAvailable is unreadable" in why

    def test_nonpositive_ctx_size_refuses(self, http):
        for bad in (0, -1):
            ok, why = admission_ok("Gemma-4-E4B-it-GGUF", bad)
            assert not ok
            assert "invalid ctx_size" in why

    def test_empty_model_name_refuses(self, http):
        ok, why = admission_ok("", 8192)
        assert not ok and "empty" in why

    def test_never_raises_on_any_input(self, http):
        """The gate's contract: (ok, reason) always, even on hostile input."""
        for name, ctx in [
            (None, 8192),
            ("x" * 5, "huge"),
            (12345, 8192),
            ("Gemma-4-E4B-it-GGUF", None),
        ]:
            ok, why = admission_ok(name, ctx, BASE)  # type: ignore[arg-type]
            assert isinstance(ok, bool) and isinstance(why, str)


# ── admission: system RAM floor ────────────────────────────────────────────


class TestAdmissionRamFloor:
    def test_refuses_when_projected_free_dips_below_floor(self, http):
        http["mem_gb"] = 20.0  # 20 - (5.56 + ~2.75 KV) = ~11.7 < 16
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 16384)
        assert not ok
        assert "RAM floor" in why and "16GB floor" in why

    def test_admits_exactly_at_floor_boundary(self, http):
        http["mem_gb"] = 22.0  # 22 - 6 = 16.0 → not below the floor
        ok, why = admission_ok("Gemma-4-E4B-it-GGUF", 1024)
        assert ok, why

    def test_floor_applies_after_backend_budget_passes(self, http):
        """Budget headroom alone is not admission — the pool floor binds too."""
        http["models"]["data"].append({"id": "TINY-GGUF", "size": 0.5})
        # 16.5 - (0.5 + 0.25 KV) = 15.875 < 16 despite a nearly empty 48G iGPU line.
        http["mem_gb"] = 16.5
        ok, why = admission_ok("TINY-GGUF", 1024)
        assert not ok
        assert "RAM floor" in why


# ── KV proration ───────────────────────────────────────────────────────────


class TestKvProration:
    def test_max_ctx_matches_hotswap_flat_rule(self):
        assert fabric._kv_overhead_gb(22.10, fabric.MAX_CTX) == 3.0
        assert fabric._kv_overhead_gb(5.56, fabric.MAX_CTX) == 1.0

    def test_small_ctx_is_prorated_with_a_floor(self):
        assert fabric._kv_overhead_gb(22.10, 1024) == pytest.approx(3.0 * 0.25)
        assert fabric._kv_overhead_gb(5.56, 1024) == 0.25

    def test_never_exceeds_the_flat_rule(self):
        assert fabric._kv_overhead_gb(22.10, 16384) <= 3.0
        assert fabric._kv_overhead_gb(22.10, 999999) == 3.0  # clamped at MAX_CTX
