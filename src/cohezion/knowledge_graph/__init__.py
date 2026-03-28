"""
Knowledge graph module for Cohezion - persistent memory and artifact management.

Contains:
- query_engine: Vault-driven query capabilities
- universe_artifact_migration: SurrealDB schema + migration service
- bidirectional_linker: Knowledge graph with bidirectional links (NEW)
- MISSION_JOURNAL: Historical developments
- KEY_LEARNINGS: Extracted wisdom patterns

Bidirectional Linking (NEW):
    Integrates with Vault + SurrealDB 3.0 for cross-session persistent links.

    Usage:
        from cohezion.knowledge_graph import get_knowledge_graph, link_doc_to_code

        kg = get_knowledge_graph()
        await kg.connect()

        # Link documentation to code
        await link_doc_to_code(
            doc="DESIGN.md",
            code_file="src/cohezion/swarm/tip_of_spear_router.py",
            section="Tip-of-Spear Routing"
        )

        # Get all links for a node
        links = await kg.get_links("DESIGN.md")

        # Find path between nodes
        path = await kg.find_path("DESIGN.md", "tip_of_spear_router.py")
"""

try:
    from cohezion.knowledge_graph.universe_artifact_migration import (
        ArtifactMetadata,
        MigrationSnapshot,
        TrainingRunMetadata,
        UniverseArtifactMigration,
    )

    migration_available = True
except ImportError:
    migration_available = False

try:
    from cohezion.knowledge_graph.bidirectional_linker import (
        BidirectionalLink,
        KnowledgeGraph,
        LinkType,
        get_knowledge_graph,
        link_decision_to_code,
        link_doc_to_code,
        link_doc_to_doc,
        link_pattern_to_code,
        link_skill_to_code,
    )

    bidirectional_available = True
except ImportError:
    bidirectional_available = False


# Build __all__ dynamically based on what's available
__all__ = []

if migration_available:
    __all__ += [
        "ArtifactMetadata",
        "MigrationSnapshot",
        "TrainingRunMetadata",
        "UniverseArtifactMigration",
    ]

if bidirectional_available:
    __all__ += [
        "BidirectionalLink",
        "KnowledgeGraph",
        "LinkType",
        "get_knowledge_graph",
        "link_decision_to_code",
        "link_doc_to_code",
        "link_doc_to_doc",
        "link_pattern_to_code",
        "link_skill_to_code",
    ]
