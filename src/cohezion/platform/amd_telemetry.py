"""AMD silicon telemetry from AMD's own tools, not hand-rolled sysfs paths.

- iGPU: ``amdsmi`` (ROCm ``amd-smi-lib``). Verified on this Strix Halo (gfx1151) 2026-10-21:
  GTT used matched sysfs ``mem_info_gtt_used`` byte for byte; edge temperature, GFX
  activity and socket power are reported; hotspot temperature and the GFX clock are not.
- NPU: ``flm validate --json`` (FastFlowLM's own stack check: device, firmware, columns,
  memlock, ``ready``).
- CPU package temperature: the ``k10temp`` hwmon sensor, found by NAME. amdsmi reads CPU
  metrics only through HSMP, which Ryzen APUs do not expose.

Every reader returns ``None`` (or omits a field) when its source is unavailable: telemetry
must never take a caller down. Inside the Claude Code sandbox ``/dev/kfd``, ``/dev/dri`` and
``/dev/accel`` are hidden, so these read as unavailable there; services see the devices.

Install amdsmi into the venv from the ROCm package (it is not on PyPI officially):
    sudo apt install amd-smi-lib
    uv pip install /opt/rocm-7.2.1/share/amd_smi
"""

from __future__ import annotations

import contextlib
import json
import logging
import pathlib
import shutil
import subprocess
from typing import Any


logger = logging.getLogger(__name__)

_GIB = 1024.0**3


def gpu_metrics() -> dict[str, float] | None:
    """iGPU metrics from amdsmi, or None when amdsmi or the GPU is unavailable.

    Keys present only when supported: gtt_used_gb, gtt_total_gb, vram_used_gb,
    gfx_busy_pct, edge_temp_c, socket_power_w.
    """
    try:
        import amdsmi as a  # type: ignore[import-not-found]
    except ImportError:
        return None
    try:
        a.amdsmi_init(a.AmdSmiInitFlags.INIT_AMD_GPUS)
    except Exception as exc:  # no device (sandbox) or driver missing
        logger.debug("amdsmi init failed: %s", exc)
        return None
    try:
        handles = a.amdsmi_get_processor_handles()
        if not handles:
            return None
        h = handles[0]
        reads: dict[str, Any] = {
            "gtt_used_gb": lambda: a.amdsmi_get_gpu_memory_usage(h, a.AmdSmiMemoryType.GTT) / _GIB,
            "gtt_total_gb": lambda: a.amdsmi_get_gpu_memory_total(h, a.AmdSmiMemoryType.GTT) / _GIB,
            "vram_used_gb": lambda: (
                a.amdsmi_get_gpu_memory_usage(h, a.AmdSmiMemoryType.VRAM) / _GIB
            ),
            "gfx_busy_pct": lambda: a.amdsmi_get_gpu_activity(h)["gfx_activity"],
            "edge_temp_c": lambda: a.amdsmi_get_temp_metric(
                h, a.AmdSmiTemperatureType.EDGE, a.AmdSmiTemperatureMetric.CURRENT
            ),
            "socket_power_w": lambda: a.amdsmi_get_power_info(h)["socket_power"],
        }
        out: dict[str, float] = {}
        for key, read in reads.items():
            try:
                value = read()
            except Exception as exc:  # unsupported on this ASIC: leave the key out
                logger.debug("amdsmi %s unavailable: %s", key, exc)
                continue
            if isinstance(value, (int, float)):  # amdsmi reports "N/A" as a string
                out[key] = float(value)
        return out
    finally:
        with contextlib.suppress(Exception):
            a.amdsmi_shut_down()


def npu_status(timeout_s: float = 20.0) -> dict[str, Any] | None:
    """``flm validate --json`` output, or None when flm is missing or the call fails."""
    flm = shutil.which("flm")
    if flm is None:
        return None
    try:
        proc = subprocess.run(
            [flm, "validate", "--json"],
            capture_output=True,
            text=True,
            timeout=timeout_s,
            check=False,
        )
        return json.loads(proc.stdout)
    except (OSError, subprocess.TimeoutExpired, ValueError) as exc:
        logger.debug("flm validate failed: %s", exc)
        return None


def cpu_package_temp_c() -> float | None:
    """CPU package temperature (Tctl) from the hwmon sensor named ``k10temp``."""
    try:
        for hw in pathlib.Path("/sys/class/hwmon").iterdir():
            if (hw / "name").read_text().strip() == "k10temp":
                return int((hw / "temp1_input").read_text()) / 1000.0
    except (OSError, ValueError):
        return None
    return None
