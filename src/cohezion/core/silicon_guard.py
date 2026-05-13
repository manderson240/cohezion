"""
Silicon Guard: Hardware-aware safety constraints for Strix Halo.
Protects local silicon from thermal overload and VRAM over-subscription.
"""

import logging
from dataclasses import dataclass

import psutil
import torch


logger = logging.getLogger(__name__)


@dataclass
class HardwarePressure:
    temp_c: float
    gpu_mem_used_gb: float
    npu_active: bool
    is_throttled: bool
    reason: str = ""


class SiliconGuard:
    """
    Active guardrails for AMD Strix Halo (gfx1151).
    Monitors thermal state and GTT (Graphics Translation Table) pressure.
    """

    def __init__(
        self,
        temp_limit: float = 85.0,
        gtt_limit_gb: float = 60.0,  # Target 64GB VRAM pool
        throttle_tps: float = 0.5,  # Reduce speed by 50% if hot
    ):
        self.temp_limit = temp_limit
        self.gtt_limit_gb = gtt_limit_gb
        self.throttle_tps = throttle_tps

    def get_temperature(self) -> float:
        """Read APU temperature from hwmon."""
        try:
            # Common path for Ryzen APUs
            with open("/sys/class/hwmon/hwmon0/temp1_input") as f:
                return float(f.read()) / 1000.0
        except Exception:
            return 45.0  # Baseline if unreadable

    def get_gpu_memory(self) -> float:
        """Measure GTT pressure (since VRAM is shared in UMA)."""
        if torch.cuda.is_available():
            try:
                # Primary: Torch's view of GPU memory
                mem = torch.cuda.memory_allocated() / (1024**3)
                if mem > 0:
                    return mem
            except RuntimeError as e:
                if "invalid device function" in str(e):
                    return -1.0
                pass

        # Fallback: Check system memory pressure (GTT on Strix Halo uses system RAM)
        vm = psutil.virtual_memory()
        # If total RAM > 96GB, assume Strix Halo and monitor the 64GB 'logical' VRAM slice
        if vm.total > 96 * (1024**3):
            # UMA pressure is reflected in available system memory
            used_system_gb = (vm.total - vm.available) / (1024**3)
            return used_system_gb

        return 0.0

    def check_safety(self) -> HardwarePressure:
        """Perform a safety audit and return pressure state."""
        temp = self.get_temperature()
        mem = self.get_gpu_memory()

        is_throttled = False
        reason = ""

        if temp > self.temp_limit:
            is_throttled = True
            reason = f"Thermal limit reached: {temp:.1f}°C > {self.temp_limit}°C"

        if mem > self.gtt_limit_gb:
            is_throttled = True
            reason = f"VRAM over-subscription: {mem:.1f}GB > {self.gtt_limit_gb}GB"

        if mem == -1.0:
            is_throttled = True
            reason = "Silicon Hard-Lock detected (gfx1151 ISA mismatch)"

        if is_throttled:
            logger.warning("🔴 SILICON GUARD ENGAGED: %s", reason)

        return HardwarePressure(
            temp_c=temp,
            gpu_mem_used_gb=mem,
            npu_active=True,  # Verified via port 13306 check elsewhere
            is_throttled=is_throttled,
            reason=reason,
        )

    def apply_guardrails(self, payload: dict) -> dict:
        """Adjust request payload based on hardware pressure."""
        pressure = self.check_safety()

        if pressure.is_throttled:
            # Aggressive throttling
            payload["temperature"] = 0.1  # Reduce variance to save compute
            payload["max_tokens"] = min(payload.get("max_tokens", 1000), 128)

            # If TurboQuant is requested, force it to highest compression
            if "turbo_quant" in payload:
                payload["turbo_quant"]["precision"] = "3.5-bit"
                payload["turbo_quant"]["node_limit"] = "npu"  # Offload to cooler node

        return payload


# Singleton for system-wide access
_GUARD = None


def get_silicon_guard() -> SiliconGuard:
    global _GUARD
    if _GUARD is None:
        _GUARD = SiliconGuard()
    return _GUARD
