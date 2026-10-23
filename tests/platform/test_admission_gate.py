"""Thin admission gate: only the lemond cgroup check, never on non-load requests.

The gate exists for one failure Lemonade cannot see (GEMS LESSONS 22, 2026-10-15): a model
loaded by lemond is charged to lemond.service's cgroup, and past memory.high the kernel
throttles every model in it, NPU included, while system RAM looks fine.
"""

from __future__ import annotations

import dataclasses
from unittest.mock import patch

import pytest

from cohezion.platform import admission_gate as ag
from cohezion.platform.admission_gate import (
    AdmissionGate,
    GateConfig,
    SystemMemory,
    audit_bypass_paths,
    is_load_path,
)


GiB = 1024**3
CHAT = "v1/chat/completions"
# Readable, ample host memory with GTT at the desktop baseline. These tests pin the cgroup
# arithmetic; with no catalog every placement is uncertain (2026-10-23 certainty rule), so
# the system check also runs and must pass for the cgroup check to be what decides.
AMPLE = SystemMemory(100.0, 128.0, gtt_used_gb=0.8, gtt_total_gb=96.0)


def _gate(
    cgroup: tuple[float, float] | None = (17.0, 30.0),
    size_gb: float | None = 3.0,
    resident: list[str] | None = None,
    enforce: bool = True,
) -> AdmissionGate:
    entries = None if resident is None else [{"model_name": n, "checkpoint": ""} for n in resident]
    return AdmissionGate(
        config=GateConfig(enforce=enforce),
        read_resident=lambda: entries,
        read_cgroup=lambda: cgroup,
        read_size_gb=lambda _m: size_gb,
        read_system=lambda: AMPLE,
    )


class TestCgroupHeadroom:
    def test_incident_load_refused(self) -> None:
        # 10-15 numbers: memory.high 30 GB, 23 GB in use, a 16 GB CPU model requested.
        d = _gate(cgroup=(23.0, 30.0), size_gb=16.0, resident=[]).decide(
            "Gemma-4-26B-A4B-it-GGUF", CHAT
        )
        assert d.allow is False
        assert "cgroup" in d.reason

    def test_npu_model_counts_too(self) -> None:
        # flm runs as a lemond child, so FLM weights hit the same limit.
        d = _gate(cgroup=(17.0, 30.0), size_gb=22.1, resident=[]).decide(
            "qwen3.6-moe-35b-a3b-FLM", CHAT
        )
        assert d.allow is False

    def test_small_load_with_headroom_admitted(self) -> None:
        d = _gate(cgroup=(17.0, 30.0), size_gb=5.0, resident=[]).decide("qwen3.5-4b-FLM", CHAT)
        assert d.allow is True, d.reason

    def test_unknown_cgroup_fails_open(self) -> None:
        assert _gate(cgroup=None, resident=[]).decide("x-GGUF", CHAT).allow

    def test_unknown_cgroup_and_system_refuses_an_uncertain_load(self) -> None:
        # The cgroup half fails open, but an uncertain placement still faces the system
        # check, which fails closed when unreadable.
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: None,
            read_size_gb=lambda _m: 3.0,
        )
        assert g.decide("x-GGUF", CHAT).allow is False

    def test_unknown_size_fails_closed(self) -> None:
        assert not _gate(size_gb=None, resident=[]).decide("x-GGUF", CHAT).allow


class TestNeverGated:
    @pytest.mark.parametrize("path", ["api/v1/unload", "v1/unload", "api/v1/delete", "api/v1/pull"])
    def test_non_load_paths_pass_even_when_cgroup_is_full(self, path: str) -> None:
        # Live defect 2026-10-21: the old guard refused an UNLOAD of the 26B because the
        # body named a model, blocking the one call that frees memory.
        d = _gate(cgroup=(29.0, 30.0), size_gb=16.0, resident=[]).decide(
            "Gemma-4-26B-A4B-it-GGUF", path
        )
        assert d.allow is True

    def test_load_paths_are_load_paths(self) -> None:
        for path in (CHAT, "api/v1/load", "v1/embeddings", "v1/completions"):
            assert is_load_path(path)

    def test_no_model_named_is_allowed(self) -> None:
        assert _gate(cgroup=(29.0, 30.0), size_gb=16.0).decide(None, "v1/models").allow

    def test_name_alone_never_refuses(self) -> None:
        # The removed aperture guard refused any '-GGUF' / '8B' name. Only bytes count now.
        d = _gate(cgroup=(10.0, 30.0), size_gb=3.1, resident=[]).decide("Gemma-4-E2B-it-GGUF", CHAT)
        assert d.allow is True


