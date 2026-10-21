"""lemond cgroup headroom: the pool the 2026-10-15 throttle actually came from.

Model weights loaded by lemond's children (llama-server, flm) are charged to the
``lemond.service`` cgroup. Past its ``memory.high`` the kernel throttles every
process in it, so one large CPU-backend probe (Gemma-4-26B) stalled the whole
fleet, NPU included, while system RAM looked fine. The byte gate checks system
MemAvailable and GTT; neither sees this limit.
"""

from __future__ import annotations

from unittest.mock import patch

import pytest

from cohezion.platform import admission_gate as ag
from cohezion.platform.admission_gate import AdmissionGate, GateConfig


GiB = 1024**3


def _gate(cgroup: tuple[float, float] | None, available_gb: float = 43.0) -> AdmissionGate:
    return AdmissionGate(
        config=GateConfig(floor_gb=16.0, enforce=True, enforce_aperture_guard=False),
        read_available_gb=lambda: available_gb,
        read_resident=lambda: [],
        read_gtt=lambda: None,
        read_swap=lambda: 0.0,
        read_psi=lambda: 0.0,
        read_cgroup=lambda: cgroup,
    )


def _catalog(name: str, size_gb: float):
    return patch(
        "cohezion.compound.oom_guard._catalog_entry",
        return_value={"id": name, "size": size_gb, "recipe": "llamacpp"},
    )


class TestCgroupHeadroom:
    def test_incident_load_refused_although_system_ram_admits_it(self) -> None:
        # 10-15 numbers: 43 GB available system-wide, memory.high 30 GB, 23 GB in use.
        # A 16 GB CPU model clears the byte gate but would push the cgroup to ~39 GB.
        with _catalog("Gemma-4-26B-A4B-it-GGUF", 16.0):
            d = _gate(cgroup=(23.0, 30.0)).decide("Gemma-4-26B-A4B-it-GGUF")
        assert d.allow is False
        assert "cgroup" in d.reason

    def test_small_load_with_headroom_admitted(self) -> None:
        with _catalog("Gemma-4-E2B-it-GGUF", 3.1):
            d = _gate(cgroup=(17.0, 30.0)).decide("Gemma-4-E2B-it-GGUF")
        assert d.allow is True, d.reason

    def test_applies_to_npu_models_too(self) -> None:
        # FLM runs as a lemond child, so its weights hit the same limit.
        with patch(
            "cohezion.compound.oom_guard._catalog_entry",
            return_value={"id": "qwen3.6-moe-35b-a3b-FLM", "size": 20.0, "recipe": "flm"},
        ):
            d = _gate(cgroup=(17.0, 30.0)).decide("qwen3.6-moe-35b-a3b-FLM")
        assert d.allow is False
        assert "cgroup" in d.reason

    def test_unreadable_or_unlimited_cgroup_fails_open(self) -> None:
        with _catalog("Gemma-4-E2B-it-GGUF", 3.1):
            assert _gate(cgroup=None).decide("Gemma-4-E2B-it-GGUF").allow is True


class TestWorkingSetReader:
    def _write(self, tmp_path, current: int, high: str, inactive_file: int) -> None:
        (tmp_path / "memory.current").write_text(f"{current}\n")
        (tmp_path / "memory.high").write_text(f"{high}\n")
        (tmp_path / "memory.stat").write_text(
            f"anon 1000\nactive_file 5000\ninactive_file {inactive_file}\nshmem 10\n"
        )

    def test_inactive_file_cache_is_not_counted(self, tmp_path, monkeypatch) -> None:
        # 25 GiB charged, 10 GiB of it cold page cache the kernel drops before throttling.
        # Counting memory.current would refuse routine loads on cache alone.
        self._write(tmp_path, 25 * GiB, str(30 * GiB), 10 * GiB)
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        ws, high = ag.read_lemond_cgroup_gb()
        assert ws == pytest.approx(15.0)
        assert high == pytest.approx(30.0)

    def test_no_memory_high_means_no_check(self, tmp_path, monkeypatch) -> None:
        self._write(tmp_path, 5 * GiB, "max", 0)
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path)
        assert ag.read_lemond_cgroup_gb() is None

    def test_missing_cgroup_returns_none(self, tmp_path, monkeypatch) -> None:
        monkeypatch.setattr(ag, "LEMOND_CGROUP", tmp_path / "absent")
        assert ag.read_lemond_cgroup_gb() is None
