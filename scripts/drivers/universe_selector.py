"""
Universe Selector: The Curator of the 12 Archetypes.
Watches the knowledge graph and maintains a 'Golden Set' of 12 transformative simulations.
"""

import asyncio
import json
import logging
from dataclasses import dataclass
from pathlib import Path


# Attempt to use local embedding for diversity, else fallback to coherence score
try:
    import numpy as np  # noqa: F401
    from sklearn.metrics.pairwise import cosine_similarity  # noqa: F401

    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False

logger = logging.getLogger("universe_selector")


@dataclass
class UniverseCandidate:
    id: str
    content: str
    coherence: float
    vector: str  # "chaos" or "order"
    timestamp: float


class UniverseSelector:
    def __init__(self):
        self.root_dir = Path("src/cohezion/knowledge_graph/universe_nodes")
        self.input_file = self.root_dir / "universes.jsonl"
        self.output_file = self.root_dir / "top_12_universes.md"
        self.candidates: list[UniverseCandidate] = []
        self.top_12: list[UniverseCandidate] = []

    async def run_forever(self):
        logger.info("Starting Universe Selector...")
        while True:
            await self._refresh_candidates()
            self._select_top_12()
            await self._publish_manifest()
            await asyncio.sleep(60)  # Run every minute

    async def _refresh_candidates(self):
        """Read latest data from graph ingestion."""
        if not self.input_file.exists():
            return

        new_candidates = []
        try:
            # Snail-read the file (it grows append-only)
            # For 24k lines, this is fine. For 1M, we'd need a cursor.
            with open(self.input_file) as f:
                for line in f:
                    try:
                        data = json.loads(line)
                        # Heuristic: Only care about "Survived" or high coherence
                        if data.get("status") == "survived" or data.get("coherence", 0) > 0.7:
                            new_candidates.append(
                                UniverseCandidate(
                                    id=data["id"],
                                    content=data["content"][:200],  # Preview
                                    coherence=data.get("coherence", 0.0),
                                    vector=data.get("vector", "unknown"),
                                    timestamp=data["timestamp"],
                                )
                            )
                    except json.JSONDecodeError:
                        continue
        except Exception as e:
            logger.error(f"Error reading DB: {e}")

        self.candidates = new_candidates

    def _select_top_12(self):
        """Logic to select the 12 most 'transformative'."""
        if not self.candidates:
            return

        # 1. Sort by Coherence initially
        sorted_by_score = sorted(self.candidates, key=lambda x: x.coherence, reverse=True)

        # 2. Diversity Filter (Primitive)
        # We want a mix of "Chaos" (Mutation) and "Order" (Physics)
        self.top_12 = []
        vectors_seen = {}

        for cand in sorted_by_score:
            if len(self.top_12) >= 12:
                break

            # Aim for balance: max 6 of any one vector type
            v = cand.vector
            if vectors_seen.get(v, 0) < 6:
                self.top_12.append(cand)
                vectors_seen[v] = vectors_seen.get(v, 0) + 1

        # Fill rest if needed
        if len(self.top_12) < 12 and len(sorted_by_score) > len(self.top_12):
            remaining = [c for c in sorted_by_score if c not in self.top_12]
            self.top_12.extend(remaining[: 12 - len(self.top_12)])

    async def _publish_manifest(self):
        """Write the Top 12 to a readable Markdown file."""
        if not self.top_12:
            return

        content = "# The 12 Universal Archetypes\n"
        content += f"**Updated:** {logging.Formatter().formatTime(logging.LogRecord('', 0, '', 0, '', '', 0))}\n\n"

        for i, u in enumerate(self.top_12, 1):
            content += f"## {i}. Universe {u.id}\n"
            content += f"- **Vector:** {u.vector.upper()}\n"
            content += f"- **Coherence:** {u.coherence:.4f}\n"
            content += f"- **Snippet:** {u.content}...\n"
            content += f"- **Artifact:** `universes.jsonl` (Timestamp: {u.timestamp})\n\n"

        with open(self.output_file, "w") as f:
            f.write(content)

        logger.info(f"Updated Top 12 Manifest with {len(self.top_12)} universes.")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    selector = UniverseSelector()
    asyncio.run(selector.run_forever())
