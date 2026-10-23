"""Placement-aware admission: a load whose bytes land in GTT is checked against system memory.

MEASURED 2026-10-23 (Strix Halo gfx1151, 128 GB unified RAM, per-second samples) with
Gemma-4-E2B-it-GGUF loaded on the llama.cpp VULKAN backend:
  - GTT used rose 0.84 -> 5.56 GB (mem_info_gtt_total = 96 GiB). Desktop baseline ~0.8 GB.
  - lemond cgroup at that moment: anon 0.96, file_mapped 1.26, file 5.58 (page cache of the
    GGUF read), memory.current 6.58 GB. The weights + KV are NOT in the cgroup the gate reads.
  - MemAvailable fell ~13 GB from its idle maximum.
So on Vulkan the cgroup check alone prices a 5 GB load at almost nothing. CPU-backend GGUF
and FLM (NPU) loads ARE charged to the cgroup and keep the existing check unchanged.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import pytest

from cohezion.platform import admission_gate as ag
from cohezion.platform.admission_gate import (
    AdmissionGate,
    GateConfig,
    SystemMemory,
    model_placement,
    read_system_memory_gb,
)


GiB = 1024**3
CHAT = "v1/chat/completions"
MODEL = "Gemma-4-E2B-it-GGUF"

# Measured cgroup working set on Vulkan: anon 0.96 + min(shmem + file_mapped, file).
# shmem was not reported in the sample; 0 is assumed, which gives the larger reading.
VULKAN_CGROUP = (0.96 + min(0.0 + 1.26, 5.58), 30.0)  # 2.22 GB of a 30 GB memory.high
GTT_TOTAL = 96.0
GTT_IDLE = 0.84  # measured, no model loaded
LOAD_GB = 5.0  # ~ the measured GTT growth (5.56 - 0.84 = 4.72 GB), rounded up


def _gate(
    *,
    backend: str = "vulkan",
    system: SystemMemory | None,
    cgroup: tuple[float, float] | None = VULKAN_CGROUP,
    size_gb: float | None = LOAD_GB,
    overrides: tuple[tuple[str, str], ...] = (),
    enforce: bool = True,
) -> AdmissionGate:
    return AdmissionGate(
        config=GateConfig(enforce=enforce, gguf_backend=backend, backend_overrides=overrides),
        read_resident=lambda: [],
        read_cgroup=lambda: cgroup,
        read_size_gb=lambda _m: size_gb,
        read_system=lambda: system,
    )


# MemAvailable = 20 GB is a CHOSEN pressure state (only the ~13 GB drop was measured): with a
# 16 GB floor, 20 - 5 = 15 GB left is a breach.
PRESSURED = SystemMemory(
    mem_available_gb=20.0, mem_total_gb=122.0, gtt_used_gb=GTT_IDLE, gtt_total_gb=GTT_TOTAL
)
AMPLE = SystemMemory(
    mem_available_gb=60.0, mem_total_gb=122.0, gtt_used_gb=GTT_IDLE, gtt_total_gb=GTT_TOTAL
)


class TestVulkanLoadIsPricedAgainstSystemMemory:
    def test_a_old_cgroup_only_path_admits_the_load(self) -> None:
        # backend=cpu is today's behaviour (and the default): only the cgroup is checked,
        # 2.22 + 5.0 = 7.2 GB <= 27 GB, so the load passes despite the MemAvailable floor.
        d = _gate(backend="cpu", system=PRESSURED).decide(MODEL, CHAT)
        assert d.allow is True, d.reason

    def test_a_vulkan_load_that_fits_the_cgroup_but_breaches_the_floor_is_refused(self) -> None:
        d = _gate(system=PRESSURED).decide(MODEL, CHAT)
        assert d.allow is False
        assert "MemAvailable" in d.reason

    def test_b_same_load_with_ample_memory_is_admitted(self) -> None:
        d = _gate(system=AMPLE).decide(MODEL, CHAT)
        assert d.allow is True, d.reason

    def test_gtt_cap_refuses_even_with_ample_memavailable(self) -> None:
        full_gtt = SystemMemory(60.0, 122.0, gtt_used_gb=84.0, gtt_total_gb=GTT_TOTAL)
        d = _gate(system=full_gtt).decide(MODEL, CHAT)  # 84 + 5 > 0.9 * 96 = 86.4
        assert d.allow is False and "GTT" in d.reason

    def test_cgroup_check_still_applies_to_gpu_loads(self) -> None:
        # Additive, not a swap: a Vulkan load must also pass the existing cgroup check.
        d = _gate(system=AMPLE, cgroup=(25.0, 30.0)).decide(MODEL, CHAT)
        assert d.allow is False and "cgroup" in d.reason

    def test_shadow_mode_reports_but_allows(self) -> None:
        d = _gate(system=PRESSURED, enforce=False).decide(MODEL, CHAT)
        assert d.allow is True and d.would_refuse is True


class TestFailClosed:
    def test_d_unreadable_gtt_refuses_a_gpu_load(self) -> None:
        no_gtt = SystemMemory(60.0, 122.0, gtt_used_gb=None, gtt_total_gb=None)
        d = _gate(system=no_gtt).decide(MODEL, CHAT)
        assert d.allow is False and "GTT" in d.reason

    def test_d_unreadable_memavailable_refuses_a_gpu_load(self) -> None:
        no_mem = SystemMemory(None, None, gtt_used_gb=GTT_IDLE, gtt_total_gb=GTT_TOTAL)
        assert _gate(system=no_mem).decide(MODEL, CHAT).allow is False

    def test_d_no_system_reading_at_all_refuses(self) -> None:
        assert _gate(system=None).decide(MODEL, CHAT).allow is False

    def test_d_unreadable_cgroup_does_not_skip_the_system_check(self) -> None:
        # The cgroup path fails open; that must not carry a GPU load past the GTT check.
        no_gtt = SystemMemory(60.0, 122.0, gtt_used_gb=None, gtt_total_gb=None)
        d = _gate(system=no_gtt, cgroup=None).decide(MODEL, CHAT)
        assert d.allow is False

    def test_unreadable_cgroup_with_ample_system_memory_admits_gpu_load(self) -> None:
        assert _gate(system=AMPLE, cgroup=None).decide(MODEL, CHAT).allow is True

    def test_cpu_load_never_reads_system_memory(self) -> None:
        def boom() -> SystemMemory:
            raise AssertionError("cgroup-placed loads must not depend on GTT/MemAvailable")

        g = AdmissionGate(
            config=GateConfig(gguf_backend="cpu"),
            read_resident=lambda: [],
            read_cgroup=lambda: VULKAN_CGROUP,
            read_size_gb=lambda _m: LOAD_GB,
            read_system=boom,
        )
        assert g.decide(MODEL, CHAT).allow is True


class TestReservations:
    def test_concurrent_gpu_loads_cannot_share_the_same_headroom(self) -> None:
        # 60 GB available, floor 16: one 30 GB GPU load fits, a second must see the first.
        g = _gate(system=AMPLE, size_gb=30.0, cgroup=(0.0, 100.0))
        assert g.decide("a-GGUF", CHAT).allow is True
        second = g.decide("b-GGUF", CHAT)
        assert second.allow is False and "reserved" in second.reason

    def test_inflight_cgroup_load_counts_against_memavailable(self) -> None:
        # An FLM load admitted but not yet resident will consume system RAM too.
        g = _gate(system=SystemMemory(30.0, 122.0, GTT_IDLE, GTT_TOTAL), size_gb=8.0)
        assert g.decide("x-FLM", CHAT).allow is True  # cgroup-placed
        d = g.decide(MODEL, CHAT)  # 30 - 8 reserved - 8 = 14 < 16
        assert d.allow is False and "MemAvailable" in d.reason

    def test_gpu_reservation_does_not_consume_cgroup_budget(self) -> None:
        # The cgroup math for a CPU/FLM load stays exactly as before: GTT-bound bytes are
        # not in the cgroup, so they must not crowd it.
        g = _gate(system=AMPLE, size_gb=10.0, cgroup=(10.0, 30.0))
        assert g.decide(MODEL, CHAT).allow is True  # gpu-placed, 10 GB reserved
        assert g.decide("x-FLM", CHAT).allow is True  # 10 + 0 + 10 = 20 <= 27


class TestPlacement:
    def test_default_backend_is_cpu(self) -> None:
        with patch.dict("os.environ", {}, clear=False):
            import os

            os.environ.pop("COHEZION_ADMISSION_GGUF_BACKEND", None)
            assert GateConfig.from_env().gguf_backend == "cpu"
        assert model_placement(MODEL, None, GateConfig()) == "cgroup"

    def test_env_configures_backend_floor_and_overrides(self) -> None:
        env = {
            "COHEZION_ADMISSION_GGUF_BACKEND": "Vulkan",
            "COHEZION_ADMISSION_BACKEND_OVERRIDES": "Big-GGUF=cpu, other-GGUF = rocm",
            "COHEZION_ADMISSION_MEMAVAIL_FLOOR_GB": "12",
        }
        with patch.dict("os.environ", env):
            cfg = GateConfig.from_env()
        assert cfg.gguf_backend == "vulkan"
        assert cfg.mem_available_floor_gb == 12.0
        assert model_placement("Big-GGUF", None, cfg) == "cgroup"
        assert model_placement("other-GGUF", None, cfg) == "gtt"
        assert model_placement(MODEL, None, cfg) == "gtt"

    def test_flm_is_always_cgroup_even_with_an_override(self) -> None:
        cfg = GateConfig(gguf_backend="vulkan", backend_overrides=(("x-flm", "vulkan"),))
        assert model_placement("x-FLM", None, cfg) == "cgroup"
        assert model_placement("y", {"recipe": "flm"}, cfg) == "cgroup"

    def test_catalog_recipe_decides_llamacpp(self) -> None:
        cfg = GateConfig(gguf_backend="vulkan")
        assert model_placement("plain-name", {"recipe": "llamacpp"}, cfg) == "gtt"
        assert model_placement("Whisper-Base", {"recipe": "whispercpp"}, cfg) == "cgroup"

    def test_unknown_backend_is_treated_as_gpu(self) -> None:
        # A backend the gate does not know must not silently skip the system check.
        cfg = GateConfig(gguf_backend="something-new")
        assert model_placement(MODEL, None, cfg) == "gtt"


def _sysfs(
    tmp_path: Path, meminfo: dict[str, int], gtt: list[tuple[int, int]]
) -> tuple[Path, Path]:
    mi = tmp_path / "meminfo"
    mi.write_text("".join(f"{k}: {v // 1024} kB\n" for k, v in meminfo.items()))
    drm = tmp_path / "drm"
    for i, (used, total) in enumerate(gtt):
        dev = drm / f"card{i}" / "device"
        dev.mkdir(parents=True)
        (dev / "mem_info_gtt_used").write_text(f"{used}\n")
        (dev / "mem_info_gtt_total").write_text(f"{total}\n")
    drm.mkdir(exist_ok=True)
    return mi, drm


class TestSystemReader:
    def test_reads_measured_values(self, tmp_path: Path) -> None:
        mi, drm = _sysfs(
            tmp_path,
            {"MemTotal": 122 * GiB, "MemAvailable": 47 * GiB},
            [(int(5.56 * GiB), 96 * GiB)],
        )
        s = read_system_memory_gb(meminfo=mi, drm=drm)
        assert s.mem_available_gb == pytest.approx(47.0, abs=0.01)
        assert s.gtt_used_gb == pytest.approx(5.56, abs=0.01)
        assert s.gtt_total_gb == pytest.approx(96.0)

    def test_absent_gtt_is_none_not_zero(self, tmp_path: Path) -> None:
        mi, drm = _sysfs(tmp_path, {"MemTotal": 122 * GiB, "MemAvailable": 47 * GiB}, [])
        s = read_system_memory_gb(meminfo=mi, drm=drm)
        assert s.gtt_used_gb is None and s.gtt_total_gb is None

    def test_connector_links_to_the_same_device_are_counted_once(self, tmp_path: Path) -> None:
        mi, drm = _sysfs(
            tmp_path, {"MemTotal": 122 * GiB, "MemAvailable": 47 * GiB}, [(1 * GiB, 96 * GiB)]
        )
        (drm / "card0-DP-1").mkdir()
        (drm / "card0-DP-1" / "device").symlink_to(drm / "card0" / "device")
        s = read_system_memory_gb(meminfo=mi, drm=drm)
        assert s.gtt_used_gb == pytest.approx(1.0) and s.gtt_total_gb == pytest.approx(96.0)

    # (e) physical bounds: no derived quantity may exceed its container.
    def test_e_gtt_used_above_total_is_rejected(self, tmp_path: Path) -> None:
        mi, drm = _sysfs(
            tmp_path, {"MemTotal": 122 * GiB, "MemAvailable": 47 * GiB}, [(97 * GiB, 96 * GiB)]
        )
        s = read_system_memory_gb(meminfo=mi, drm=drm)
        assert s.gtt_used_gb is None and s.gtt_total_gb is None

    def test_e_memavailable_above_memtotal_is_rejected(self, tmp_path: Path) -> None:
        mi, drm = _sysfs(tmp_path, {"MemTotal": 10 * GiB, "MemAvailable": 47 * GiB}, [])
        assert read_system_memory_gb(meminfo=mi, drm=drm).mem_available_gb is None

    def test_e_gtt_bound_holds_on_this_box(self) -> None:
        s = read_system_memory_gb()
        if s.gtt_used_gb is not None:
            assert s.gtt_total_gb is not None and 0 <= s.gtt_used_gb <= s.gtt_total_gb
        if s.mem_available_gb is not None:
            assert s.mem_total_gb is not None and s.mem_available_gb <= s.mem_total_gb

    def test_e_gtt_budget_is_bounded_by_its_container(self) -> None:
        assert 0 < ag.GTT_TOTAL_FRACTION <= 1.0
