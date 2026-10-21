"""amd_telemetry: amdsmi for the iGPU, flm validate for the NPU, k10temp by name for the CPU."""

from __future__ import annotations

import json
import sys
import types
from unittest.mock import MagicMock, patch

from cohezion.platform import amd_telemetry as t


GIB = 1024**3


def _fake_amdsmi(*, activity: object = 2, power: object = 68) -> types.ModuleType:
    a = types.ModuleType("amdsmi")
    a.AmdSmiInitFlags = types.SimpleNamespace(INIT_AMD_GPUS=1)
    a.AmdSmiMemoryType = types.SimpleNamespace(GTT="gtt", VRAM="vram")
    a.AmdSmiTemperatureType = types.SimpleNamespace(EDGE="edge")
    a.AmdSmiTemperatureMetric = types.SimpleNamespace(CURRENT="cur")
    a.amdsmi_init = MagicMock()
    a.amdsmi_shut_down = MagicMock()
    a.amdsmi_get_processor_handles = lambda: ["h0"]
    a.amdsmi_get_gpu_memory_usage = lambda h, kind: {"gtt": 3 * GIB, "vram": GIB // 2}[kind]
    a.amdsmi_get_gpu_memory_total = lambda h, kind: 96 * GIB
    a.amdsmi_get_gpu_activity = lambda h: {"gfx_activity": activity}
    a.amdsmi_get_temp_metric = lambda h, typ, metric: 45
    a.amdsmi_get_power_info = lambda h: {"socket_power": power}
    return a


class TestGpuMetrics:
    def test_reads_every_supported_metric(self) -> None:
        with patch.dict(sys.modules, {"amdsmi": _fake_amdsmi()}):
            m = t.gpu_metrics()
        assert m == {
            "gtt_used_gb": 3.0,
            "gtt_total_gb": 96.0,
            "vram_used_gb": 0.5,
            "gfx_busy_pct": 2.0,
            "edge_temp_c": 45.0,
            "socket_power_w": 68.0,
        }

    def test_na_strings_are_left_out_not_reported_as_numbers(self) -> None:
        # amdsmi 26.2.2 on gfx1151 returns "N/A" for activity and socket power.
        with patch.dict(sys.modules, {"amdsmi": _fake_amdsmi(activity="N/A", power="N/A")}):
            m = t.gpu_metrics()
        assert "gfx_busy_pct" not in m and "socket_power_w" not in m
        assert m["gtt_used_gb"] == 3.0

    def test_missing_amdsmi_returns_none(self) -> None:
        with patch.dict(sys.modules, {"amdsmi": None}):
            assert t.gpu_metrics() is None

    def test_init_failure_returns_none_and_never_raises(self) -> None:
        a = _fake_amdsmi()
        a.amdsmi_init = MagicMock(side_effect=RuntimeError("no /dev/dri"))
        with patch.dict(sys.modules, {"amdsmi": a}):
            assert t.gpu_metrics() is None

    def test_shuts_down_after_reading(self) -> None:
        a = _fake_amdsmi()
        with patch.dict(sys.modules, {"amdsmi": a}):
            t.gpu_metrics()
        a.amdsmi_shut_down.assert_called_once()


class TestNpuStatus:
    def test_parses_flm_validate_json(self) -> None:
        payload = {"ready": True, "devices": [{"device": "/dev/accel/accel0", "cols": 8}]}
        done = MagicMock(stdout=json.dumps(payload))
        with (
            patch.object(t.shutil, "which", return_value="/usr/bin/flm"),
            patch.object(t.subprocess, "run", return_value=done) as run,
        ):
            assert t.npu_status() == payload
        assert run.call_args.args[0] == ["/usr/bin/flm", "validate", "--json"]

    def test_missing_flm_returns_none(self) -> None:
        with patch.object(t.shutil, "which", return_value=None):
            assert t.npu_status() is None

    def test_unparseable_output_returns_none(self) -> None:
        with (
            patch.object(t.shutil, "which", return_value="/usr/bin/flm"),
            patch.object(t.subprocess, "run", return_value=MagicMock(stdout="oops")),
        ):
            assert t.npu_status() is None


def _hwmon_tree(root, sensors: dict[str, str | None]) -> None:
    for i, (name, temp) in enumerate(sensors.items()):
        d = root / f"hwmon{i}"
        d.mkdir()
        (d / "name").write_text(f"{name}\n")
        if temp is not None:
            (d / "temp1_input").write_text(f"{temp}\n")


class TestCpuTempAndSiliconGuard:
    def test_finds_k10temp_by_name_not_position(self, tmp_path, monkeypatch) -> None:
        # The real box: hwmon0 is the AC adapter with no temperature.
        _hwmon_tree(tmp_path, {"ACAD": None, "acpitz_0": "44800", "k10temp": "67750"})
        real_path = t.pathlib.Path
        monkeypatch.setattr(
            t.pathlib,
            "Path",
            lambda p: tmp_path if p == "/sys/class/hwmon" else real_path(p),
        )
        assert t.cpu_package_temp_c() == 67.75

    def test_silicon_guard_reads_the_package_sensor(self, monkeypatch) -> None:
        # Old code read hwmon0 (ACAD), failed, and always returned the 45.0 fallback.
        from cohezion.core.silicon_guard import SiliconGuard

        monkeypatch.setattr("cohezion.platform.amd_telemetry.cpu_package_temp_c", lambda: 84.4)
        assert SiliconGuard().get_temperature() == 84.4

    def test_silicon_guard_falls_back_when_unreadable(self, monkeypatch) -> None:
        from cohezion.core.silicon_guard import SiliconGuard

        monkeypatch.setattr("cohezion.platform.amd_telemetry.cpu_package_temp_c", lambda: None)
        assert SiliconGuard().get_temperature() == 45.0
