"""Local-first mem0 memory adapter for Cohezion.

mem0 adds an LLM-extracted conversational memory layer: it uses an LLM to extract
salient facts from raw turns, then consolidates them against prior memories with
ADD / UPDATE / DELETE / NOOP operations (deduping and resolving contradictions).
This COMPLEMENTS — does not replace — SemanticCache (similarity dedup), SurrealDB
(structured bi-temporal store), JourneyTracker (12D trajectory), and the
Entity-Relation memory MCP server.

Wired local-first: LLM + embedder route to Lemonade's OpenAI-compatible endpoints
($0, on-device), and the vector store is in-process embedded Qdrant (no server
process). Telemetry (posthog) is disabled so conversational memory never egresses.

The module is import-safe with the optional `memory` extra absent: `mem0` is only
imported lazily inside ``build_local_mem0``. Construction itself is offline-safe —
the OpenAI-compatible clients are lazy, so no network call happens until
``.add()`` / ``.search()``. A live Lemonade node is required only at call time.
"""

from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any


if TYPE_CHECKING:  # pragma: no cover - typing only
    from mem0 import Memory


logger = logging.getLogger(__name__)

# Lemonade OpenAI-compatible defaults (local-first, $0). The CPU node (13309) is
# the resilient default because the NPU (13306) / iGPU (13307) tiers are often
# down; any caller can override every field via Mem0Config.
_DEFAULT_LLM_BASE_URL = "http://localhost:13309/v1"
_DEFAULT_LLM_MODEL = "Gemma-4-E4B-it-GGUF"
_DEFAULT_EMBED_BASE_URL = "http://localhost:13309/v1"
# Verified live on Lemonade 13309 (dogfood exp_mem0_dogfood): the generic
# "nomic-embed-text" id does NOT exist there and hard-fails; this moe GGUF is the
# harness-CA1 primary 768-dim encoder actually served.
_DEFAULT_EMBED_MODEL = "nomic-embed-text-v2-moe-GGUF"
_DEFAULT_EMBED_DIMS = 768  # Lemonade nomic embeddings are 768-dim (harness CA1)
_LOCAL_API_KEY = "lemonade-local"  # nosec B105 - dummy; Lemonade ignores auth


def mem0_available() -> bool:
    """Return True if the optional ``mem0ai`` extra is importable."""
    try:
        import mem0  # noqa: F401
    except ImportError:
        return False
    return True


@dataclass
class Mem0Config:
    """Local-first mem0 wiring. Every field defaults to on-device Lemonade."""

    llm_base_url: str = _DEFAULT_LLM_BASE_URL
    llm_model: str = _DEFAULT_LLM_MODEL
    embed_base_url: str = _DEFAULT_EMBED_BASE_URL
    embed_model: str = _DEFAULT_EMBED_MODEL
    embed_dims: int = _DEFAULT_EMBED_DIMS
    collection_name: str = "cohezion_memory"
    # Embedded Qdrant persists here — no server process. Override per deployment.
    storage_path: str = "/tmp/cohezion_mem0_qdrant"  # nosec B108
    api_key: str = _LOCAL_API_KEY
    temperature: float = 0.1
    max_tokens: int = 2000
    # Vector backend: "qdrant" (embedded, default) or "surrealdb" (canonical engine).
    vector_store_provider: str = "qdrant"
    surreal_url: str = "http://localhost:8001/sql"
    surreal_namespace: str = "cohezion"
    surreal_database: str = "main"
    # Opt-in: also write a SurrealDB provenance graph (agent -[remembers]-> fact,
    # preserving superseded text) alongside the vector store. Off by default so the
    # default path is unchanged; graph writes are always best-effort.
    provenance_graph: bool = False

    def _vector_store_dict(self) -> dict[str, Any]:
        if self.vector_store_provider == "surrealdb":
            return {
                "provider": "surrealdb",
                "config": {
                    "collection_name": self.collection_name,
                    "embedding_model_dims": self.embed_dims,
                    "url": self.surreal_url,
                    "namespace": self.surreal_namespace,
                    "database": self.surreal_database,
                },
            }
        return {
            "provider": "qdrant",
            "config": {
                "collection_name": self.collection_name,
                "path": self.storage_path,
                "embedding_model_dims": self.embed_dims,
                "on_disk": True,
            },
        }

    def to_mem0_dict(self) -> dict[str, Any]:
        """Render the dict consumed by ``mem0.Memory.from_config``."""
        return {
            "llm": {
                "provider": "openai",
                "config": {
                    "model": self.llm_model,
                    "openai_base_url": self.llm_base_url,
                    "api_key": self.api_key,
                    "temperature": self.temperature,
                    "max_tokens": self.max_tokens,
                },
            },
            "embedder": {
                "provider": "openai",
                "config": {
                    "model": self.embed_model,
                    "openai_base_url": self.embed_base_url,
                    "api_key": self.api_key,
                    "embedding_dims": self.embed_dims,
                },
            },
            "vector_store": self._vector_store_dict(),
        }


def disable_telemetry() -> None:
    """Disable mem0/posthog telemetry — conversational memory must not egress.

    Uses ``setdefault`` so an explicit operator override (re-enabling telemetry on
    purpose) is respected; otherwise both known opt-out switches are set off.
    """
    os.environ.setdefault("MEM0_TELEMETRY", "False")
    os.environ.setdefault("POSTHOG_DISABLED", "1")


def build_local_mem0(config: Mem0Config | None = None) -> Memory:
    """Construct a local-first mem0 ``Memory`` wired to Lemonade.

    Lazy-imports ``mem0``; raises ``ImportError`` with an install hint if the
    optional ``memory`` extra is absent. Telemetry is disabled before import.
    """
    cfg = config or Mem0Config()
    disable_telemetry()
    try:
        from mem0 import Memory
    except ImportError as exc:
        raise ImportError(
            "mem0 not installed. Install the optional extra: "
            "uv pip install -e '.[memory]'  (or: uv pip install mem0ai)"
        ) from exc

    # Register the custom SurrealDB vector provider into mem0's lookup tables.
    if cfg.vector_store_provider == "surrealdb":
        from cohezion.memory.surreal_vector_store import register_surreal_provider

        register_surreal_provider()

    logger.info(
        "Building local mem0: llm=%s@%s embedder=%s@%s(dims=%d) "
        "store=qdrant(embedded:%s) telemetry=off",
        cfg.llm_model,
        cfg.llm_base_url,
        cfg.embed_model,
        cfg.embed_base_url,
        cfg.embed_dims,
        cfg.storage_path,
    )
    return Memory.from_config(cfg.to_mem0_dict())
