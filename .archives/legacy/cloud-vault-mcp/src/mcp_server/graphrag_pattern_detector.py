"""
Pattern Auto-Detection for GraphRAG

Automatically identifies reusable patterns from graph relationships.
Finds patterns referenced 3+ times and suggests new pattern extraction
from similar decisions/experiments.

Version History:
- v1.0 (2026-02-13): Initial implementation with usage analysis, similarity detection

Usage:
    detector = PatternDetector(vault_path, surreal_client)
    await detector.detect_patterns(min_usage=3)
"""

import logging
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .graphrag_helpers import GraphRAGError, execute_surreal_async
from .graphrag_query import GraphRAGQuery


logger = logging.getLogger(__name__)


@dataclass
class PatternUsage:
    """Pattern with usage statistics"""

    pattern_id: str
    title: str
    path: str
    content: str
    usage_count: int
    referenced_by: list[str]  # Document IDs that reference this pattern
    used_in: list[str]  # Document IDs where pattern was used
    informed_by: list[str]  # Document IDs that informed this pattern
    total_impact: int  # Sum of all relationship types


@dataclass
class PatternSuggestion:
    """Suggested pattern extraction from similar documents"""

    suggested_title: str
    similarity_score: float
    source_docs: list[str]  # Document IDs with similar outcomes
    common_themes: list[str]  # Shared keywords/concepts
    rationale: str


