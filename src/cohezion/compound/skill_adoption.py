"""Skill-adoption telemetry — a READ-ONLY report of undertriggering registry skills.

Item 32 (thread A), from claude.com "lessons from building Claude Code" #16 ("find skills
undertriggering compared to expectations"). `CharterAlignedSkillTracker.log_skill_usage` writes a
`skill_usage` stream, but never-fired registry skills are surfaced nowhere — the tracking→decision
gap. This instrument closes it: given the usage stream and the registered skills, it lists the
skills with ZERO usage events.

Mirrors item-25 `loop_telemetry`: read-only, derives its answer from the inputs on every call.
The function NEVER reads SurrealDB — the caller fetches the `skill_usage` events (from SurrealDB in
production, injected in tests), so "no real SurrealDB read under pytest" holds by construction.
``registry_skills`` defaults to the keys of ``skill_registry.json`` (a file read, not SurrealDB).
"""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path


_REPO = Path(__file__).resolve().parents[3]
_DEFAULT_REGISTRY = _REPO / "src" / "cohezion" / "registry" / "skill_registry.json"


def _registry_skill_names(registry_path: Path | None = None) -> list[str]:
    """Skill names = the top-level keys of ``skill_registry.json``. Fail-soft → [] on any error."""
    path = registry_path or _DEFAULT_REGISTRY
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError, ValueError):
        return []
    return list(data.keys()) if isinstance(data, dict) else []


def skill_adoption_report(
    usage_events: Iterable[dict],
    registry_skills: Iterable[str] | None = None,
    *,
    registry_path: Path | None = None,
) -> list[str]:
    """Registered skills with ZERO usage events (undertriggering). READ-ONLY, never writes.

    ``usage_events``: the `skill_usage` stream — each a dict carrying ``skill_name``. The caller
    fetches these (SurrealDB in production, injected in tests); this function does NOT read
    SurrealDB. ``registry_skills``: the registered skill names; when ``None`` they are loaded from
    ``skill_registry.json`` (a file read). Returns the SORTED registered names absent from the
    usage stream — the skills that have never fired.
    """
    used = {
        str(e.get("skill_name"))
        for e in usage_events
        if isinstance(e, dict) and e.get("skill_name")
    }
    if registry_skills is None:
        registry_skills = _registry_skill_names(registry_path)
    return sorted({str(s) for s in registry_skills} - used)
