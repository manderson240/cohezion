"""Knowledge Integrator.

Integrates insights from across Cohezion into the knowledge graph,
enabling semantic understanding and cross-journey learning transfer.
"""

import asyncio
import hashlib
import json
import logging
from collections import defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any

logger = logging.getLogger(__name__)


@dataclass
class ConceptNode:
    """Knowledge graph concept node."""

    id: str
    name: str
    concept_type: str
    properties: dict[str, Any]
    confidence: float
    created_at: datetime
    last_updated: datetime


@dataclass
class Relationship:
    """Knowledge graph relationship."""

    source: str
    target: str
    relation_type: str
    strength: float
    evidence: list[dict]


class KnowledgeIntegrator:
    """
    Integrates insights into the knowledge graph.

    Builds semantic understanding by:
    - Extracting concepts from universe journeys
    - Creating cross-journey learning links
    - Building pattern taxonomies
    - Synthesizing best practices
    """

    def __init__(self, graph_path: str = "data/knowledge"):
        self.graph_path = Path(graph_path)
        self.graph_path.mkdir(parents=True, exist_ok=True)

        self.concepts: dict[str, ConceptNode] = {}
        self.relationships: list[Relationship] = []
        self._load_graph()

    def _load_graph(self) -> None:
        """Load existing knowledge graph."""
        concepts_file = self.graph_path / "concepts.json"
        relations_file = self.graph_path / "relationships.json"

        if concepts_file.exists():
            with open(concepts_file) as f:
                data = json.load(f)
                for c in data:
                    self.concepts[c["id"]] = ConceptNode(**c)

        if relations_file.exists():
            with open(relations_file) as f:
                self.relationships = [Relationship(**r) for r in json.load(f)]

    def _save_graph(self) -> None:
        """Persist knowledge graph."""
        concepts_file = self.graph_path / "concepts.json"
        relations_file = self.graph_path / "relationships.json"

        with open(concepts_file, "w") as f:
            json.dump(
                [
                    {
                        "id": c.id,
                        "name": c.name,
                        "concept_type": c.concept_type,
                        "properties": c.properties,
                        "confidence": c.confidence,
                        "created_at": c.created_at.isoformat(),
                        "last_updated": c.last_updated.isoformat(),
                    }
                    for c in self.concepts.values()
                ],
                f,
                indent=2,
                default=str,
            )

        with open(relations_file, "w") as f:
            json.dump(
                [
                    {
                        "source": r.source,
                        "target": r.target,
                        "relation_type": r.relation_type,
                        "strength": r.strength,
                        "evidence": r.evidence,
                    }
                    for r in self.relationships
                ],
                f,
                indent=2,
            )

    async def extract_concepts_from_journey(self, journey: dict) -> list[ConceptNode]:
        """Extract semantic concepts from a journey."""
        concepts = []

        intent = journey.get("intent", "")
        agent_name = journey.get("agent_name", "")

        # Extract agent capability concept
        agent_id = f"agent:{agent_name}"
        if agent_id not in self.concepts:
            concepts.append(
                ConceptNode(
                    id=agent_id,
                    name=agent_name,
                    concept_type="agent",
                    properties={
                        "journeys": 1,
                        "avg_phi": journey.get("final_phi_score", 0.5),
                    },
                    confidence=0.9,
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                )
            )
        else:
            self.concepts[agent_id].properties["journeys"] += 1
            self.concepts[agent_id].last_updated = datetime.now()

        # Extract intent-based concepts
        intent_words = intent.lower().split()[:5]
        for word in intent_words:
            if len(word) > 3:
                concept_id = f"concept:{word}"
                if concept_id not in self.concepts:
                    concepts.append(
                        ConceptNode(
                            id=concept_id,
                            name=word,
                            concept_type="topic",
                            properties={"occurrences": 1},
                            confidence=0.6,
                            created_at=datetime.now(),
                            last_updated=datetime.now(),
                        )
                    )
                else:
                    self.concepts[concept_id].properties["occurrences"] += 1
                    self.concepts[concept_id].last_updated = datetime.now()

        return concepts

    async def build_concept_taxonomy(
        self, patterns: list[dict]
    ) -> dict[str, list[str]]:
        """Build taxonomy from discovered patterns."""
        taxonomy: dict[str, list[str]] = defaultdict(list)

        for pattern in patterns:
            ptype = pattern.get("type", "unknown")
            file_path = pattern.get("file", "")

            # Extract domain from file path
            if "swarm" in file_path:
                domain = "agent"
            elif "meta" in file_path:
                domain = "meta_programming"
            elif "universe" in file_path:
                domain = "universe"
            elif "rewards" in file_path:
                domain = "rewards"
            else:
                domain = "core"

            taxonomy[domain].append(ptype)

        # Save taxonomy concepts
        for domain, types in taxonomy.items():
            domain_id = f"domain:{domain}"
            if domain_id not in self.concepts:
                self.concepts[domain_id] = ConceptNode(
                    id=domain_id,
                    name=domain,
                    concept_type="domain",
                    properties={"pattern_count": len(types), "patterns": types},
                    confidence=0.85,
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                )
            else:
                self.concepts[domain_id].properties["pattern_count"] = len(types)

        return dict(taxonomy)

    async def create_learning_links(self, journeys: list[dict]) -> list[Relationship]:
        """Create cross-journey learning relationships."""
        relationships = []

        # Group by similar intent
        intent_groups: dict[str, list[dict]] = defaultdict(list)
        for journey in journeys:
            intent = journey.get("intent", "").lower()[:30]
            intent_groups[intent].append(journey)

        # Create links between successful similar journeys
        for intent, group in intent_groups.items():
            if len(group) >= 2:
                # Sort by phi_score
                sorted_group = sorted(
                    group, key=lambda x: x.get("final_phi_score", 0), reverse=True
                )

                for i, journey in enumerate(sorted_group[1:], 1):
                    better_journey = sorted_group[0]

                    rel = Relationship(
                        source=f"journey:{journey.get('id', journey.get('hash', 'unknown'))}",
                        target=f"journey:{better_journey.get('id', better_journey.get('hash', 'unknown'))}",
                        relation_type="learning_from",
                        strength=0.5 + (0.1 * i),
                        evidence=[
                            {
                                "intent": intent,
                                "phi_comparison": journey.get("final_phi_score", 0),
                                "better_phi": better_journey.get("final_phi_score", 0),
                            }
                        ],
                    )
                    relationships.append(rel)

        self.relationships.extend(relationships)
        logger.info(f"🔗 Created {len(relationships)} learning links")
        return relationships

    async def synthesize_best_practices(self) -> list[dict]:
        """Extract best practices from successful journeys."""
        best_practices = []

        try:
            from cohezion.core.persistence.surreal_client import SurrealClient

            db = SurrealClient()
            await db.connect()

            # Get high-performing journeys
            result = await db.query(
                "SELECT * FROM universe_journey WHERE final_phi_score >= 0.8 ORDER BY final_phi_score DESC LIMIT 20"
            )

            if result:
                # Extract common patterns
                common_intents = []
                common_agents = []

                for journey in result[:20]:
                    intent = journey.get("intent", "")
                    agent = journey.get("agent_name", "")

                    if len(intent) > 10:
                        common_intents.append(intent[:50])
                    if agent:
                        common_agents.append(agent)

                best_practices.append(
                    {
                        "category": "high_performance",
                        "description": "Common traits of high-phi journeys",
                        "patterns": {
                            "avg_intent_length": sum(len(i) for i in common_intents)
                            / max(len(common_intents), 1),
                            "common_agents": list(set(common_agents))[:5],
                            "sample_intents": common_intents[:5],
                        },
                        "confidence": 0.75,
                    }
                )

            await db.close()

        except Exception as e:
            logger.warning(f"Could not synthesize best practices: {e}")

        logger.info(f"📚 Synthesized {len(best_practices)} best practices")
        return best_practices

    async def integrate_synthesis_insights(self, insights: list[dict]) -> None:
        """Integrate synthesis core insights into knowledge graph."""
        for insight in insights:
            insight_id = f"insight:{insight.get('pattern_id', hashlib.md5(str(insight).encode()).hexdigest()[:8])}"

            if insight_id not in self.concepts:
                self.concepts[insight_id] = ConceptNode(
                    id=insight_id,
                    name=insight.get("description", "Unknown insight")[:50],
                    concept_type="synthetic_insight",
                    properties={
                        "type": insight.get("pattern_type"),
                        "impact": insight.get("impact_score"),
                        "confidence": insight.get("confidence"),
                    },
                    confidence=insight.get("confidence", 0.5),
                    created_at=datetime.now(),
                    last_updated=datetime.now(),
                )

        self._save_graph()
        logger.info(f"🧠 Integrated {len(insights)} synthesis insights")

    async def query_knowledge(self, query: str) -> dict[str, Any]:
        """Query the knowledge graph."""
        query_lower = query.lower()

        # Find related concepts
        related: list[dict] = []
        for concept in self.concepts.values():
            if (
                query_lower in concept.name.lower()
                or query_lower in concept.concept_type.lower()
            ):
                related.append(
                    {
                        "id": concept.id,
                        "name": concept.name,
                        "type": concept.concept_type,
                        "properties": concept.properties,
                    }
                )

        # Find related relationships
        related_rels = []
        for rel in self.relationships:
            if query_lower in rel.source.lower() or query_lower in rel.target.lower():
                related_rels.append(
                    {
                        "from": rel.source,
                        "to": rel.target,
                        "type": rel.relation_type,
                        "strength": rel.strength,
                    }
                )

        return {
            "query": query,
            "concepts_found": len(related),
            "relationships_found": len(related_rels),
            "concepts": related[:10],
            "relationships": related_rels[:10],
        }

    async def get_graph_summary(self) -> dict[str, Any]:
        """Get knowledge graph summary."""
        by_type: dict[str, int] = {}
        for concept in self.concepts.values():
            by_type[concept.concept_type] = by_type.get(concept.concept_type, 0) + 1

        return {
            "total_concepts": len(self.concepts),
            "total_relationships": len(self.relationships),
            "by_type": by_type,
            "domains_covered": len(by_type),
        }


async def main():
    """Demo knowledge integration."""
    logging.basicConfig(level=logging.INFO)

    integrator = KnowledgeIntegrator()
    summary = await integrator.get_graph_summary()

    print("\n" + "=" * 60)
    print("🧠 KNOWLEDGE GRAPH SUMMARY")
    print("=" * 60)
    print(json.dumps(summary, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
