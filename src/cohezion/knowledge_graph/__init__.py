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

# Wiring-sweep (2026-06-06): graphrag_engine was a genuine Class-A orphan — ZERO literal
# import edges in production (its lone non-test reference is a STRING in surreal_dba.py's
# canonical_modules metadata, invisible to static analysis). Failure-isolated re-export so a
# broken graphrag import never unbinds the migration symbols above.
try:
    from cohezion.knowledge_graph.graphrag_engine import (
        GraphRAGEngine as GraphRAGEngine,
    )
    from cohezion.knowledge_graph.graphrag_engine import (
        GraphRAGResponse as GraphRAGResponse,
    )
    from cohezion.knowledge_graph.graphrag_engine import (
        RetrievalResult as RetrievalResult,
    )

    __all__ += ["GraphRAGEngine", "GraphRAGResponse", "RetrievalResult"]
except ImportError:
    pass
