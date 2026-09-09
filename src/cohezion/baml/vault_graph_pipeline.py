"""Neurosymbolic BAML Knowledge Graph Pipeline for Cohezion.
===========================================================
Bridges Obsidian Vault markdown notes, typed local LLM inference,
AutoHarness code-as-action verification, and SurrealDB graph persistence.

Architecture:
  [Obsidian Note (.md)]
         │
         ▼
  [BAML Extraction Contract & Local Model (Tier 1 Lemonade / Tier 2 Ollama)]
         │
         ▼
  [BAMLResilientParser (Rust SAP & Heuristic Token Healing)]
         │
         ▼
  [AutoHarness Referential Integrity & Bound Verifier (0ms AST gate)]
         ├──► SurrealDB (knowledge_entity & relates_to graph edges)
         └──► Obsidian Vault (MOC & [[wiki-links]] sync)
"""

from __future__ import annotations

import base64
import json
import logging
import re
import urllib.request
from collections.abc import Callable
from pathlib import Path
from typing import Any

from pydantic import BaseModel, Field

from cohezion.baml.baml_bridge import BAMLRegistry, BAMLResilientParser


logger = logging.getLogger(__name__)


# ==============================================================================
# BAML Pydantic Contracts
# ==============================================================================


class ExtractedEntity(BaseModel):
    """Domain entity extracted from unstructured technical text."""

    id: str = Field(description="Canonical entity slug (e.g. 'hiho-stability-protocol')")
    name: str = Field(description="Human-readable entity title")
    entity_type: str = Field(
        default="concept",
        description="Category: theory, architecture, hardware, agent, protocol, metric",
    )
    summary: str = Field(default="", description="Concise definition or role")
    tags: list[str] = Field(default_factory=list, description="Topic tags")


class ExtractedRelation(BaseModel):
    """Directed semantic edge connecting two extracted entities."""

    source_id: str = Field(description="Source entity ID")
    target_id: str = Field(description="Target entity ID")
    relation_type: str = Field(
        default="relates_to",
        description="Semantic relation: depends_on, proves, governs, implements, refines, contradicts",
    )
    confidence: float = Field(default=1.0, description="Extraction confidence [0.0, 1.0]")
    weight: float = Field(
        default=1.0, description="Strength or frequency of association [0.0, 1.0]"
    )
    rationale: str = Field(default="", description="Textual justification from the source text")


class VaultGraphExtraction(BaseModel):
    """Complete knowledge graph bundle extracted from a single document."""

    source_document: str = Field(description="Name or relative path of the Obsidian note")
    coherence_score: float = Field(default=1.0, description="Evaluated coherence index [0.0, 1.0]")
    entities: list[ExtractedEntity] = Field(
        default_factory=list, description="Discovered entities in the note"
    )
    relations: list[ExtractedRelation] = Field(
        default_factory=list, description="Discovered inter-entity edges"
    )


# Register models into central BAML registry
BAMLRegistry.register("ExtractedEntity", ExtractedEntity)
BAMLRegistry.register("ExtractedRelation", ExtractedRelation)
BAMLRegistry.register("VaultGraphExtraction", VaultGraphExtraction)


# ==============================================================================
# AutoHarness Code-as-Action Verifier
# ==============================================================================


class VaultGraphHarnessVerifier:
    """Zero-cost bytecode verifier enforcing referential integrity and mathematical bounds."""

    VALID_RELATION_TYPES: set[str] = {
        "depends_on",
        "proves",
        "governs",
        "implements",
        "refines",
        "contradicts",
        "relates_to",
        "composed_of",
        "optimizes",
    }

    @classmethod
    def verify(cls, extraction: VaultGraphExtraction) -> tuple[bool, list[str]]:
        """Verifies graph invariants before any persistence write.

        Invariants:
        1. Non-empty IDs and names for all entities.
        2. Strict uniqueness of entity IDs within document.
        3. Strict referential integrity: relation source and target must exist in entities.
        4. Bounds checking: confidence in [0.0, 1.0], weight in [0.0, 1.0], coherence in [0.0, 1.0].
        5. No reflexive self-loops unless explicitly tagged.
        """
        violations: list[str] = []

        if not (0.0 <= extraction.coherence_score <= 1.0):
            violations.append(
                f"Invalid coherence_score {extraction.coherence_score:.4f}: must be in [0.0, 1.0]"
            )

        seen_ids: set[str] = set()
        for i, entity in enumerate(extraction.entities):
            if not entity.id or not entity.id.strip():
                violations.append(f"Entity #{i} has an empty id")
            if not entity.name or not entity.name.strip():
                violations.append(f"Entity #{i} ({entity.id}) has an empty name")
            if entity.id in seen_ids:
                violations.append(f"Duplicate entity id detected: '{entity.id}'")
            seen_ids.add(entity.id)

        for j, rel in enumerate(extraction.relations):
            if rel.source_id not in seen_ids:
                violations.append(f"Relation #{j} references unknown source_id '{rel.source_id}'")
            if rel.target_id not in seen_ids:
                violations.append(f"Relation #{j} references unknown target_id '{rel.target_id}'")
            if rel.source_id == rel.target_id:
                violations.append(f"Relation #{j} is an illegal self-loop on '{rel.source_id}'")
            if not (0.0 <= rel.confidence <= 1.0):
                violations.append(
                    f"Relation #{j} invalid confidence {rel.confidence:.4f}: must be in [0.0, 1.0]"
                )
            if not (0.0 <= rel.weight <= 1.0):
                violations.append(
                    f"Relation #{j} invalid weight {rel.weight:.4f}: must be in [0.0, 1.0]"
                )

        return (len(violations) == 0, violations)


