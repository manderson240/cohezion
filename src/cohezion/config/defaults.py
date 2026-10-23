"""Cohezion platform defaults — single source of truth for well-known constants.

All production inference routes through the Lemonade OmniRouter on :13305.
Per-port servers (:13306/:13307/:13308/:13309) are down and redundant.
See harness.md §N3 and local-inference-default.md for the full topology.
"""

from __future__ import annotations

import os


# ── Lemonade OmniRouter (AMD Strix Halo) ──────────────────────────────────────
LEMONADE_BASE_URL: str = "http://localhost:13305"
LEMONADE_OPENAI_URL: str = f"{LEMONADE_BASE_URL}/v1"
LEMONADE_API_URL: str = f"{LEMONADE_BASE_URL}/api/v1"
LEMONADE_NPU_BASE_URL: str = "http://localhost:13305"

# ── Tier 0 (fast classify/route) model — single source of truth ──────────────
# Moved OFF the NPU 2026-10-23: the XDNA2 NPU holds one FLM model and every swap evicts/
# reloads it under lemond's lock; the cascade's llama3.2-1b-FLM thrashed it against the
# Kaggle worker's FLM models. Same model family, llama.cpp Vulkan (iGPU) build.
DEFAULT_TIER0_MODEL: str = "Llama-3.2-1B-Instruct-GGUF"


def tier0_model() -> str:
    """Tier-0 model id; ``COHEZION_TIER0_MODEL`` overrides. Read at call time, not import."""
    return os.environ.get("COHEZION_TIER0_MODEL") or DEFAULT_TIER0_MODEL


# Tier-0 context window. Routing/classify prompts are short; every extra token of ctx is
# KV reserved at load (Llama-3.2-1B: 32 KiB/token, so 4096 -> 0.125 GB vs 4.0 GB native).
DEFAULT_TIER0_CTX: int = 4096
_TIER0_CTX_CEILING: int = 32768  # the N3 bound every BASE_RECIPES ctx_size respects


def tier0_ctx() -> int:
    """Tier-0 ctx_size; ``COHEZION_TIER0_CTX`` overrides. Read at call time.

    Non-positive or unparseable values fall back to the default: ctx_size 0 means "native
    window" to lemonade (the N3 OOM hazard), so it is never passed through. Clamped to 32768.
    """
    try:
        ctx = int(os.environ.get("COHEZION_TIER0_CTX", ""))
    except ValueError:
        return DEFAULT_TIER0_CTX
    if ctx <= 0:
        return DEFAULT_TIER0_CTX
    return min(ctx, _TIER0_CTX_CEILING)


def tier0_client_kwargs(model: str) -> dict[str, int]:
    """GAIA ``LemonadeClient`` kwargs that pin the tier-0 lane's load to ``tier0_ctx()``.

    Empty for any other model: re-pinning a shared non-tier-0 model would force a reload.
    """
    return {"ctx_size_override": tier0_ctx()} if model == tier0_model() else {}


# ── SurrealDB ─────────────────────────────────────────────────────────────────
SURREAL_HTTP_URL: str = "http://127.0.0.1:8001/sql"
SURREAL_WS_URL: str = "ws://localhost:8001"
SURREAL_NS: str = "cohezion"
SURREAL_DB: str = "main"
SURREAL_USER: str = "root"
SURREAL_PASS: str = "root"

# ── Ollama (cloud/remote fallback only) ──────────────────────────────────────
OLLAMA_BASE_URL: str = "http://localhost:11434"

# ── Unified orchestrator lanes (PR #242 imported these but never defined them;
#    values grounded in harness.md N1/N2 fleet topology and module usage) ─────
# All lanes dispatch through the :13305 OmniRouter (which fans out to NPU/iGPU/CPU
# on demand); the deprecated per-lane ports (:13306-:13309) are down and redundant.
LANE_PORTS: dict[str, int] = {"npu": 13305, "igpu": 13305, "cpu": 13305}
LANE_MODELS: dict[str, str] = {
    "npu": "llama3.2-1b-FLM",
    "igpu": "Gemma-4-E4B-it-GGUF",
    "cpu": "Gemma-4-26B-A4B-it-GGUF",
}
CPU_SMALL_MODELS: list[str] = ["phi3:mini"]
N_CPU_WORKERS: int = 2
# [0,1] complexity score above which LatentEngine engages
COMPLEXITY_THRESHOLD: float = 0.7
# [0,1] minimum quality gate before escalating a lane's answer
MIN_QUALITY_ACCEPT: float = 0.5
# rolling window (samples) for lane quality scores
SCORE_WINDOW: int = 20

# ── FastAPI backend ───────────────────────────────────────────────────────────
API_HOST: str = "0.0.0.0"
API_PORT: int = 8080

# ── Swarm / unified orchestrator constants ───────────────────────────────────
CPU_SMALL_MODELS: list[str] = [
    "phi4-mini",
    "mistral:7b",
    "qwen3:1.7b",
    "gemma3n:2b",
    "smollm2:1.7b",
]

LANE_MODELS: dict[str, str] = {
    "npu": "Gemma-4-E2B-it-GGUF",
    "igpu_rocwmma": "Gemma-4-E4B-it-GGUF",
    "igpu_unified": "Gemma-4-26B-A4B-it-GGUF",
    "cpu": "Gemma-4-31B-it-GGUF",
}

LANE_PORTS: dict[str, int] = {
    "npu": 13305,
    "igpu_rocwmma": 13305,
    "igpu_unified": 13305,
    "cpu": 13305,
}

N_CPU_WORKERS: int = int(os.environ.get("SWARM_CPU_WORKERS", "6"))
SCORE_WINDOW: int = int(os.environ.get("SWARM_SCORE_WINDOW", "20"))
MIN_QUALITY_ACCEPT: float = float(os.environ.get("SWARM_MIN_QUALITY", "0.45"))
COMPLEXITY_THRESHOLD: float = float(os.environ.get("SWARM_COMPLEXITY_THRESHOLD", "0.4"))
LATENT_SMALL_MODEL: str = os.environ.get("LATENT_SMALL_MODEL", "phi4-mini")
LATENT_MEDIUM_MODEL: str = os.environ.get("LATENT_MEDIUM_MODEL", "mistral:7b")