class PatternDetector:
    """Auto-detect reusable patterns from GraphRAG"""

    def __init__(
        self,
        vault_path: Path,
        surrealdb_url: str = "http://localhost:8001",
        namespace: str = "cohezion",
        database: str = "vault",
    ):
        self.vault_path = vault_path
        self.surrealdb_url = surrealdb_url
        self.namespace = namespace
        self.database = database
        self.query_engine = GraphRAGQuery(
            surrealdb_url=surrealdb_url, namespace=namespace, database=database
        )

    async def __aenter__(self):
        await self.query_engine.__aenter__()
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.query_engine.__aexit__(exc_type, exc_val, exc_tb)

    async def detect_patterns(
        self, min_usage: int = 3, max_results: int = 20
    ) -> list[PatternUsage]:
        """
        Detect high-usage patterns from graph relationships.

        Args:
            min_usage: Minimum reference count (default: 3)
            max_results: Maximum patterns to return

        Returns:
            List of PatternUsage ordered by total impact

        Raises:
            GraphRAGError: If query fails
        """
        try:
            # Query for patterns with usage counts
            query = f"""
            SELECT
                id,
                title,
                path,
                content,
                count(<-used_in) AS used_in_count,
                count(<-informed_by) AS informed_by_count,
                count(<-led_to) AS led_to_count,
                array::distinct(<-used_in<-vault_memory.id) AS used_in_docs,
                array::distinct(<-informed_by<-vault_memory.id) AS informed_by_docs,
                array::distinct(<-led_to<-vault_memory.id) AS led_to_docs
            FROM vault_memory
            WHERE type = 'pattern'
            ORDER BY (used_in_count + informed_by_count + led_to_count) DESC
            LIMIT {max_results};
            """

            results = await execute_surreal_async(
                query, self.surrealdb_url, self.namespace, self.database
            )

            if not results or not results[0].get("result"):
                logger.warning("No patterns found in graph")
                return []

            patterns = []
            for row in results[0]["result"]:
                # Calculate total impact
                used_in = row.get("used_in_count", 0)
                informed_by = row.get("informed_by_count", 0)
                led_to = row.get("led_to_count", 0)
                total_impact = used_in + informed_by + led_to

                # Filter by min_usage
                if total_impact < min_usage:
                    continue

                # Extract document IDs (handle potential None values)
                used_in_docs = row.get("used_in_docs") or []
                informed_by_docs = row.get("informed_by_docs") or []
                led_to_docs = row.get("led_to_docs") or []

                pattern = PatternUsage(
                    pattern_id=row["id"],
                    title=row.get("title", "Untitled"),
                    path=row.get("path", ""),
                    content=row.get("content", "")[:200],  # Preview only
                    usage_count=used_in,
                    referenced_by=informed_by_docs,
                    used_in=used_in_docs,
                    informed_by=led_to_docs,
                    total_impact=total_impact,
                )
                patterns.append(pattern)

            logger.info(
                f"Detected {len(patterns)} patterns with ≥{min_usage} references"
            )
            return patterns

        except Exception as e:
            logger.error(f"Pattern detection failed: {e}")
            raise GraphRAGError(f"Pattern detection failed: {e}") from e

    async def suggest_patterns(
        self, min_similarity: float = 0.7, max_suggestions: int = 10
    ) -> list[PatternSuggestion]:
        """
        Suggest pattern extraction from similar decisions/experiments.

        Finds groups of documents with similar outcomes that could be
        abstracted into reusable patterns.

        Args:
            min_similarity: Minimum cosine similarity threshold
            max_suggestions: Maximum suggestions to return

        Returns:
            List of PatternSuggestion ordered by similarity

        Raises:
            GraphRAGError: If query fails
        """
        try:
            # Find decisions/experiments without corresponding patterns
            query = """
            SELECT
                id,
                title,
                type,
                content,
                embedding,
                tags
            FROM vault_memory
            WHERE type IN ['decision', 'experiment']
              AND count(->led_to->vault_memory[WHERE type = 'pattern']) = 0
            ORDER BY time::now() - created_at DESC
            LIMIT 50;
            """

            results = await execute_surreal_async(
                query, self.surrealdb_url, self.namespace, self.database
            )

            if not results or not results[0].get("result"):
                logger.warning("No unpatternized documents found")
                return []

            docs = results[0]["result"]

            # Group by semantic similarity
            suggestions = []
            seen_docs = set()

            for i, doc1 in enumerate(docs):
                if doc1["id"] in seen_docs:
                    continue

                similar_group = [doc1]
                doc1_embedding = doc1.get("embedding")

                if not doc1_embedding:
                    continue

                # Find similar documents
                for doc2 in docs[i + 1 :]:
                    if doc2["id"] in seen_docs:
                        continue

                    doc2_embedding = doc2.get("embedding")
                    if not doc2_embedding:
                        continue

                    # Calculate cosine similarity (simple dot product for normalized vectors)
                    similarity = sum(
                        a * b for a, b in zip(doc1_embedding, doc2_embedding)
                    )

                    if similarity >= min_similarity:
                        similar_group.append(doc2)
                        seen_docs.add(doc2["id"])

                # Create suggestion if group size ≥ 2
                if len(similar_group) >= 2:
                    # Extract common themes from tags
                    all_tags = []
                    for doc in similar_group:
                        all_tags.extend(doc.get("tags", []))

                    tag_counts = defaultdict(int)
                    for tag in all_tags:
                        tag_counts[tag] += 1

                    common_themes = [
                        tag for tag, count in tag_counts.items() if count >= 2
                    ]

                    # Generate suggested title from common themes
                    if common_themes:
                        suggested_title = f"{common_themes[0].title()} Pattern"
                    else:
                        suggested_title = "Unnamed Pattern"

                    # Build rationale
                    doc_titles = [doc.get("title", "Untitled") for doc in similar_group]
                    rationale = (
                        f"Found {len(similar_group)} similar {similar_group[0]['type']}s "
                        f"that could be abstracted into a reusable pattern"
                    )

                    suggestion = PatternSuggestion(
                        suggested_title=suggested_title,
                        similarity_score=min_similarity,  # Use threshold as proxy
                        source_docs=[doc["id"] for doc in similar_group],
                        common_themes=common_themes,
                        rationale=rationale,
                    )
                    suggestions.append(suggestion)

                    seen_docs.add(doc1["id"])

                    if len(suggestions) >= max_suggestions:
                        break

            logger.info(f"Generated {len(suggestions)} pattern suggestions")
            return sorted(suggestions, key=lambda x: x.similarity_score, reverse=True)

        except Exception as e:
            logger.error(f"Pattern suggestion failed: {e}")
            raise GraphRAGError(f"Pattern suggestion failed: {e}") from e

    async def get_pattern_impact_summary(self) -> dict[str, Any]:
        """
        Get summary statistics about pattern usage in vault.

        Returns:
            Dict with:
                - total_patterns: Total pattern count
                - high_impact_patterns: Patterns with ≥5 references
                - avg_usage: Average usage count
                - max_usage: Highest usage count
                - unused_patterns: Patterns with 0 references
        """
        try:
            query = """
            SELECT
                count() AS total_patterns,
                count(<-used_in) AS total_used_in,
                count(<-informed_by) AS total_informed_by,
                math::max(count(<-used_in) + count(<-informed_by)) AS max_usage
            FROM vault_memory
            WHERE type = 'pattern'
            GROUP ALL;
            """

            results = await execute_surreal_async(
                query, self.surrealdb_url, self.namespace, self.database
            )

            if not results or not results[0].get("result"):
                return {
                    "total_patterns": 0,
                    "high_impact_patterns": 0,
                    "avg_usage": 0.0,
                    "max_usage": 0,
                    "unused_patterns": 0,
                }

            data = results[0]["result"][0] if results[0]["result"] else {}

            total_patterns = data.get("total_patterns", 0)
            total_used_in = data.get("total_used_in", 0)
            total_informed_by = data.get("total_informed_by", 0)
            max_usage = data.get("max_usage", 0)

            # Get high-impact count (≥5 references)
            high_impact_patterns = await self.detect_patterns(
                min_usage=5, max_results=100
            )

            # Get unused patterns
            unused_query = """
            SELECT count() AS unused
            FROM vault_memory
            WHERE type = 'pattern'
              AND count(<-used_in) = 0
              AND count(<-informed_by) = 0
              AND count(<-led_to) = 0;
            """

            unused_results = await execute_surreal_async(
                unused_query, self.surrealdb_url, self.namespace, self.database
            )
            unused_count = 0
            if unused_results and unused_results[0].get("result"):
                unused_count = unused_results[0]["result"][0].get("unused", 0)

            avg_usage = (
                (total_used_in + total_informed_by) / total_patterns
                if total_patterns > 0
                else 0.0
            )

            return {
                "total_patterns": total_patterns,
                "high_impact_patterns": len(high_impact_patterns),
                "avg_usage": round(avg_usage, 2),
                "max_usage": max_usage,
                "unused_patterns": unused_count,
            }

        except Exception as e:
            logger.error(f"Pattern impact summary failed: {e}")
            return {
                "total_patterns": 0,
                "high_impact_patterns": 0,
                "avg_usage": 0.0,
                "max_usage": 0,
                "unused_patterns": 0,
                "error": str(e),
            }
