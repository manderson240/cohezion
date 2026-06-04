"""Centralized infrastructure defaults for Cohezion.

Single source of truth for ports, hardware topology, model roster, swarm
tuning constants, and computed base URLs.  Every value that was previously
hardcoded across ``distributed_swarm``, ``latent_engine``, ``telegram_bot``,
``tri_compute_orchestrator``, and ``orchestrator`` now lives here and is
overridable via environment variable.

Usage::

    from cohezion.config.defaults import OLLAMA_PORT, OLLAMA_BASE_URL
    from cohezion.config.defaults import CPU_SMALL_MODELS, LANE_PORTS

Environment variables (all optional — sensible defaults provided):

    OLLAMA_PORT            – Ollama HTTP port           (default 11434)
    LEMONADE_NPU_PORT      – Lemonade NPU lane port     (default 13306)
    LEMONADE_IGPU_ROCWMMA_PORT  – iGPU ROCWMMA port    (default 13307)
    LEMONADE_IGPU_UNIFIED_PORT  – iGPU Unified port    (default 13308)
    LEMONADE_CPU_PORT      – Lemonade CPU lane port     (default 13309)
    NPU_FLM_PORT           – NPU FLM inference port     (default 8004)
    SWARM_CPU_WORKERS      – CPU-parallel worker count   (default 6)
    SWARM_SCORE_WINDOW     – Adaptive scoring window     (default 20)
    SWARM_MIN_QUALITY      – Min quality to accept       (default 0.45)
    NPU_DEVICE             – NPU device path             (default /dev/xdna2)
    VULKAN_DEVICE          – Vulkan device id            (default amd:0)
    CPU_CORES              – Available CPU core count     (default 16)
"""

from __future__ import annotations

import os


# ---------------------------------------------------------------------------
# Infrastructure ports
# ---------------------------------------------------------------------------

OLLAMA_PORT: int = int(os.environ.get("OLLAMA_PORT", "11434"))
"""Default Ollama HTTP API port."""

LEMONADE_NPU_PORT: int = int(os.environ.get("LEMONADE_NPU_PORT", "13306"))
"""Lemonade lane port for NPU (XDNA2)."""

LEMONADE_IGPU_ROCWMMA_PORT: int = int(os.environ.get("LEMONADE_IGPU_ROCWMMA_PORT", "13307"))
"""Lemonade lane port for iGPU ROCWMMA."""

LEMONADE_IGPU_UNIFIED_PORT: int = int(os.environ.get("LEMONADE_IGPU_UNIFIED_PORT", "13308"))
"""Lemonade lane port for iGPU unified memory."""

LEMONADE_CPU_PORT: int = int(os.environ.get("LEMONADE_CPU_PORT", "13309"))
"""Lemonade lane port for CPU."""

NPU_FLM_PORT: int = int(os.environ.get("NPU_FLM_PORT", "8004"))
"""NPU FLM (FastFlowLM) inference port used by tri-compute orchestrator."""


# ---------------------------------------------------------------------------
# Strix Halo Symphony lane port map (computed from individual port vars)
# ---------------------------------------------------------------------------

LANE_PORTS: dict[str, int] = {
    "npu": LEMONADE_NPU_PORT,
    "igpu_rocwmma": LEMONADE_IGPU_ROCWMMA_PORT,
    "igpu_unified": LEMONADE_IGPU_UNIFIED_PORT,
    "cpu": LEMONADE_CPU_PORT,
}
"""Strix Halo Symphony lane ports — matches registry.py."""


# ---------------------------------------------------------------------------
# Base URLs (computed from ports)
# ---------------------------------------------------------------------------

OLLAMA_BASE_URL: str = f"http://localhost:{OLLAMA_PORT}"
"""Ollama HTTP API base URL."""

LEMONADE_NPU_BASE_URL: str = f"http://localhost:{LEMONADE_NPU_PORT}"
"""Lemonade NPU lane base URL."""


# ---------------------------------------------------------------------------
# Hardware topology
# ---------------------------------------------------------------------------

NPU_DEVICE: str = os.environ.get("NPU_DEVICE", "/dev/xdna2")
"""NPU device path (XDNA2)."""

VULKAN_DEVICE: str = os.environ.get("VULKAN_DEVICE", "amd:0")
"""Vulkan compute device identifier."""

CPU_CORES: int = int(os.environ.get("CPU_CORES", "16"))
"""Available CPU cores (Zen 5)."""


# ---------------------------------------------------------------------------
# Model roster
# ---------------------------------------------------------------------------

CPU_SMALL_MODELS: list[str] = [
    "phi4-mini",  # 3.8B  – matches 7-9B on many tasks
    "mistral:7b",  # 7B    – fast QA, edge-optimised
    "qwen3:1.7b",  # 1.7B  – very small, great for routing/sensing
    "gemma3n:2b",  # 2B    – on-device multimodal
    "smollm2:1.7b",  # 1.7B  – ultra-compact
]
"""Small models suited for CPU parallelism — no GPU memory needed."""

# Default tier models for TieredOrchestrator hierarchy
DEFAULT_TIER0_MODEL: str = "Gemma-4-E2B-it-GGUF"
"""Tier 0: fast NPU primary."""

DEFAULT_TIER1_MODEL: str = "Gemma-4-26B-A4B-it-GGUF"
"""Tier 1: midsize iGPU reasoner."""

DEFAULT_TIER2_MODEL: str = "claude-haiku-4-5"
"""Tier 2: first cloud fallback."""

DEFAULT_TIER3_MODEL: str = "claude-sonnet-4-6"
"""Tier 3: reviewer / arbiter (terminal tier)."""

# Lemonade lane model assignments
LANE_MODELS: dict[str, str] = {
    "npu": "Gemma-4-E2B-it-GGUF",
    "igpu_rocwmma": "Gemma-4-E4B-it-GGUF",
    "igpu_unified": "Gemma-4-26B-A4B-it-GGUF",
    "cpu": "Gemma-4-31B-it-GGUF",
}
"""Model-to-lane mapping for the Gemma-4 symphony deployment."""


# ---------------------------------------------------------------------------
# Swarm tuning
# ---------------------------------------------------------------------------

N_CPU_WORKERS: int = int(os.environ.get("SWARM_CPU_WORKERS", "6"))
"""How many CPU-parallel workers are allowed simultaneously."""

SCORE_WINDOW: int = int(os.environ.get("SWARM_SCORE_WINDOW", "20"))
"""Sliding window size for adaptive scoring."""

MIN_QUALITY_ACCEPT: float = float(os.environ.get("SWARM_MIN_QUALITY", "0.45"))
"""Minimum quality score (0-1) to accept a node's response without escalation."""

# ---------------------------------------------------------------------------
# Complexity analysis thresholds (unified_orchestrator)
# ---------------------------------------------------------------------------

COMPLEXITY_THRESHOLD: float = float(os.environ.get("SWARM_COMPLEXITY_THRESHOLD", "0.4"))
"""Complexity score where >COMPLEXITY_THRESHOLD triggers LatentEngine fallback."""

# ---------------------------------------------------------------------------
# Flume LatentEngine model defaults
# ---------------------------------------------------------------------------

LATENT_SMALL_MODEL: str = os.environ.get("LATENT_SMALL_MODEL", "phi4-mini")
"""Small language model for latent space encoding."""

LATENT_MEDIUM_MODEL: str = os.environ.get("LATENT_MEDIUM_MODEL", "mistral:7b")
"""Medium language model for latent space reasoning."""
