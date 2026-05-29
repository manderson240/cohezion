"""SurrealDB provenance graph for mem0 memories.

Honest scope: this is a memory **provenance graph** — it records WHICH agent
remembers WHICH fact, and (the value-add) preserves the text a fact superseded. It
is NOT an entity-relation knowledge graph (entities extracted from text and related
to each other); that remains future work. It is also distinct from the
workflow-execution graph in ``src/cohezion/graph/`` (nodes = workflow steps).

Why it isn't redundant with the vector store: ``SurrealVectorStore`` already records
``payload.user_id``, so an agent->fact edge alone would just duplicate a filter. The
justification for a graph layer is what the flat store LOSES — mem0's UPDATE
consolidation overwrites a fact in place (same id), discarding the prior text. This
graph captures that prior text on the provenance edge, so the consolidation lineage
survives.

Convention reuse: follows the SurrealDB edge-table RELATE pattern already used by
``WorkflowPersistence.get_schema_statements()`` (in/out record fields, queried via
the edge table). Deterministic edge ids (``<agent>__<fact>``) make RELATE idempotent
— replaying a turn updates the edge in place instead of duplicating it.

Dependency-free transport: stdlib urllib over HTTP /sql, so the module adds no
packages and can't fail to import. Every write is best-effort — a graph failure must
never crash the memory layer or the workflow it serves (callers get a bool/0, never
an exception).
"""

from __future__ import annotations

import base64
import json
import logging
import urllib.request
from typing import TYPE_CHECKING


if TYPE_CHECKING:  # pragma: no cover - typing only
    from collections.abc import Iterable, Sequence


logger = logging.getLogger(__name__)


class SurrealMemoryGraph:
    """Best-effort provenance edges (agent -[remembers]-> fact) in SurrealDB."""

    def __init__(
        self,
        url: str = "http://localhost:8001/sql",
        namespace: str = "cohezion",
        database: str = "main",
        user: str = "root",
        password: str = "root",  # noqa: S107 - local SurrealDB dev default; override in prod
        *,
        agent_table: str = "mem_agent",
        fact_table: str = "mem_fact",
        edge_table: str = "mem_remembers",
        timeout: float = 10.0,
    ) -> None:
        self.url = url
        self.namespace = namespace
        self.database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.agent_table = agent_table
        self.fact_table = fact_table
        self.edge_table = edge_table
        self._timeout = timeout

    # ── transport ────────────────────────────────────────────────────────────
    def _sql(self, query: str) -> list[dict]:
        req = urllib.request.Request(  # noqa: S310 - fixed localhost SurrealDB URL
            self.url,
            data=query.encode(),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "surreal-ns": self.namespace,
                "surreal-db": self.database,
                "Authorization": f"Basic {self._auth}",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self._timeout) as resp:  # noqa: S310
            return json.loads(resp.read().decode())

    @staticmethod
    def _last_result(resp: list[dict]) -> list:
        if not resp:
            return []
        tail = resp[-1]
        res = tail.get("result", []) if isinstance(tail, dict) else []
        return res if isinstance(res, list) else [res]

    @staticmethod
    def _ref(table: str, rid: str) -> str:
        """Backtick record reference `table`:`id` (handles ids with hyphens)."""
        return f"`{table.replace('`', '')}`:`{str(rid).replace('`', '')}`"

    # ── writes (best-effort) ─────────────────────────────────────────────────
    def link(
        self,
        agent_id: str,
        fact_id: str,
        *,
        memory: str = "",
        event: str = "ADD",
        prior_memory: str | None = None,
    ) -> bool:
        """RELATE agent -> fact with provenance on the edge. Idempotent per (agent,fact).

        Returns True on success, False on any failure (logged once, never raised).
        """
        edge_id = f"{agent_id}__{fact_id}"
        prior = json.dumps(prior_memory) if prior_memory else "NONE"
        q = (
            f"RELATE {self._ref(self.agent_table, agent_id)} -> "
            f"{self._ref(self.edge_table, edge_id)} -> {self._ref(self.fact_table, fact_id)} "
            f"SET event = {json.dumps(event)}, memory = {json.dumps(memory)}, "
            f"prior_memory = {prior}, updated_at = time::now();"
        )
        try:
            self._sql(q)
        except Exception as exc:  # provenance must never crash the caller
            logger.warning("SurrealMemoryGraph.link failed (%s); skipping edge", exc)
            return False
        return True

    def record_facts(self, agent_id: str, facts: Iterable[dict]) -> int:
        """Write a provenance edge for each mem0 fact dict. Returns edges written.

        Accepts mem0's ``add()`` result entries: ``{id, memory, event, [previous_memory]}``.
        Facts without an ``id`` are skipped. UPDATE events preserve ``previous_memory``
        on the edge so the superseded text is not lost.
        """
        written = 0
        for fact in facts:
            fid = fact.get("id")
            if not fid:
                continue
            if self.link(
                agent_id,
                str(fid),
                memory=fact.get("memory", ""),
                event=fact.get("event", "ADD"),
                prior_memory=fact.get("previous_memory"),
            ):
                written += 1
        return written

    # ── reads ────────────────────────────────────────────────────────────────
    def facts_for_agent(self, agent_id: str, limit: int = 100) -> list[dict]:
        """Return provenance rows for an agent via the edge table (degrades to [])."""
        q = (
            f"SELECT memory, event, prior_memory, meta::id(out) AS fact_id, updated_at "
            f"FROM {self.edge_table} WHERE in = {self._ref(self.agent_table, agent_id)} "
            f"ORDER BY updated_at DESC LIMIT {int(limit)};"
        )
        try:
            return self._last_result(self._sql(q))
        except Exception as exc:  # reads must never crash the caller
            logger.warning("SurrealMemoryGraph.facts_for_agent failed (%s); returning []", exc)
            return []

    def reset(self) -> None:
        """Drop the provenance tables (test/dev convenience; best-effort)."""
        for table in (self.edge_table, self.agent_table, self.fact_table):
            try:
                self._sql(f"REMOVE TABLE IF EXISTS `{table}`;")
            except Exception as exc:  # best-effort cleanup
                logger.warning("SurrealMemoryGraph.reset(%s) failed (%s)", table, exc)

    @staticmethod
    def schema_statements(
        agent_table: str = "mem_agent",
        fact_table: str = "mem_fact",
        edge_table: str = "mem_remembers",
    ) -> Sequence[str]:
        """SurrealDB DDL for the provenance edge (optional; tables are SCHEMALESS-safe)."""
        return (
            f"DEFINE TABLE IF NOT EXISTS `{edge_table}` SCHEMALESS",
            f"DEFINE FIELD `in` ON TABLE `{edge_table}` TYPE record<`{agent_table}`>",
            f"DEFINE FIELD `out` ON TABLE `{edge_table}` TYPE record<`{fact_table}`>",
            f"DEFINE FIELD event ON TABLE `{edge_table}` TYPE string DEFAULT 'ADD'",
            f"DEFINE FIELD memory ON TABLE `{edge_table}` TYPE string DEFAULT ''",
            f"DEFINE FIELD prior_memory ON TABLE `{edge_table}` TYPE option<string>",
            f"DEFINE FIELD updated_at ON TABLE `{edge_table}` TYPE datetime DEFAULT time::now()",
        )
