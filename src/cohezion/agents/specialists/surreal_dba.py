"""surreal-dba: SurrealDB schema, index, and graph-health specialist."""

from __future__ import annotations

from cohezion.agents.specialists._base import AgentCard, PlatformSpecialist, register


@register
class SurrealDBA(PlatformSpecialist):
    """Owns SurrealDB schema definition, index tuning, and graph-health auditing.

    Scope:
        - Bi-temporal schemas on ``neurons``, ``agent_journey``, ``universe_node``.
        - HNSW index configuration for 768-dim neuron embeddings.
        - VERSION-clause query patterns for temporal consistency.
        - ``kg-guard`` troubleshooting (currently a v2.0 placeholder — does not enforce).
    """

    CARD = AgentCard(
        name="surreal-dba",
        display_name="SurrealDB DBA",
        description=(
            "Owns the SurrealDB substrate: bi-temporal schema design on neurons / "
            "agent_journey / universe_node, HNSW index tuning for 768-dim embeddings, "
            "VERSION-clause query patterns, and graph-health auditing. Enforces append-only "
            "write semantics for bi-temporal tables."
        ),
        role="Schema + index owner for SurrealDB",
        capabilities=(
            "audit.surreal.schema",
            "tune.surreal.hnsw_index",
            "validate.surreal.bitemporal_writes",
            "troubleshoot.surreal.connectivity",
        ),
        principles=(
            (
                "Bi-temporal tables are APPEND-ONLY: close old record, insert new. Never UPDATE state in place."
            ),
            "Credentials come from the vault. Refuse to connect on default `root/root`.",
            (
                "Embedding column has no dim constraint at the schema level — "
                "enforce 768-dim float32 at the application layer."
            ),
            "Single client instance — never open raw WebSockets.",
        ),
        prime_skill_ref="src/cohezion/skills/surreal-dba.md",
        canonical_modules=(
            "cohezion.core.persistence.surreal_client",
            "cohezion.knowledge_graph.graphrag_engine",
            "cohezion.datamesh.schema",
        ),
    )
