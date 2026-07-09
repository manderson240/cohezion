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

# ── FastAPI backend ───────────────────────────────────────────────────────────
API_HOST: str = "0.0.0.0"
API_PORT: int = 8080
