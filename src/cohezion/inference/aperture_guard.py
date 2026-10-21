"""Hardware Aperture & Memory Guard for Strix Halo.

Enforces the NPU/CPU local inference policy on facts the guard can actually see:
- Forbids Vulkan and ROCm/HIP model loads in Tier 1 to protect the GTT UMA
  aperture from kernel page-table races and host OOM crashes.
- Refuses non-NPU loads while live GTT usage is above the soft cap.

It does NOT decide by model name. A name says nothing about the backend (the
fleet runs GGUF on ``llamacpp.backend=cpu``) or the footprint, and FLM weights
live in shared DRAM, not NPU SRAM. Memory is priced by the admission gate's
byte budget (weights + KV, floor, swap, PSI, GTT headroom), which runs after
this guard.
"""

from __future__ import annotations

import contextlib
import logging
from pathlib import Path
from typing import Literal


logger = logging.getLogger(__name__)

# Hard limits for Tier 1
TIER1_MAX_CPU_BYTES = 4 * 1024 * 1024 * 1024  # 4 GiB
GTT_UMA_SOFT_CAP_BYTES = 40 * 1024 * 1024 * 1024  # 40 GiB
GTT_UMA_HARD_CAP_BYTES = 50 * 1024 * 1024 * 1024  # 50 GiB

# Allowed models for Tier 1
TIER1_NPU_ALLOWLIST = {
    "llama3.2-1b-FLM",
    "llama3.2:1b",
    "qwen3.5-4b-FLM",
    "qwen3.5:4b",
    "qwen3vl-it-4b-FLM",
    "qwen3vl:4b",
    "deepseek-r1-0528-8b-FLM",
    "deepseek-r1-0528:8b",
    "deepseek-r1-8b-FLM",
    "deepseek-r1:8b",
    "qwen3.6-moe-35b-a3b-FLM",
    "qwen3.6-moe:35b-a3b",
    "qwen3.8-mtp-27b-FLM",
    "qwen3.8-mtp:27b",
    "gemma4-it-e2b-FLM",
    "gemma4-it:e2b",
    "gemma4e-flash-e2b-FLM",
    "gemma4e-flash:e2b",
    "gemma4-it-12b-FLM",
    "gemma4-it:12b",
    "gpt-oss-20b-FLM",
    "gpt-oss:20b",
    "embed-gemma-300m-FLM",
    "gemma3-4b-FLM",
    "gemma3:4b",
}

TIER1_CPU_ALLOWLIST = {
    "Qwen3-0.6B-GGUF",
    "Qwen3-0.6B",
    "nomic-embed-text-v2-moe-GGUF",
    "nomic-embed-text",
    "kokoro-v1",
    "onnxruntime",
    "moonshine",
    "Whisper-Large-v3-Turbo",
}

BLOCKED_TIER1_BACKENDS = {"vulkan", "rocm", "hip", "vllm"}


class AperturePolicyError(Exception):
    """Raised when an inference request violates the hardware aperture safety policy."""

    pass


# Backwards compatibility alias
AperturePolicyViolation = AperturePolicyError


def get_current_gtt_used_bytes() -> int:
    """Read currently used AMD GPU GTT memory via sysfs."""
    total_used = 0
    for p in Path("/sys/class/drm").glob("card*/device/mem_info_gtt_used"):
        if p.is_file():
            with contextlib.suppress(Exception):
                total_used += int(p.read_text().strip())
    return total_used


def validate_tier1_request(
    model_id: str,
    backend: str = "auto",
    estimated_bytes: int = 0,
) -> Literal["allow", "reroute_tier2"]:
    """Validate whether an inference request is permitted to run on Tier 1.

    Parameters
    ----------
    model_id : str
        Model identifier (e.g. 'qwen3.5-4b-FLM', 'Qwen3.6-35B-A3B-GGUF').
    backend : str, default 'auto'
        Backend target (e.g. 'flm', 'cpu', 'vulkan', 'rocm').
    estimated_bytes : int, default 0
        Estimated memory allocation in bytes.

    Returns
    -------
    Literal['allow', 'reroute_tier2']
        'allow' if permitted on NPU/CPU; 'reroute_tier2' if heavy and must be offloaded.
    """
    backend_clean = backend.lower()

    # 1. Block forbidden GPU backends
    if backend_clean in BLOCKED_TIER1_BACKENDS:
        logger.warning(
            "Hardware Aperture Guard: Backend '%s' forbidden in Tier 1 for model '%s'. Offloading to Tier 2.",
            backend,
            model_id,
        )
        return "reroute_tier2"

    # 2. NPU models draw no GTT. Their DRAM footprint is NOT zero; the admission
    #    gate prices it (npu_exempt=False).
    if model_id in TIER1_NPU_ALLOWLIST or model_id.endswith("-FLM"):
        return "allow"

    # 3. Check if model is on CPU allowlist
    if model_id in TIER1_CPU_ALLOWLIST:
        if estimated_bytes > TIER1_MAX_CPU_BYTES:
            logger.warning(
                "Hardware Aperture Guard: CPU model '%s' exceeds 4GB limit (%d bytes). Offloading to Tier 2.",
                model_id,
                estimated_bytes,
            )
            return "reroute_tier2"
        return "allow"

    # 4. No name-based verdict. A "-GGUF"/"8B" name refused a ~3 GB CPU-backend model
    #    (Gemma-4-E2B, 2026-10-21) and broke the local cascade past the NPU, while the
    #    byte gate would have admitted it. Backend is ruled on in step 1; size belongs
    #    to the byte gate.

    # 5. Check live GTT saturation
    gtt_used = get_current_gtt_used_bytes()
    if gtt_used >= GTT_UMA_SOFT_CAP_BYTES:
        logger.warning(
            "Hardware Aperture Guard: GTT usage (%d GiB) exceeds soft cap (%d GiB). Rerouting '%s' to Tier 2.",
            gtt_used // (1024**3),
            GTT_UMA_SOFT_CAP_BYTES // (1024**3),
            model_id,
        )
        return "reroute_tier2"

    return "allow"


def assert_safe_tier1(model_id: str, backend: str = "auto", estimated_bytes: int = 0) -> None:
    """Raise AperturePolicyViolation if request cannot run on Tier 1."""
    verdict = validate_tier1_request(model_id, backend, estimated_bytes)
    if verdict != "allow":
        raise AperturePolicyViolation(
            f"Hardware Aperture Guard blocked Tier 1 execution for '{model_id}' (backend: {backend}). "
            f"Mandate requires NPU/CPU only; heavy workloads must route to Ollama Cloud or Headless Claude."
        )
