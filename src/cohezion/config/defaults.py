"""Cohezion platform defaults — single source of truth for well-known constants.

All production inference routes through the Lemonade OmniRouter on :13305.
Per-port servers (:13306/:13307/:13308/:13309) are down and redundant.
See harness.md §N3 and local-inference-default.md for the full topology.
"""

from __future__ import annotations


# ── Lemonade OmniRouter (AMD Strix Halo) ──────────────────────────────────────
LEMONADE_BASE_URL: str = "http://localhost:13305"
LEMONADE_OPENAI_URL: str = f"{LEMONADE_BASE_URL}/v1"
LEMONADE_API_URL: str = f"{LEMONADE_BASE_URL}/api/v1"

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
LANE_PORTS: dict[str, int] = {"npu": 13306, "igpu": 13307, "cpu": 13309}
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