class TestResidency:
    def test_resident_model_passes_even_when_cgroup_is_full(self) -> None:
        g = _gate(cgroup=(29.0, 30.0), size_gb=16.0, resident=["Bonsai-8B-gguf"])
        assert g.decide("Bonsai-8B-gguf", CHAT).allow is True

    def test_checkpoint_style_name_matches_resident_entry(self) -> None:
        entries = [{"model_name": "bonsai-8b", "checkpoint": "unsloth/Bonsai-8B-gguf:Q4_K_M"}]
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: entries,
            read_cgroup=lambda: (29.0, 30.0),
            read_size_gb=lambda _m: 16.0,
        )
        assert g.decide("Bonsai-8B-gguf", CHAT).allow is True

    def test_residency_unreadable_is_not_a_pass(self) -> None:
        # Health blocks during loads; 'cannot see' falls through to the cgroup check.
        g = _gate(cgroup=(29.0, 30.0), size_gb=16.0, resident=None)
        assert g.decide("Bonsai-8B-gguf", CHAT).allow is False

    def test_probes_target_the_upstream_not_the_proxy(self) -> None:
        cfg = GateConfig(upstream_base="http://127.0.0.1:13315")
        with patch("cohezion.platform.admission_gate.fetch_loaded_models", return_value=[]) as m:
            AdmissionGate(config=cfg, read_cgroup=lambda: None).decide("Bonsai-8B-gguf", CHAT)
        assert m.call_args.kwargs["base_url"] == "http://127.0.0.1:13315"


class TestConfig:
    def test_config_rereads_environment_on_every_construction(self) -> None:
        with patch.dict("os.environ", {"COHEZION_ADMISSION_ENFORCE": "0"}):
            assert GateConfig.from_env().enforce is False
        with patch.dict("os.environ", {"COHEZION_ADMISSION_ENFORCE": "1"}):
            assert GateConfig.from_env().enforce is True

    def test_config_is_frozen(self) -> None:
        cfg = GateConfig()
        with pytest.raises(dataclasses.FrozenInstanceError):
            cfg.enforce = False  # type: ignore[misc]

    def test_enforce_false_logs_but_allows(self) -> None:
        d = _gate(cgroup=(29.0, 30.0), size_gb=16.0, resident=[], enforce=False).decide(
            "Gemma-4-26B-A4B-it-GGUF", CHAT
        )
        assert d.allow is True and d.would_refuse is True


class TestBypassAudit:
    def test_audit_surfaces_backend_ports(self) -> None:
        health = [
            {"model_name": "Bonsai-8B-gguf", "backend_url": "http://127.0.0.1:8002/v1"},
            {"model_name": "kokoro-v1", "backend_url": ""},
        ]
        assert audit_bypass_paths(loaded=health) == ["http://127.0.0.1:8002/v1"]

    def test_audit_unreadable_health_reports_unknown_not_empty(self) -> None:
        assert audit_bypass_paths(loaded=None) is None


