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
# NPU-first (user directive 2026-10-23/24): run inference on the XDNA2 NPU (FastFlowLM,
# "-FLM" ids served by lemonade on :13305) unless a task needs an iGPU-only model -- less
# power, and it keeps the iGPU/CPU free. Priorities: tasks complete (no OOM) > quality > speed.
# Measured (calibrated 6-role gauntlet, exact/exec graders, n=39): gemma4-it-e2b-FLM with
# think=false 1.000 (every role 1.0) -- best on any silicon; same model think=true 0.949;
# Gemma-4-E2B-it-GGUF (iGPU, the previous default) 0.973; qwen3.5-4b-FLM think=false 0.897;
# llama3.2-1b-FLM 0.513.
# SINGLE SLOT: the NPU holds ONE LLM at a time and requesting another FLM model swaps it
# (slow, under lemond's lock), so tier 0 is the one shared NPU model -- the llama3.2-1b-FLM
# tier 0 of 2026-10-22 thrashed the slot against other FLM workloads.
# STICKY THINK: FLM's "think" flag persists on the loaded model across callers; a request
# that omits it inherits whatever the last caller set. EVERY tier-0 request to an FLM id
# must therefore send top-level "think": false -- merge tier0_request_extras() into the
# payload (the one chokepoint). Gemma-4-E2B-it-GGUF stays a valid COHEZION_TIER0_MODEL
# override (thinking GGUF: callers read reasoning_content; no think flag is sent).
DEFAULT_TIER0_MODEL: str = "gemma4-it-e2b-FLM"


def tier0_model() -> str:
    """Tier-0 model id; ``COHEZION_TIER0_MODEL`` overrides. Read at call time, not import."""
    return os.environ.get("COHEZION_TIER0_MODEL") or DEFAULT_TIER0_MODEL


def tier0_request_extras(model_id: str) -> dict[str, bool]:
    """Payload fields every tier-0 request must carry: ``{"think": False}`` for an FLM id
    (the flag is sticky on the loaded NPU model), else nothing. Callers pass the tier-0 id."""
    return {"think": False} if model_id.endswith("-FLM") else {}


# ── Tier 2 (cascade completion) model ────────────────────────────────────────
# AWAITING THE LARGE-MODEL SWEEP: no measured more-capable tier 2 has been chosen yet. The
# default is the cascade's tier-1 id (Gemma-4-E4B), so build_triune_omni_orchestrator
# deduplicates it away for ANY tier 0 and the default cascade is [tier 0, Gemma-4-E4B]: the
# iGPU only as the quality-gate escalation. Set COHEZION_TIER2_MODEL to add a third tier.
DEFAULT_TIER2_MODEL: str = "Gemma-4-E4B-it-GGUF"


def tier2_model() -> str:
    """Tier-2 model id; ``COHEZION_TIER2_MODEL`` overrides. Read at call time, not import."""
    return os.environ.get("COHEZION_TIER2_MODEL") or DEFAULT_TIER2_MODEL


# Tier-0 ctx has exactly ONE authority: lemonade's saved per-model option, written from
# compound.lemonade_recipes.BASE_RECIPES by scripts/apply_lemonade_recipes.py. No client
# pins it per load -- a second authority makes lemond unload/reload the model whenever two
# callers disagree (a slot thrash). FLM honours a saved "ctx_size" too (rounded up to a
# power of two, min 512).


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
    "npu": DEFAULT_TIER0_MODEL,
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
    "npu": DEFAULT_TIER0_MODEL,
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
