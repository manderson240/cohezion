"""Unit and Property Tests for BAML Vault Graph Pipeline.
=========================================================
Verifies referential integrity, AutoHarness bytecode verification,
resilient schema healing, and SurrealDB/Obsidian dual persistence.
"""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

from cohezion.baml.baml_bridge import BAMLRegistry
from cohezion.baml.vault_graph_pipeline import (
    ExtractedEntity,
    ExtractedRelation,
    ObsidianVaultSync,
    SurrealKnowledgeGraphBridge,
    VaultGraphExtraction,
    VaultGraphHarnessVerifier,
    _sanitize_extraction,
    extract_knowledge_graph_from_text,
)


def test_baml_registry_registration():
    """Verify models are registered in central BAMLRegistry."""
    assert BAMLRegistry.get("ExtractedEntity") is ExtractedEntity
    assert BAMLRegistry.get("ExtractedRelation") is ExtractedRelation
    assert BAMLRegistry.get("VaultGraphExtraction") is VaultGraphExtraction


def test_autoharness_verifier_valid_extraction():
    """Verify AutoHarness passes a sound extraction."""
    extraction = VaultGraphExtraction(
        source_document="00-MOCs/000_Master_Transcendence_MOC.md",
        coherence_score=0.95,
        entities=[
            ExtractedEntity(
                id="hiho-stability",
                name="HIHO Stability Protocol",
                entity_type="protocol",
                summary="Half-in-half-out 0.50 coherence rule",
                tags=["physics", "hiho"],
            ),
            ExtractedEntity(
                id="orch-or",
                name="Orch-OR Quantum Collapse",
                entity_type="theory",
                summary="Objective reduction in microtubules",
                tags=["quantum", "consciousness"],
            ),
        ],
        relations=[
            ExtractedRelation(
                source_id="hiho-stability",
                target_id="orch-or",
                relation_type="governs",
                confidence=0.92,
                weight=0.88,
                rationale="HIHO 0.50 coherence anchors Orch-OR objective reduction boundary.",
            )
        ],
    )

    valid, violations = VaultGraphHarnessVerifier.verify(extraction)
    assert valid is True
    assert len(violations) == 0


def test_autoharness_verifier_flags_violations():
    """Verify AutoHarness detects dangling relations, empty names, and out-of-bound scores."""
    invalid_extraction = VaultGraphExtraction(
        source_document="test_doc.md",
        coherence_score=1.5,  # Out of bounds
        entities=[
            ExtractedEntity(
                id="valid-node",
                name="",  # Empty name
                entity_type="concept",
            )
        ],
        relations=[
            ExtractedRelation(
                source_id="valid-node",
                target_id="missing-node",  # Dangling target
                relation_type="depends_on",
                confidence=1.2,  # Out of bounds
            ),
            ExtractedRelation(
                source_id="valid-node",
                target_id="valid-node",  # Illegal self loop
                relation_type="relates_to",
            ),
        ],
    )

    valid, violations = VaultGraphHarnessVerifier.verify(invalid_extraction)
    assert valid is False
    assert any("coherence_score" in v for v in violations)
    assert any("empty name" in v for v in violations)
    assert any("unknown target_id 'missing-node'" in v for v in violations)
    assert any("illegal self-loop" in v for v in violations)
    assert any("invalid confidence" in v for v in violations)


def test_sanitize_extraction_recovers_valid_graph():
    """Verify sanitizer purges invalid edges and clamps bounds."""
    invalid_extraction = VaultGraphExtraction(
        source_document="test_doc.md",
        coherence_score=1.8,
        entities=[
            ExtractedEntity(id="e1", name="Entity 1"),
            ExtractedEntity(id="e2", name="Entity 2"),
            ExtractedEntity(id="", name="Empty ID"),
        ],
        relations=[
            ExtractedRelation(source_id="e1", target_id="e2", confidence=0.8),
            ExtractedRelation(source_id="e1", target_id="nonexistent", confidence=0.9),
            ExtractedRelation(source_id="e1", target_id="e1", confidence=0.5),  # Self-loop
        ],
    )

    sanitized = _sanitize_extraction(invalid_extraction)
    valid, violations = VaultGraphHarnessVerifier.verify(sanitized)
    assert valid is True
    assert len(violations) == 0
    assert sanitized.coherence_score == 1.0
    assert len(sanitized.entities) == 2
    assert len(sanitized.relations) == 1
    assert sanitized.relations[0].target_id == "e2"


