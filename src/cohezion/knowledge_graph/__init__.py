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
        UniverseArtifactMigration,
        ArtifactMetadata,
        TrainingRunMetadata,
        MigrationSnapshot,
    )

    __all__ = [
        "UniverseArtifactMigration",
        "ArtifactMetadata",
        "TrainingRunMetadata",
        "MigrationSnapshot",
    ]
except ImportError:
    # Optional: migration service may not be available in all contexts
    __all__ = []
