"""Semantic search handler — FLUME VAE 256D embeddings via SemanticCache."""

from __future__ import annotations

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.cohezion_bridge import CohezionBridge

_bridge = CohezionBridge()


def handle_search(query: str, top_k: int = 3) -> dict:
    """Search Cohezion knowledge vault using FLUME VAE semantic embeddings.

    Args:
        query: Natural language search query.
        top_k: Maximum results to return.

    Returns:
        {
            "results": list of {"pattern": str, "similarity": float, "source": str},
            "formatted": str,  # formatted text for Slack
            "cache_used": bool,
            "query": str,
        }
    """
    results = _bridge.semantic_search(query, top_k=top_k)
    cache_used = _bridge.cohezion_available

    if results:
        lines = [f"*Cohezion Semantic Search* — `{query}`\n"]
        for i, r in enumerate(results, 1):
            sim_pct = int(r.get("similarity", 0) * 100)
            pattern = r.get("pattern", "")[:300]
            source = r.get("source", "vault")
            lines.append(f"*{i}.* [{sim_pct}% match] _{source}_\n```{pattern}```")
        formatted = "\n".join(lines)
    else:
        formatted = (
            f"*Cohezion Semantic Search* — `{query}`\n"
            "No similar patterns found in the knowledge vault.\n"
            "_Hint: The vault grows smarter with every code review run (SkillRefiner)._"
        )

    return {
        "results": results,
        "formatted": formatted,
        "cache_used": cache_used,
        "query": query,
    }
