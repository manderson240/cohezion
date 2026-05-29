"""CohezionMemory — workflow-facing memory service over the mem0 adapter.

This is the seam the dynamic/compound workflows call. It exists to make mem0 SAFE
to embed in a long-running loop:

  1. Graceful degradation — a memory layer must NEVER crash the workflow it serves.
     If the `memory` extra is absent, or the local LLM/embedder nodes are offline,
     every call logs once and returns empty / no-ops. (Right now NPU/iGPU are down,
     so this path is live: wiring it in today is a safe no-op that activates when
     nodes return.)
  2. API normalization — mem0 2.0.4 is asymmetric: ``add(..., user_id=x)`` takes a
     top-level kwarg, but ``search``/``get_all`` require ``filters={"user_id": x}``.
     (Verified by dogfood: search with top-level user_id raises ValueError.) Callers
     should not have to know this; remember()/recall() hide it.
  3. Lazy build — the mem0 Memory (and its embedded qdrant store) is constructed on
     first use, not at import, so importing this module is always cheap and safe.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any

from cohezion.memory.mem0_adapter import Mem0Config, build_local_mem0, mem0_available


if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Sequence


logger = logging.getLogger(__name__)


class CohezionMemory:
    """Safe, lazy, workflow-facing wrapper around a local mem0 Memory."""

    _instance: CohezionMemory | None = None

    def __init__(
        self,
        config: Mem0Config | None = None,
        *,
        enabled: bool = True,
        memory: Any | None = None,
        graph: Any | None = None,
    ) -> None:
        self._config = config or Mem0Config()
        self._enabled = enabled
        self._memory = memory  # may be injected (tests) or built lazily
        self._build_attempted = memory is not None
        self._graph = graph  # provenance graph: injected (tests) or built lazily
        self._graph_attempted = graph is not None
        # If the extra is missing, disable up front — no point retrying imports.
        if enabled and memory is None and not mem0_available():
            logger.info("CohezionMemory disabled: mem0 extra not installed (.[memory])")
            self._enabled = False

    @classmethod
    def get_instance(cls) -> CohezionMemory:
        """Process-wide singleton (mirrors SemanticCache.get_instance)."""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    @property
    def available(self) -> bool:
        """True if memory operations can be attempted (extra present + enabled)."""
        return self._enabled

    def _ensure_memory(self) -> Any | None:
        """Lazily build the mem0 Memory; disable self on failure."""
        if not self._enabled:
            return None
        if self._memory is None and not self._build_attempted:
            self._build_attempted = True
            try:
                self._memory = build_local_mem0(self._config)
            except Exception as exc:
                logger.warning("CohezionMemory build failed (%s); disabling memory", exc)
                self._enabled = False
        return self._memory

    def _ensure_graph(self) -> Any | None:
        """Lazily build the SurrealDB provenance graph when opted in; degrade on failure.

        Returns an injected graph as-is. Otherwise builds one only if
        ``config.provenance_graph`` is set. The graph is independent of mem0 — it has
        no extra dependency — so it can be active even when the memory build fails.
        """
        if self._graph is None and not self._graph_attempted and self._config.provenance_graph:
            self._graph_attempted = True
            try:
                from cohezion.memory.surreal_graph import SurrealMemoryGraph

                self._graph = SurrealMemoryGraph(
                    url=self._config.surreal_url,
                    namespace=self._config.surreal_namespace,
                    database=self._config.surreal_database,
                )
            except Exception as exc:  # provenance is optional, never fatal
                logger.warning("provenance graph init failed (%s); continuing without it", exc)
        return self._graph

    def remember(self, messages: Sequence[dict[str, str]] | str, agent_id: str) -> list[dict]:
        """Extract + store salient facts from a turn. Returns extracted facts (or [])."""
        mem = self._ensure_memory()
        if mem is None:
            return []
        try:
            result = mem.add(messages, user_id=agent_id)
        except Exception as exc:
            logger.warning("CohezionMemory.remember failed (%s); skipping", exc)
            return []
        facts = result.get("results", []) if isinstance(result, dict) else []
        # Best-effort provenance: feed the extracted facts to the graph. This must
        # NEVER change remember()'s return or raise — a graph hiccup is invisible here.
        graph = self._ensure_graph()
        if graph is not None and facts:
            try:
                graph.record_facts(agent_id, facts)
            except Exception as exc:  # provenance is best-effort
                logger.warning("provenance record_facts failed (%s); memory unaffected", exc)
        return facts

    def recall(self, query: str, agent_id: str, limit: int = 5) -> list[str]:
        """Semantic-search stored memories for this agent. Returns memory strings (or [])."""
        mem = self._ensure_memory()
        if mem is None:
            return []
        try:
            # mem0 2.0.4: user_id MUST go through filters= here (not a top-level kwarg).
            hits = mem.search(query, filters={"user_id": agent_id}, limit=limit)
        except Exception as exc:
            logger.warning("CohezionMemory.recall failed (%s); returning no memories", exc)
            return []
        results = hits.get("results", []) if isinstance(hits, dict) else []
        return [h.get("memory", "") for h in results if h.get("memory")]

    def provenance(self, agent_id: str, limit: int = 100) -> list[dict]:
        """Return provenance rows (event/memory/prior_memory/fact_id) for an agent.

        Returns [] when the provenance graph is not enabled or is unreachable —
        never raises, mirroring recall()'s graceful-degradation contract.
        """
        graph = self._ensure_graph()
        if graph is None:
            return []
        rows = graph.facts_for_agent(agent_id, limit=limit)
        return rows if isinstance(rows, list) else []
