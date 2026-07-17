"""Graphify Integration - Transforming documents into knowledge graphs.

This service integrates the Graphify logic (converting unstructured text/PDFs into
triplets of entities and relations) into the Cohezion Knowledge Graph and Vault.

Integration Pipeline:
  Document -> Graphify (LLM Extraction) -> Semantic Triplets -> Cohezion KG/Vault

The integration leverages the Mereon System's geometric coordinates to map
extracted entities to specific topological regimes:
  - High-level concepts -> M120p boundary (E8)
  - Technical specifics -> M144p core (E7)
  - Linking relationships -> Focusing Sphere
"""

from __future__ import annotations

import logging

from pydantic import BaseModel

from cohezion.physics.mereon_projector import MereonProjector


logger = logging.getLogger(__name__)


class GraphEntity(BaseModel):
    """A node in the extracted knowledge graph."""

    name: str
    type: str
    description: str = ""
    coherence: float = 1.0


class GraphRelation(BaseModel):
    """An edge between two entities."""

    source: str
    target: str
    relation: str
    weight: float = 1.0


class GraphifyResult(BaseModel):
    """The complete graph extracted from a document."""

    entities: list[GraphEntity]
    relations: list[GraphRelation]
    document_id: str


class GraphifyService:
    """
    Service to orchestrate the transformation of documents into knowledge graphs.
    """

    def __init__(self, projector: MereonProjector = None):
        self.projector = projector or MereonProjector()

    async def extract_graph(self, content: str, doc_id: str) -> GraphifyResult:
        """
        Transform text content into a knowledge graph.

        In a production environment, this would call the Graphify library
        via a subprocess or API. Here we implement the semantic mapping
        logic to the Cohezion manifold.
        """
        logger.info(f"Graphifying document {doc_id}...")

        # Mocking the Graphify extraction (S, P, O) logic
        # In reality, this uses the LLM-based entity/relation extraction from Graphify
        entities, relations = await self._mock_graphify_extraction(content)

        # Assign geometric coordinates based on the entity's 'coherence'
        # High coherence (abstract) -> Boundary (E8)
        # Low coherence (concrete) -> Core (E7)
        for entity in entities:
            entity.coherence = self._estimate_coherence(entity)
            # We can store the projected vertex as metadata in the KG
            # pos = self.projector.project(...)

        return GraphifyResult(entities=entities, relations=relations, document_id=doc_id)

    # Map free-verb relations onto the EXISTING edge tables (census 2026-07-17:
    # all empty). Unknown verbs land in relates_to rather than spawning tables.
    _EDGE_TABLES = ("informed_by", "led_to", "influences", "similar_to", "derived_from", "adjacent_to")

    _VERB_ROOTS = {
        "inform": "informed_by",
        "led": "led_to",
        "lead": "led_to",
        "influenc": "influences",
        "similar": "similar_to",
        "deriv": "derived_from",
        "adjacent": "adjacent_to",
    }

    @classmethod
    def edge_table_for(cls, relation: str) -> str:
        v = relation.strip().lower().replace(" ", "_")
        if v in cls._EDGE_TABLES:
            return v
        for root, table in cls._VERB_ROOTS.items():
            if v.startswith(root):
                return table
        return "relates_to"

    @staticmethod
    def _slug(name: str) -> str:
        import re as _re

        return _re.sub(r"[^a-z0-9]+", "_", name.lower()).strip("_")[:60] or "unnamed"

    async def ingest_to_vault(self, result: GraphifyResult) -> int:
        """Persist entities + edges into SurrealDB (was log-only until 2026-07-17).

        Entities → kg_entity:⟨slug⟩ (UPSERT); doc→entity via mentions;
        entity→entity via the mapped existing edge tables. Bi-temporal
        valid_from stamped per project convention. Returns edges written.
        """
        import asyncio
        import json as _json
        import urllib.request

        stmts: list[str] = []
        for e in result.entities:
            s = self._slug(e.name)
            stmts.append(
                f"UPSERT kg_entity:⟨{s}⟩ SET name = {_json.dumps(e.name)}, "
                f"type = {_json.dumps(e.type)}, coherence = {e.coherence};"
            )
            stmts.append(
                # vault_memory is the DOCUMENT node table (vault_neuron is telemetry
                # — census correction 2026-07-17); compile_memory_from_vault.py
                # counts ->informed_by/<-led_to edges from these records.
                f"RELATE vault_memory:⟨{result.document_id}⟩ -> mentions -> kg_entity:⟨{s}⟩ "
                f"SET valid_from = time::now(), extractor = 'graphify';"
            )
        for r in result.relations:
            table = self.edge_table_for(r.relation)
            stmts.append(
                f"RELATE kg_entity:⟨{self._slug(r.source)}⟩ -> {table} -> "
                f"kg_entity:⟨{self._slug(r.target)}⟩ SET valid_from = time::now(), "
                f"verb = {_json.dumps(r.relation)}, weight = {r.weight}, "
                f"doc = {_json.dumps(result.document_id)};"
            )
        if not stmts:
            return 0

        def _run() -> int:
            req = urllib.request.Request(
                "http://localhost:8001/sql",  # noqa: S310
                data="".join(stmts).encode(),
                headers={
                    "surreal-ns": "cohezion", "surreal-db": "main",
                    "Content-Type": "text/plain", "Accept": "application/json",
                    "Authorization": "Basic cm9vdDpyb290",
                },
            )
            with urllib.request.urlopen(req, timeout=30) as resp:  # noqa: S310
                results = _json.load(resp)
            return sum(1 for x in results if x.get("status") == "OK")

        ok = await asyncio.to_thread(_run)
        logger.info(
            "graphify: %s — %d/%d statements ok (%d entities, %d relations)",
            result.document_id, ok, len(stmts), len(result.entities), len(result.relations),
        )
        return ok

    def _estimate_coherence(self, entity: GraphEntity) -> float:
        """Estimates coherence based on entity type and name length."""
        if entity.type.lower() in ["concept", "theory", "paradigm"]:
            return 0.9  # E8 Boundary
        if entity.type.lower() in ["variable", "constant", "function"]:
            return 0.3  # E7 Core
        return 0.6  # Focusing Sphere

    async def _mock_graphify_extraction(
        self, content: str
    ) -> tuple[list[GraphEntity], list[GraphRelation]]:
        """LLM-driven extraction via the local router (was a hardcoded mock until
        2026-07-17 — the edge tables sat empty for months; pathway Move 2).

        Model choice: FleetRoster.select("interactive") — the resident heavy
        model per the RAM-policy retarget; extraction inherits fleet policy
        instead of pinning a checkpoint.
        """
        import json as _json
        import re as _re

        try:
            from cohezion.inference.fleet_roles import ROSTER

            model = ROSTER.select("interactive") or "Gemma-4-26B-A4B-it-GGUF"
        except Exception:
            model = "Gemma-4-26B-A4B-it-GGUF"
        prompt = (
            "Extract a knowledge graph from the text. Return ONLY JSON: "
            '{"entities": [{"name": str, "type": str}], '
            '"relations": [{"source": str, "relation": str, "target": str}]}. '
            "Max 8 entities; use short canonical names; relation is a single "
            "lowercase verb phrase (e.g. informed_by, led_to, influences, "
            "similar_to, derived_from, uses, part_of).\n\nTEXT:\n" + content[:6000]
        )
        # Reuse the gauntlet's hardened call path: think-strip, reasoning_content
        # fallback, bounded timeout. (First attempt used raw urllib with 900
        # max_tokens → the thinking-channel 26B burned the whole budget in-think
        # and returned content='' — the exact trap _call_model already solves.)
        from cohezion.inference.gauntlet import _call_model

        _ttft, _tps, text = await _call_model(
            model, prompt, max_tokens=2500, timeout_s=300.0, temperature=0.2
        )
        fenced = _re.findall(r"```(?:json)?\s*(.*?)```", text, _re.DOTALL)
        raw = fenced[-1] if fenced else text
        try:
            data = _json.loads(raw[raw.find("{"): raw.rfind("}") + 1])
        except (ValueError, TypeError):
            logger.warning("graphify: unparseable extraction — returning empty graph")
            return [], []
        entities = [
            GraphEntity(name=str(e.get("name", ""))[:80], type=str(e.get("type", "Concept"))[:40])
            for e in data.get("entities", []) if e.get("name")
        ]
        known = {e.name for e in entities}
        relations = [
            GraphRelation(
                source=str(r.get("source", ""))[:80],
                target=str(r.get("target", ""))[:80],
                relation=str(r.get("relation", "relates_to"))[:40],
            )
            for r in data.get("relations", [])
            if r.get("source") in known and r.get("target") in known
        ]
        return entities, relations
