"""
Knowledge graph module for Cohezion - persistent memory and artifact management.

Contains:
- query_engine: Vault-driven query capabilities
- universe_artifact_migration: SurrealDB schema + migration service
- MISSION_JOURNAL: Historical developments
- KEY_LEARNINGS: Extracted wisdom patterns
"""

try:
    from cohezion.knowledge_graph.universe_artifact_migration import (
        ArtifactMetadata,
        MigrationSnapshot,
        TrainingRunMetadata,
        UniverseArtifactMigration,
    )

    __all__ = [
        "ArtifactMetadata",
        "MigrationSnapshot",
        "TrainingRunMetadata",
        "UniverseArtifactMigration",
    ]
except ImportError:
    # Optional: migration service may not be available in all contexts
    __all__ = []

import contextlib


# Wiring-sweep 2026-06-22: graphrag_engine, query_engine, bidirectional_linker,
# universe_genealogy_migration were genuine import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.knowledge_graph.graphrag_engine import (
        GraphRAGEngine as GraphRAGEngine,
    )
    from cohezion.knowledge_graph.graphrag_engine import (
        GraphRAGResponse as GraphRAGResponse,
    )
    from cohezion.knowledge_graph.graphrag_engine import (
        RetrievalResult as RetrievalResult,
    )

with contextlib.suppress(Exception):
    from cohezion.knowledge_graph.query_engine import (
        KnowledgeGraphQueryEngine as KnowledgeGraphQueryEngine,
    )

with contextlib.suppress(Exception):
    from cohezion.knowledge_graph.bidirectional_linker import (
        KnowledgeGraph as KnowledgeGraph,
    )
    from cohezion.knowledge_graph.bidirectional_linker import (
        get_knowledge_graph as get_knowledge_graph,
    )

with contextlib.suppress(Exception):
    from cohezion.knowledge_graph.universe_genealogy_migration import (
        UniverseGenealogySurvey as UniverseGenealogySurvey,
    )