def test_obsidian_markdown_sync_and_file_update():
    """Verify rendering of Obsidian backlinks and updating markdown file."""
    extraction = VaultGraphExtraction(
        source_document="note.md",
        coherence_score=0.98,
        entities=[
            ExtractedEntity(
                id="poincare-manifold",
                name="Poincaré Ball Manifold",
                entity_type="architecture",
                summary="Hyperbolic latent space embedding",
                tags=["geometry", "poincare"],
            )
        ],
        relations=[],
    )

    rendered = ObsidianVaultSync.render_markdown_section(extraction)
    assert "## Knowledge Graph Connections (BAML-Extracted)" in rendered
    assert "[[Poincaré Ball Manifold]]" in rendered
    assert "#geometry" in rendered

    with tempfile.NamedTemporaryFile("w+", suffix=".md", delete=False) as tf:
        tf.write("# Existing Note\nSome initial content.\n")
        temp_path = tf.name

    try:
        success = ObsidianVaultSync.sync_to_file(temp_path, extraction)
        assert success is True
        content = Path(temp_path).read_text(encoding="utf-8")
        assert "## Knowledge Graph Connections (BAML-Extracted)" in content
        assert "[[Poincaré Ball Manifold]]" in content
    finally:
        Path(temp_path).unlink(missing_ok=True)


def test_surreal_knowledge_graph_bridge_persistence():
    """Verify SurrealDB persistence generates valid UPSERT and RELATE queries."""
    extraction = VaultGraphExtraction(
        source_document="note.md",
        coherence_score=0.90,
        entities=[
            ExtractedEntity(id="node_a", name="Node A"),
            ExtractedEntity(id="node_b", name="Node B"),
        ],
        relations=[
            ExtractedRelation(
                source_id="node_a",
                target_id="node_b",
                relation_type="governs",
                confidence=0.95,
            )
        ],
    )

    bridge = SurrealKnowledgeGraphBridge()
    with patch.object(bridge, "_sql", return_value=[{"result": "ok"}]) as mock_sql:
        stats = bridge.persist(extraction)
        assert stats["entities_persisted"] == 2
        assert stats["edges_persisted"] == 1
        assert mock_sql.call_count == 3
        # Check first query is UPSERT
        upsert_query = mock_sql.call_args_list[0][0][0]
        assert "UPSERT `knowledge_entity`:`node_a`" in upsert_query
        # Check third query is RELATE
        relate_query = mock_sql.call_args_list[2][0][0]
        assert "RELATE `knowledge_entity`:`node_a` -> `relates_to`:" in relate_query


def test_extract_knowledge_graph_from_text_with_thinking_model():
    """Verify LLM extraction with resilient parsing stripping <think> tags."""
    raw_llm_response = """
    <think>
    We need to extract the entities and relations according to the VaultGraphExtraction schema.
    Entity 1: Autopoietic Memory
    Entity 2: SurrealDB
    Relation: Autopoietic Memory uses SurrealDB
    </think>
    ```json
    {
      "source_document": "autopoietic_memory.md",
      "coherence_score": 0.99,
      "entities": [
        {
          "id": "autopoietic-memory",
          "name": "Autopoietic Memory",
          "entity_type": "architecture",
          "summary": "Self-healing biological memory fabric",
          "tags": ["memory", "healing"]
        },
        {
          "id": "surrealdb",
          "name": "SurrealDB Persistence",
          "entity_type": "database",
          "summary": "Multi-model graph and document database",
          "tags": ["database", "graph"]
        }
      ],
      "relations": [
        {
          "source_id": "autopoietic-memory",
          "target_id": "surrealdb",
          "relation_type": "implements",
          "confidence": 0.95,
          "weight": 0.90,
          "rationale": "SurrealDB provides graph storage for autopoietic memory."
        }
      ]
    }
    ```
    """
    mock_llm = MagicMock(return_value=raw_llm_response)
    extraction = extract_knowledge_graph_from_text(
        document_text="Some document text",
        doc_name="autopoietic_memory.md",
        llm_callable=mock_llm,
    )

    assert extraction.source_document == "autopoietic_memory.md"
    assert len(extraction.entities) == 2
    assert extraction.entities[0].id == "autopoietic-memory"
    assert len(extraction.relations) == 1
    assert extraction.relations[0].relation_type == "implements"