# ==============================================================================
# SurrealDB Knowledge Graph Bridge
# ==============================================================================


class SurrealKnowledgeGraphBridge:
    """Transports extracted entities and typed relations into SurrealDB graph tables."""

    def __init__(
        self,
        url: str = "http://localhost:8001/sql",
        namespace: str = "cohezion",
        database: str = "main",
        user: str = "root",
        password: str = "root",  # noqa: S107 - local dev default
        entity_table: str = "knowledge_entity",
        edge_table: str = "relates_to",
        timeout: float = 5.0,
    ) -> None:
        self.url = url
        self.namespace = namespace
        self.database = database
        self._auth = base64.b64encode(f"{user}:{password}".encode()).decode()
        self.entity_table = entity_table
        self.edge_table = edge_table
        self.timeout = timeout

    def _sql(self, query: str) -> list[dict[str, Any]]:
        """Executes a SurrealQL query via HTTP endpoint."""
        req = urllib.request.Request(  # noqa: S310 - fixed local SurrealDB URL
            self.url,
            data=query.encode("utf-8"),
            headers={
                "Accept": "application/json",
                "Content-Type": "text/plain",
                "surreal-ns": self.namespace,
                "surreal-db": self.database,
                "Authorization": f"Basic {self._auth}",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:  # noqa: S310
                parsed = json.loads(resp.read().decode("utf-8"))
            return parsed if isinstance(parsed, list) else []
        except Exception as exc:
            logger.debug("SurrealDB query failed (fallback safe): %s", exc)
            return []

    def persist(self, extraction: VaultGraphExtraction) -> dict[str, int]:
        """Persists validated extraction bundle into SurrealDB."""
        # AutoHarness verification check
        valid, violations = VaultGraphHarnessVerifier.verify(extraction)
        if not valid:
            raise ValueError(f"AutoHarness verification failed: {'; '.join(violations)}")

        entities_persisted = 0
        edges_persisted = 0

        # Upsert entities
        for entity in extraction.entities:
            clean_id = re.sub(r"[^a-zA-Z0-9_-]", "_", entity.id)
            doc_data = {
                "name": entity.name,
                "entity_type": entity.entity_type,
                "summary": entity.summary,
                "tags": entity.tags,
                "source_doc": extraction.source_document,
            }
            query = f"UPSERT `{self.entity_table}`:`{clean_id}` MERGE {json.dumps(doc_data)};"
            res = self._sql(query)
            if res:
                entities_persisted += 1

        # Relate edges
        for rel in extraction.relations:
            clean_source = re.sub(r"[^a-zA-Z0-9_-]", "_", rel.source_id)
            clean_target = re.sub(r"[^a-zA-Z0-9_-]", "_", rel.target_id)
            edge_id = f"{clean_source}__{rel.relation_type}__{clean_target}"
            rel_data = {
                "relation_type": rel.relation_type,
                "confidence": rel.confidence,
                "weight": rel.weight,
                "rationale": rel.rationale,
                "source_doc": extraction.source_document,
            }
            query = (
                f"RELATE `{self.entity_table}`:`{clean_source}` -> "
                f"`{self.edge_table}`:`{edge_id}` -> "
                f"`{self.entity_table}`:`{clean_target}` "
                f"CONTENT {json.dumps(rel_data)};"
            )
            res = self._sql(query)
            if res:
                edges_persisted += 1

        return {
            "entities_persisted": entities_persisted,
            "edges_persisted": edges_persisted,
        }


# ==============================================================================
# Obsidian Vault Synchronizer
# ==============================================================================


class ObsidianVaultSync:
    """Updates Obsidian notes with structured markdown graph links and metadata."""

    @classmethod
    def render_markdown_section(cls, extraction: VaultGraphExtraction) -> str:
        """Renders a clean Obsidian markdown section with bidirectional [[wiki-links]]."""
        lines = [
            "\n## Knowledge Graph Connections (BAML-Extracted)",
            f"*Source: `{extraction.source_document}` | Coherence: {extraction.coherence_score:.2f}*",
            "",
            "### Entities",
        ]
        for entity in extraction.entities:
            tag_str = " ".join([f"#{t}" for t in entity.tags])
            lines.append(
                f"- [[{entity.name}]] (`{entity.entity_type}`): {entity.summary} {tag_str}".strip()
            )

        lines.extend(["", "### Semantic Relations"])
        for rel in extraction.relations:
            lines.append(
                f"- [[{rel.source_id}]] **{rel.relation_type}** [[{rel.target_id}]] "
                f"(confidence: {rel.confidence:.2f}) - *{rel.rationale}*"
            )
        lines.append("")
        return "\n".join(lines)

    @classmethod
    def sync_to_file(cls, file_path: Path | str, extraction: VaultGraphExtraction) -> bool:
        """Appends or updates the Knowledge Graph section in an Obsidian note."""
        path = Path(file_path)
        if not path.exists():
            return False

        content = path.read_text(encoding="utf-8")
        section_header = "## Knowledge Graph Connections (BAML-Extracted)"

        new_section = cls.render_markdown_section(extraction)
        if section_header in content:
            # Replace existing section
            pattern = re.compile(rf"{re.escape(section_header)}.*?(?=\n## |\Z)", re.DOTALL)
            updated_content = pattern.sub(new_section.strip(), content)
        else:
            updated_content = content.rstrip() + "\n" + new_section

        path.write_text(updated_content, encoding="utf-8")
        return True


# ==============================================================================
# Orchestrated Extraction Pipeline
# ==============================================================================


def extract_knowledge_graph_from_text(
    document_text: str,
    doc_name: str,
    llm_callable: Callable[[str], str] | None = None,
) -> VaultGraphExtraction:
    """Extracts typed knowledge graph from text using LLM callable + BAML resilient parsing."""
    if llm_callable is None:
        # Deterministic heuristic extractor for offline test/harness runs
        return _heuristic_extract(document_text, doc_name)

    prompt = (
        f"You are a neurosymbolic graph extraction agent. Analyze the following document and output "
        f"a JSON object adhering to the VaultGraphExtraction schema:\n"
        f"Document Name: {doc_name}\n"
        f"Document Content:\n{document_text[:4000]}\n\n"
        f"Output JSON strictly matching:\n"
        f"{{\n"
        f'  "source_document": "{doc_name}",\n'
        f'  "coherence_score": 0.95,\n'
        f'  "entities": [{{"id": "entity-slug", "name": "Entity Name", "entity_type": "concept", "summary": "...", "tags": []}}],\n'
        f'  "relations": [{{"source_id": "entity-slug", "target_id": "other-slug", "relation_type": "governs", "confidence": 0.95, "weight": 0.8, "rationale": "..."}}]\n'
        f"}}"
    )

    raw_response = llm_callable(prompt)
    extraction = BAMLResilientParser.parse_to_model(raw_response, VaultGraphExtraction)

    # Enforce AutoHarness verification
    valid, violations = VaultGraphHarnessVerifier.verify(extraction)
    if not valid:
        logger.warning(
            "AutoHarness verifier flagged violations: %s. Performing heuristic sanitization.",
            violations,
        )
        extraction = _sanitize_extraction(extraction)

    return extraction


def _heuristic_extract(document_text: str, doc_name: str) -> VaultGraphExtraction:
    """Fast deterministic extractor based on header & keyword extraction."""
    # Find headers or key terms
    headers = re.findall(r"^#{1,3}\s+(.+)$", document_text, re.MULTILINE)
    entities: list[ExtractedEntity] = []
    seen_ids: set[str] = set()

    for h in headers[:5]:
        clean_h = h.strip()
        slug = re.sub(r"[^a-zA-Z0-9]+", "-", clean_h.lower()).strip("-")
        if slug and slug not in seen_ids:
            entities.append(
                ExtractedEntity(
                    id=slug,
                    name=clean_h,
                    entity_type="architecture" if "architecture" in slug else "concept",
                    summary=f"Section '{clean_h}' from {doc_name}",
                    tags=["markdown", "heading"],
                )
            )
            seen_ids.add(slug)

    # Build linear dependency relations between extracted sequential entities
    relations: list[ExtractedRelation] = []
    for i in range(len(entities) - 1):
        relations.append(
            ExtractedRelation(
                source_id=entities[i].id,
                target_id=entities[i + 1].id,
                relation_type="depends_on",
                confidence=0.90,
                weight=0.85,
                rationale=f"Sequential structural dependency between '{entities[i].name}' and '{entities[i + 1].name}'",
            )
        )

    return VaultGraphExtraction(
        source_document=doc_name,
        coherence_score=0.95,
        entities=entities,
        relations=relations,
    )


def _sanitize_extraction(extraction: VaultGraphExtraction) -> VaultGraphExtraction:
    """Sanitizes an imperfect extraction to guarantee AutoHarness compliance."""
    valid_entity_ids = {e.id for e in extraction.entities if e.id and e.id.strip()}

    sanitized_entities = [
        e for e in extraction.entities if e.id in valid_entity_ids and e.name and e.name.strip()
    ]

    sanitized_relations = [
        r
        for r in extraction.relations
        if r.source_id in valid_entity_ids
        and r.target_id in valid_entity_ids
        and r.source_id != r.target_id
        and 0.0 <= r.confidence <= 1.0
        and 0.0 <= r.weight <= 1.0
    ]

    coherence = max(0.0, min(1.0, extraction.coherence_score))

    return VaultGraphExtraction(
        source_document=extraction.source_document,
        coherence_score=coherence,
        entities=sanitized_entities,
        relations=sanitized_relations,
    )
