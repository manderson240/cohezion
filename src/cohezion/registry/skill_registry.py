import difflib
import json
import os
from typing import Any

# Path to the JSON registry file located alongside this module
_REGISTRY_FILE = os.path.join(os.path.dirname(__file__), "skill_registry.json")


def _ensure_registry_file() -> None:
    """
    Ensure that the registry JSON file exists.
    If it does not, create an empty registry.
    """
    if not os.path.exists(_REGISTRY_FILE):
        with open(_REGISTRY_FILE, "w", encoding="utf-8") as f:
            json.dump({}, f, indent=2)


def load_registry() -> dict[str, Any]:
    """
    Load the entire skill registry from disk.

    Returns
    -------
    dict
        Mapping of skill names to their metadata dictionaries.
    """
    _ensure_registry_file()
    with open(_REGISTRY_FILE, encoding="utf-8") as f:
        try:
            data = json.load(f)
            if not isinstance(data, dict):
                # Corrupted file – reset to empty dict
                data = {}
        except json.JSONDecodeError:
            data = {}
    return data


def _save_registry(data: dict[str, Any]) -> None:
    """
    Persist the given registry data to disk.

    Parameters
    ----------
    data: dict
        The full registry mapping to write.
    """
    with open(_REGISTRY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def register_skill(
    name: str,
    description: str,
    keywords: list[str],
    path: str,
    version: str = "0.1.0",
    template_version: str = "v0.1",
    generated_from: str = "skill.md",
) -> None:
    """
    Register (or update) a skill in the registry.

    Parameters
    ----------
    name: str
        Unique identifier for the skill (e.g., "METAPHYSICS_PRIME").
    description: str
        Human‑readable description of what the skill does.
    keywords: list[str]
        A list of search‑friendly tokens that capture the core concepts.
    path: str
        Relative path to the markdown file that implements the skill.
    version: str, optional
        SemVer version of the skill implementation.
    template_version: str, optional
        Version of the template used to generate this skill.
    generated_from: str, optional
        Name of the template file used.
    """
    registry = load_registry()
    registry[name] = {
        "description": description,
        "keywords": [kw.lower() for kw in keywords],
        "path": path,
        "version": version,
        "template_version": template_version,
        "generated_from": generated_from,
        "last_updated": os.environ.get("COHEZION_TIMESTAMP", "") or "",
    }
    _save_registry(registry)


def _match_score(query: str, text: str) -> float:
    """
    Compute a simple similarity score between a query and a piece of text.
    Uses difflib's SequenceMatcher ratio after lower‑casing both strings.
    """
    return difflib.SequenceMatcher(None, query.lower(), text.lower()).ratio()


def search_skills(query: str, limit: int = 10) -> list[dict[str, Any]]:
    """
    Perform a fuzzy search over the skill registry using natural‑language
    queries. Returns the best matching skill entries.

    Parameters
    ----------
    query: str
        The user's search phrase.
    limit: int, optional
        Maximum number of results to return (default 10).

    Returns
    -------
    list[dict]
        Each dict contains the keys ``name``, ``description``, ``keywords``,
        and ``path`` for a matching skill.
    """
    registry = load_registry()
    results: list[dict[str, Any]] = []

    for name, meta in registry.items():
        # Compute a combined score from name, description, and keywords
        name_score = _match_score(query, name)
        desc_score = _match_score(query, meta.get("description", ""))
        keywords = " ".join(meta.get("keywords", []))
        kw_score = _match_score(query, keywords)

        # Weighted sum – name is most important
        total_score = 0.6 * name_score + 0.3 * desc_score + 0.1 * kw_score

        if total_score > 0.0:
            entry = {
                "name": name,
                "description": meta.get("description", ""),
                "keywords": meta.get("keywords", []),
                "path": meta.get("path", ""),
                "score": total_score,
            }
            results.append(entry)

    # Sort descending by score and trim to limit
    results.sort(key=lambda x: x["score"], reverse=True)
    return results[:limit]