class TestCgroupReader:
    def _write(self, tmp_path, high: str, current: int | None = None, **stat: int) -> None:
        (tmp_path / "memory.high").write_text(f"{high}\n")
        if current is not None:
            (tmp_path / "memory.current").write_text(f"{current}\n")
        fields = {
            "anon": 0,
            "file": 0,
            "shmem": 0,
            "file_mapped": 0,
            "active_file": 0,
            "inactive_file": 0,
            **stat,
        }
        (tmp_path / "memory.stat").write_text("".join(f"{k} {v}\n" for k, v in fields.items()))

    def test_unmapped_cache_is_not_counted_even_on_the_active_list(
        self, tmp_path, monkeypatch
    ) -> None:
        # Live 2026-10-21 after the 26B was unloaded: its 16.9 GB stayed on the ACTIVE
        # file list. Counting it (current - inactive_file = 28.7 GB) refuses every load.
        # Bound: 5 + min(7 + 9, 24) = 21.
        self._write(
            tmp_path,
            str(30 * GiB),
            anon=5 * GiB,
            shmem=7 * GiB,
            file_mapped=9 * GiB,
            file=24 * GiB,
            active_file=17 * GiB,
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() == pytest.approx((21.0, 30.0))

    def test_mapped_shmem_is_not_counted_twice(self, tmp_path, monkeypatch) -> None:
        # Live 2026-10-22 22:33 with deepseek-r1-0528-8b-FLM resident on the NPU: its 7.21 GB
        # buffers sat in BOTH shmem and file_mapped (unloading it dropped each by 7.2 GB and
        # memory.current by 8.44 GB). anon+shmem+file_mapped read 22.6 GB, more than the
        # cgroup's entire 20.12 GB charge, and refused a 6.8 GB Gemma that fit.
        self._write(
            tmp_path,
            str(30 * GiB),
            current=int(20.12 * GiB),
            anon=int(6.25 * GiB),
            shmem=int(7.21 * GiB),
            file_mapped=int(9.13 * GiB),
            file=int(13.79 * GiB),
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        reading = ag.read_lemond_cgroup_gb()
        assert reading is not None
        working, high = reading
        assert working == pytest.approx(20.04, abs=0.01)  # 6.25 + min(16.34, 13.79)
        assert working <= 20.12 and high == pytest.approx(30.0)
        # The refused load now fits the 90% budget; it would not under the old sum (22.6).
        assert working + 6.8 <= 0.9 * high

    def test_after_the_flm_unload_the_reading_tracks_the_charge(
        self, tmp_path, monkeypatch
    ) -> None:
        # Same cgroup after the FLM model left: shmem 0, file_mapped 1.90, file 6.58.
        self._write(
            tmp_path,
            str(30 * GiB),
            current=int(11.67 * GiB),
            anon=int(5.05 * GiB),
            shmem=0,
            file_mapped=int(1.90 * GiB),
            file=int(6.58 * GiB),
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        reading = ag.read_lemond_cgroup_gb()
        assert reading is not None
        assert reading[0] == pytest.approx(6.95, abs=0.01)

    def test_unmapped_pinned_shmem_beside_mapped_weights_is_not_under_counted(
        self, tmp_path, monkeypatch
    ) -> None:
        # The case anon + max(shmem, file_mapped) gets wrong (adversarial review 2026-10-22):
        # amdxdna pins NPU buffers with drm_gem_shmem_pin whether or not anything maps them,
        # while llama.cpp mmaps its GGUF weights. 6 GB unmapped shmem + 10 GB mapped weights
        # is 16 GB the kernel cannot drop; max() would report 10. Under-counting admits a load
        # that pushes lemond past memory.high and throttles every model.
        self._write(
            tmp_path,
            str(30 * GiB),
            anon=2 * GiB,
            shmem=6 * GiB,
            file_mapped=10 * GiB,
            file=16 * GiB,
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() == pytest.approx((18.0, 30.0))

    def test_unmapped_shmem_still_counts(self, tmp_path, monkeypatch) -> None:
        # shmem nobody maps is still unreclaimable without swap: 2 + min(6 + 1, 7) = 9.
        self._write(
            tmp_path, str(30 * GiB), anon=2 * GiB, shmem=6 * GiB, file_mapped=1 * GiB, file=7 * GiB
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() == pytest.approx((9.0, 30.0))

    def test_working_set_never_exceeds_the_cgroup_charge(self, tmp_path, monkeypatch) -> None:
        # memory.stat and memory.current are read separately, so an unload between the two
        # reads can leave the stat figure above the charge. Uncharged memory is not in use.
        self._write(
            tmp_path,
            str(30 * GiB),
            current=int(8.5 * GiB),
            anon=8 * GiB,
            shmem=0,
            file_mapped=1 * GiB,
            file=9 * GiB,
        )
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() == pytest.approx((8.5, 30.0))

    def test_no_memory_high_means_no_check(self, tmp_path, monkeypatch) -> None:
        self._write(tmp_path, "max", anon=5 * GiB)
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() is None

    def test_missing_cgroup_returns_none(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path / "absent")
        assert ag.read_lemond_cgroup_gb() is None


class TestSizeUnknownFailsClosed:
    """Live defect 2026-10-21 20:22: lemonade's /api/v1/models stalls while a model loads,
    the 2 s size lookup timed out, the gate read 'size unknown' as 'Lemonade decides', and a
    16.9 GB CPU model loaded past the cgroup budget (throttle events 3,237 -> 4,558)."""

    def _gate_with_catalog(self, fetches):
        calls = iter(fetches)
        return AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: (11.1, 30.0),
            read_catalog=lambda: (
                None
                if (c := next(calls)) is None
                else {k: {"size": v, "recipe": "flm"} for k, v in c.items()}
            ),
        )

    def test_unknown_size_refuses(self) -> None:
        g = self._gate_with_catalog([None])  # catalog stalled, never read
        d = g.decide("never-curated-model-GGUF", CHAT)  # not in oom_guard's curated table
        assert d.allow is False
        assert "size unknown" in d.reason

    def test_curated_size_prices_a_model_even_without_the_catalog(self) -> None:
        g = self._gate_with_catalog([None])
        d = g.decide("Gemma-4-26B-A4B-it-GGUF", CHAT)
        assert d.allow is False and "cgroup" in d.reason

    def test_name_missing_from_a_fresh_catalog_is_refused_without_retry(self) -> None:
        # Review H3: a permanent "not a model" must not become a 503-retry loop. Round 3
        # (A3, user directive): it must not be admitted unchecked either, because lemonade
        # can resolve names its catalog lacks (aliases, register-then-load). So: 404.
        g = self._gate_with_catalog([{"Gemma-4-26B-A4B-it-GGUF": 16.9}])
        d = g.decide("qwen3.5-4b-FLM-typo", CHAT)
        assert d.allow is False and "not in lemonade's catalog" in d.reason
        assert d.status == 404

    def test_small_cached_model_admitted(self) -> None:
        g = self._gate_with_catalog([{"qwen3.5-4b-FLM": 5.0}])
        assert g.decide("qwen3.5-4b-FLM", CHAT).allow is True


class TestNpuSlotSwap:
    """Live 2026-10-21 22:00: the NPU holds ONE FLM llm. Loading another evicts it, but the
    gate added the new model on top and refused even the 1.3 GB llama3.2-1b-FLM at a 27.8 GB
    working set, blocking every NPU swap."""

    def _gate(self, resident: list[dict[str, object]], sizes: dict[str, float]):
        return AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: resident,
            read_cgroup=lambda: (27.8, 30.0),
            read_size_gb=lambda m: sizes.get(m),
        )

    FLM_RESIDENT = [{"model_name": "deepseek-r1-0528-8b-FLM", "recipe": "flm", "type": "llm"}]
    SIZES = {"deepseek-r1-0528-8b-FLM": 5.6, "llama3.2-1b-FLM": 1.3, "x-GGUF": 1.3}

    def test_flm_swap_credits_the_evicted_flm_model(self) -> None:
        d = self._gate(self.FLM_RESIDENT, self.SIZES).decide("llama3.2-1b-FLM", CHAT)
        assert d.allow is True, d.reason

    def test_gguf_load_gets_no_npu_credit(self) -> None:
        d = self._gate(self.FLM_RESIDENT, self.SIZES).decide("x-GGUF", CHAT)
        assert d.allow is False

    def test_no_credit_when_no_flm_is_resident(self) -> None:
        d = self._gate([], self.SIZES).decide("llama3.2-1b-FLM", CHAT)
        assert d.allow is False

    def test_embedding_path_gets_no_llm_slot_credit(self) -> None:
        d = self._gate(self.FLM_RESIDENT, self.SIZES).decide("llama3.2-1b-FLM", "v1/embeddings")
        assert d.allow is False


class TestDynamicCoordination:
    def test_mcp_tools_call_names_its_model(self) -> None:
        # Live 2026-10-21: lemonade's MCP tools (lemonade_chat, lemonade_omni, ...) take a
        # `model` argument and load it on demand; the gate read only top-level keys.
        from cohezion.platform.admission_gate import extract_model_name

        body = {
            "jsonrpc": "2.0",
            "method": "tools/call",
            "params": {"name": "lemonade_chat", "arguments": {"model": "Gemma-4-26B-A4B-it-GGUF"}},
        }
        assert extract_model_name(body) == "Gemma-4-26B-A4B-it-GGUF"
        assert extract_model_name({"jsonrpc": "2.0", "method": "tools/list"}) is None

    def test_concurrent_loads_cannot_share_the_same_headroom(self) -> None:
        # Two 10 GB loads at 10 GB working set (budget 27): only one may pass until the first
        # shows up as resident -- each seeing the same headroom is the race.
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: (10.0, 30.0),
            read_size_gb=lambda _m: 10.0,
            read_system=lambda: AMPLE,
        )
        assert g.decide("a-FLMX", CHAT).allow is True
        second = g.decide("b-FLMX", CHAT)
        assert second.allow is False and "reserved" in second.reason

    def test_reservation_released_once_the_model_is_resident(self) -> None:
        resident: list[dict[str, object]] = []
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: resident,
            read_cgroup=lambda: (10.0, 30.0),
            read_size_gb=lambda _m: 10.0,
            read_system=lambda: AMPLE,
        )
        assert g.decide("a-GGUF", CHAT).allow
        resident.append({"model_name": "a-GGUF", "checkpoint": ""})
        g._resident_cache = None  # skip the 1.5 s TTL
        assert g.decide("b-GGUF", CHAT).allow

    def test_footprint_includes_kv_reservation(self) -> None:
        entry = {"size": 5.0, "recipe": "llamacpp", "recipe_options": {"ctx_size": 32768}}
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: (20.0, 30.0),
            read_catalog=lambda: {"x-GGUF": entry},
        )
        footprint = g._read_size_gb("x-GGUF")
        assert footprint is not None and footprint > 5.0  # weights alone under-price the load


