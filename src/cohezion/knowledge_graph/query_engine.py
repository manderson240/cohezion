# ruff: noqa: S112  # best-effort skip in cleanup paths
"""Knowledge graph query engine for execution history and pattern analysis.

Provides search over agent execution records and knowledge graph entries,
backed by SurrealDB with InMemoryStore fallback.
"""

from __future__ import annotations

import json
import logging
import math
import re
from collections import Counter
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)


class KnowledgeGraphQueryEngine:
    """Query engine for the Cohezion knowledge graph.

    Parameters
    ----------
    db_client : Any | None
        SurrealClient instance. If ``None``, uses local file fallback.
    knowledge_dir : str | Path
        Directory containing knowledge graph markdown files.
    """

    def __init__(
        self,
        db_client: Any | None = None,
        knowledge_dir: str | Path = "src/cohezion/knowledge_graph",
    ) -> None:
        self._db = db_client
        self._knowledge_dir = Path(knowledge_dir)

    async def query_execution_history(self, limit: int = 50) -> list[dict[str, Any]]:
        """Return recent agent execution records.

        Tries SurrealDB first, falls back to scanning local journey files.
        """
        # Try DB first
        if self._db is not None:
            try:
                safe_limit = min(int(limit), 10000)
                rows = await self._db.query(
                    "SELECT * FROM agent_journey ORDER BY created_at DESC LIMIT $limit",
                    {"limit": safe_limit},
                )
                if rows and isinstance(rows, list):
                    # Handle flat list or wrapped formats
                    if rows and isinstance(rows[0], dict) and "result" in rows[0]:
                        return list(rows[0]["result"][:limit])
                    return list(rows[:limit])
            except Exception as e:
                logger.debug("DB query failed, using file fallback: %s", e)

        # Fallback: scan local journey files
        journey_dir = Path("data/universe")
        if not journey_dir.exists():
            return []

        records: list[dict[str, Any]] = []
        for path in sorted(journey_dir.glob("journey_*.json"), reverse=True):
            if len(records) >= limit:
                break
            try:
                data = json.loads(path.read_text())
                records.append(data)
            except Exception as _e:
                logger.debug("Skipping: %s", _e)
                continue
        return records

    async def get_pattern_summary(self) -> dict[str, Any]:
        """Analyze execution history for patterns.

        Returns
        -------
        dict
            Keys: total_executions, agent_counts, status_counts, avg_coherence.
        """
        history = await self.query_execution_history(limit=200)

        agent_counts: Counter[str] = Counter()
        status_counts: Counter[str] = Counter()
        coherences: list[float] = []

        for record in history:
            agent_counts[record.get("agent_name", "unknown")] += 1
            status_counts[record.get("status", "unknown")] += 1
            coh = record.get("final_coherence")
            if coh is not None:
                coherences.append(float(coh))

        return {
            "total_executions": len(history),
            "agent_counts": dict(agent_counts.most_common(20)),
            "status_counts": dict(status_counts),
            "avg_coherence": sum(coherences) / len(coherences) if coherences else 0.0,
        }

    def search_knowledge(self, query: str, top_k: int = 5) -> list[dict[str, Any]]:
        """Keyword search across knowledge graph markdown files.

        Uses simple TF-IDF style scoring on document sections.

        Parameters
        ----------
        query : str
            Search query (whitespace-separated terms).
        top_k : int
            Number of results to return.

        Returns
        -------
        list[dict]
            Ranked results with path, title, snippet, and score.
        """
        terms = [t.lower() for t in query.split() if len(t) > 2]
        if not terms:
            return []

        results: list[dict[str, Any]] = []

        # Search markdown files in knowledge_graph dir
        for md_path in self._knowledge_dir.glob("*.md"):
            try:
                text = md_path.read_text(encoding="utf-8")
            except Exception as _e:
                logger.debug("Skipping: %s", _e)
                continue

            text_lower = text.lower()
            # Score = sum of term frequencies weighted by inverse document length
            score = 0.0
            for term in terms:
                count = text_lower.count(term)
                if count > 0:
                    # TF-IDF-like: term freq / log(doc length)
                    doc_len = max(len(text_lower.split()), 1)
                    score += count / math.log2(doc_len + 1)

            if score > 0:
                # Extract first matching line as snippet
                snippet = ""
                for line in text.splitlines():
                    if any(t in line.lower() for t in terms):
                        snippet = line.strip()[:200]
                        break

                # Extract title from first heading
                title_match = re.search(r"^#\s+(.+)", text, re.MULTILINE)
                title = title_match.group(1).strip() if title_match else md_path.stem

                results.append(
                    {
                        "path": str(md_path),
                        "title": title,
                        "snippet": snippet,
                        "score": round(score, 4),
                    }
                )

        results.sort(key=lambda r: r["score"], reverse=True)
        return results[:top_k]
