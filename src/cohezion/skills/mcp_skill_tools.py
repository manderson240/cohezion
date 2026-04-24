"""Skill execution and long-term memory tools for the MCP server.

Includes:
* :func:`execute_skill` — read a registered skill file by ID
* :func:`get_truth_anchors` — verified hardware/system facts
* :func:`remember_fact` / :func:`recall_context` — semantic memory wrappers
* :func:`daily_scout_research` — trigger the SOTA-SLM scout agent
"""

from __future__ import annotations

import json
import os
from typing import Any

from .mcp_paths import cohezion_root


def execute_skill(
    skill_name: str, inputs: dict[str, Any], skills: dict[str, Any]
) -> dict[str, Any]:
    """Resolve a skill by name in the registry and return its source contents.

    ``inputs`` is currently unused — the skill source is returned verbatim so
    the caller (an agent) can interpret the directives.
    """
    if skill_name not in skills:
        return {"content": [{"type": "text", "text": f"Error: Skill '{skill_name}' not found"}]}
    skill = skills[skill_name]
    skill_path_rel = skill.get("path")
    if not skill_path_rel:
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: Skill path missing for '{skill_name}'",
                }
            ]
        }

    skill_path = os.path.join(cohezion_root(), skill_path_rel)
    if not os.path.exists(skill_path):
        return {
            "content": [
                {
                    "type": "text",
                    "text": f"Error: Skill file not found: {skill_path}",
                }
            ]
        }
    try:
        with open(skill_path) as f:
            return {"content": [{"type": "text", "text": f.read()}]}
    except (OSError, UnicodeDecodeError) as e:
        return {"content": [{"type": "text", "text": f"Error executing skill: {e}"}]}


def get_truth_anchors(arguments: dict[str, Any]) -> dict[str, Any]:
    """Return the verified hardware/system context block for grounding."""
    from cohezion.reliability.residency_awareness import ResidencyAnchorBase

    return {
        "content": [
            {
                "type": "text",
                "text": ResidencyAnchorBase.get_context_block(),
            }
        ]
    }


def remember_fact(arguments: dict[str, Any]) -> dict[str, Any]:
    """Persist ``arguments['fact']`` into semantic memory under ``category``."""
    from cohezion.reliability.memory_manager import MemoryManager

    fact = arguments.get("fact")
    category = arguments.get("category", "general")
    mgr = MemoryManager()
    res = mgr.add(fact, metadata={"category": category})
    return {
        "content": [
            {
                "type": "text",
                "text": f"Fact remembered successfully. Result: {res}",
            }
        ]
    }


def recall_context(arguments: dict[str, Any]) -> dict[str, Any]:
    """Search semantic memory for ``arguments['query']`` (default ``limit=5``)."""
    from cohezion.reliability.memory_manager import MemoryManager

    query = arguments.get("query")
    limit = arguments.get("limit", 5)
    mgr = MemoryManager()
    results = mgr.search(query, limit=limit)
    return {
        "content": [
            {
                "type": "text",
                "text": json.dumps(results, indent=2),
            }
        ]
    }


def daily_scout_research(arguments: dict[str, Any]) -> dict[str, Any]:
    """Run the Daily Scout agent and return its filtered SLM proposals."""
    from cohezion.agents.daily_scout import DailyScoutAgent

    scout = DailyScoutAgent()
    # In a real async environment, this would await research.
    # For now, we simulate the proposal generation.
    proposals = scout.perform_research()
    filtered = scout.filter_proposals(proposals)
    return {
        "content": [
            {
                "type": "text",
                "text": f"Scout Research Complete:\n{json.dumps(filtered, indent=2)}",
            }
        ]
    }