class TestReviewFindings:
    def test_models_named_finds_every_shape(self) -> None:
        from cohezion.platform.admission_gate import models_named

        batch = [
            {"method": "tools/call", "params": {"arguments": {"model": "A"}}},
            {"params": {"arguments": {"image_model": "B", "messages": [{"content": "C-GGUF"}]}}},
            {"checkpoint": "D"},
        ]
        # keys select, not values: a message mentioning a model is not a load
        assert sorted(models_named(batch)) == ["A", "B", "D"]

    def test_exact_routes_only_skip_gating(self) -> None:
        assert not is_load_path("api/v1/unload") and not is_load_path("/v1/pull/")
        assert is_load_path("api/v1/preload") and is_load_path("v1/reload")

    def test_release_frees_a_reservation(self) -> None:
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: (10.0, 30.0),
            read_size_gb=lambda _m: 10.0,
            read_system=lambda: AMPLE,
        )
        assert g.decide("a-GGUF", CHAT).allow
        g.release("a-GGUF")
        assert g.decide("b-GGUF", CHAT).allow

    def test_same_model_twice_is_not_repriced(self) -> None:
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [],
            read_cgroup=lambda: (10.0, 30.0),
            read_size_gb=lambda _m: 10.0,
            read_system=lambda: AMPLE,
        )
        assert g.decide("a-GGUF", CHAT).allow
        assert g.decide("a-GGUF", CHAT).allow  # still loading; lemond dedupes

    def test_last_known_residency_survives_a_health_stall(self) -> None:
        answers = iter([[{"model_name": "big-GGUF", "checkpoint": ""}], None])
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: next(answers),
            read_cgroup=lambda: (29.0, 30.0),
            read_size_gb=lambda _m: 16.0,
        )
        assert g.decide("big-GGUF", CHAT).allow
        g._resident_cache = None  # health now blocks
        assert g.decide("big-GGUF", CHAT).allow

    def test_residency_never_matches_by_substring(self) -> None:
        g = AdmissionGate(
            config=GateConfig(),
            read_resident=lambda: [
                {"model_name": "x", "checkpoint": "org/Qwen3.6-35B-A3B-GGUF:Q4"}
            ],
            read_cgroup=lambda: (29.0, 30.0),
            read_size_gb=lambda _m: 16.0,
        )
        assert not g.decide("GGUF", CHAT).allow
