"""PRIME skill loader for compound engineering.

Provides dynamic skill discovery and loading for agentic workflows.
Enables agents to automatically find and inject relevant PRIME skills
based on task context.
"""

import difflib
import logging
from pathlib import Path
from typing import Any


logger = logging.getLogger(__name__)

SKILLS_DIR = Path(__file__).parent
CACHE: dict[str, dict[str, Any]] | None = None


def _load_skill_index() -> dict[str, dict[str, Any]]:
    """Load or build skill index from PRIME skill files."""
    global CACHE
    if CACHE is not None:
        return CACHE

    index: dict[str, dict[str, Any]] = {}

    for skill_file in SKILLS_DIR.glob("*_PRIME.md"):
        content = skill_file.read_text()
        name = skill_file.stem.replace("_PRIME", "")

        domain = ""
        keywords = []
        lines = content.split("\n")

        in_domain = False
        in_keywords = False

        for line in lines:
            if "## DOMAIN EXPERTISE" in line:
                in_domain = True
                continue
            if "## KEY TEXTS & CONCEPTS" in line:
                in_domain = False
                in_keywords = True
                continue
            if line.startswith("## "):
                in_keywords = False

            if in_domain and line.strip():
                domain = line.strip()
                in_domain = False

            if in_keywords and "**" in line:
                import re

                terms = re.findall(r"\*\*([^*]+)\*\*", line)
                keywords.extend([t.lower() for t in terms])

        index[name.upper()] = {
            "name": name,
            "title": name.replace("_", " "),
            "domain": domain,
            "keywords": keywords,
            "path": str(skill_file),
            "content": content[:500],
        }

    CACHE = index
    return index


def search_skills(query: str, limit: int = 5) -> list[dict[str, Any]]:
    """Search skills using fuzzy matching.

    Args:
        query: Natural language query or skill name
        limit: Maximum number of results

    Returns:
        List of matching skills with relevance scores
    """
    index = _load_skill_index()
    query_lower = query.lower()

    results: list[tuple[str, float]] = []

    for skill_name, skill_data in index.items():
        score = 0.0

        if query_lower in skill_name.lower():
            score += 0.6

        if query_lower in skill_data["title"].lower():
            score += 0.5

        if query_lower in skill_data["domain"].lower():
            score += 0.3

        for kw in skill_data["keywords"]:
            if query_lower in kw.lower():
                score += 0.1

        if score > 0:
            results.append((skill_name, score))

    results.sort(key=lambda x: x[1], reverse=True)
    return [index[name] for name, _ in results[:limit]]


def load_skill(skill_name: str) -> str | None:
    """Load full skill content by name.

    Args:
        skill_name: Name of the skill (case-insensitive)

    Returns:
        Full skill content or None if not found
    """
    index = _load_skill_index()
    skill_name_upper = skill_name.upper()

    if skill_name_upper in index:
        return index[skill_name_upper]["path"]

    matches = difflib.get_close_matches(
        skill_name_upper, list(index.keys()), n=1, cutoff=0.6
    )
    if matches:
        return index[matches[0]]["path"]

    return None


def get_relevant_skills_for_task(task_description: str) -> list[dict[str, Any]]:
    """Find skills relevant to a task description.

    This provides semantic-like discovery without embeddings.

    Args:
        task_description: Natural language description of the task

    Returns:
        List of relevant skills sorted by relevance
    """
    task_lower = task_description.lower()

    skill_queries = {
        "token": ["TOKEN_EFFICIENCY", "COST", "OPTIMIZATION"],
        "journey": ["JOURNEY_TRACKING", "TRAJECTORY", "MONITORING"],
        "tracking": ["JOURNEY_TRACKING", "MONITORING"],
        "physics": ["FLUME", "UNIVERSE", "LATENT"],
        "cache": ["CACHING", "SEMANTIC_CACHE", "VECTOR_STORE"],
        "memory": ["MEMORY", "VECTOR_STORE", "PERSISTENCE"],
        "security": ["SECURITY", "GUARDRAIL", "AUTH"],
        "testing": ["TESTING", "ADVERSARIAL"],
        "swarm": ["SWARM", "ORCHESTRATION", "TEAM"],
        "agent": ["AGENTIC", "AGENT"],
        "compound": ["COMPOUND", "ENGINEERING"],
        "vault": ["VAULT", "INTEGRATION"],
        "recovery": ["RECOVERY", "RESILIENCE", "HEALING"],
        "model": ["MODEL", "POOL", "ROUTING"],
        "routing": ["ROUTING", "MODEL_ROUTING"],
    }

    matched_skills: set[str] = set()

    for keyword, skill_names in skill_queries.items():
        if keyword in task_lower:
            matched_skills.update(skill_names)

    index = _load_skill_index()
    results = []

    for skill_name in matched_skills:
        if skill_name in index:
            results.append(index[skill_name])

    return results


def list_all_skills() -> list[dict[str, Any]]:
    """List all available PRIME skills."""
    index = _load_skill_index()
    return list(index.values())


def get_skill_by_keyword(keyword: str) -> list[dict[str, Any]]:
    """Find skills matching a keyword.

    Args:
        keyword: Keyword to search for

    Returns:
        List of matching skills
    """
    index = _load_skill_index()
    keyword_lower = keyword.lower()

    results = []
    for skill_data in index.values():
        title_or_keywords = (
            keyword_lower in skill_data["title"].lower()
            or keyword_lower in " ".join(skill_data["keywords"]).lower()
        )
        if title_or_keywords:
            results.append(skill_data)

    return results
