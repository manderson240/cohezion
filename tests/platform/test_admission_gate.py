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
    audit_bypass_paths,
    is_load_path,
)


GiB = 1024**3
CHAT = "v1/chat/completions"


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
    def _write(self, tmp_path, current: int, high: str, inactive_file: int) -> None:
        (tmp_path / "memory.current").write_text(f"{current}\n")
        (tmp_path / "memory.high").write_text(f"{high}\n")
        (tmp_path / "memory.stat").write_text(
            f"anon 1000\nactive_file 5000\ninactive_file {inactive_file}\nshmem 10\n"
        )

    def test_inactive_file_cache_is_not_counted(self, tmp_path, monkeypatch) -> None:
        # Counting memory.current would refuse routine loads on cold page cache alone.
        self._write(tmp_path, 25 * GiB, str(30 * GiB), 10 * GiB)
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() == pytest.approx((15.0, 30.0))

    def test_no_memory_high_means_no_check(self, tmp_path, monkeypatch) -> None:
        self._write(tmp_path, 5 * GiB, "max", 0)
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
            read_catalog=lambda: next(calls),
        )

    def test_unknown_size_refuses(self) -> None:
        g = self._gate_with_catalog([None])  # catalog stalled, never read
        d = g.decide("Gemma-4-26B-A4B-it-GGUF", CHAT)
        assert d.allow is False
        assert "size unknown" in d.reason

    def test_cached_size_survives_a_stalled_catalog(self) -> None:
        g = self._gate_with_catalog([{"Gemma-4-26B-A4B-it-GGUF": 16.9}, None])
        assert g.decide("qwen3.5-4b-FLM", CHAT).allow is False  # first fetch: name absent
        d = g.decide("Gemma-4-26B-A4B-it-GGUF", CHAT)  # served from cache, no refetch
        assert d.allow is False and "cgroup" in d.reason

    def test_small_cached_model_admitted(self) -> None:
        g = self._gate_with_catalog([{"qwen3.5-4b-FLM": 5.0}])
        assert g.decide("qwen3.5-4b-FLM", CHAT).allow is True
