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
from dataclasses import dataclass
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


def _counts_per_registered_skill(
    usage_events: Iterable[dict],
    registry_skills: Iterable[str] | None,
    registry_path: Path | None,
) -> dict[str, int]:
    """``{registered_skill: firing_count}`` for EVERY registered skill (never-fired → 0). READ-ONLY.

    The shared counting core of ``low_adoption_report`` (item 41) and ``least_adopted`` (item 60):
    iterates the REGISTRY (not the event stream), so a never-fired registered skill is included with
    count 0 and an unregistered firing is ignored. Never reads SurrealDB (caller injects events).
    """
    counts: dict[str, int] = {}
    for e in usage_events:
        if isinstance(e, dict) and e.get("skill_name"):
            name = str(e["skill_name"])
            counts[name] = counts.get(name, 0) + 1
    if registry_skills is None:
        registry_skills = _registry_skill_names(registry_path)
    return {str(s): counts.get(str(s), 0) for s in registry_skills}


def low_adoption_report(
    usage_events: Iterable[dict],
    registry_skills: Iterable[str] | None = None,
    *,
    min_uses: int,
    registry_path: Path | None = None,
) -> dict[str, int]:
    """Registered skills fired FEWER than ``min_uses`` times → ``{skill: exact_count}``. READ-ONLY.

    Generalizes item-32 from binary (zero events) to a threshold — the "vs expectations" nuance
    from claude.com #16, where ``min_uses`` is the expected firing count. Iterates the REGISTRY
    (not the event stream), so a never-fired registered skill is reported with count 0, and an
    unregistered skill that fires is ignored. ``min_uses=1`` reproduces item-32's zero-only set
    (a count of 1 is not ``< 1``). The threshold is strict: a skill used exactly ``min_uses`` times
    is NOT reported. Never reads SurrealDB (the caller injects ``usage_events``).
    """
    counts = _counts_per_registered_skill(usage_events, registry_skills, registry_path)
    return {name: count for name, count in counts.items() if count < min_uses}


def least_adopted(
    usage_events: Iterable[dict],
    registry_skills: Iterable[str] | None = None,
    *,
    n: int,
    registry_path: Path | None = None,
) -> list[tuple[str, int]]:
    """The ``n`` LOWEST-firing registered skills as ``[(skill, count)]`` ascending (item 60). READ-ONLY.

    The prioritized "investigate these under-triggers first" queue claude.com #16 wants — distinct
    from item-41 ``low_adoption_report`` (threshold-gated, unordered map): no threshold, RANKED. All
    registered skills are counted (never-fired → count 0, sorts first); ordered by ``(count, name)``
    ascending so ties break deterministically by name; the first ``n`` are returned. ``n <= 0`` → []
    (clamped); ``n >= len(registry)`` → every skill ranked. Unregistered firings are ignored. Never
    reads SurrealDB (caller injects ``usage_events``).
    """
    counts = _counts_per_registered_skill(usage_events, registry_skills, registry_path)
    ranked = sorted(counts.items(), key=lambda kv: (kv[1], kv[0]))
    return ranked[: max(0, n)]


# ---------------------------------------------------------------------------
# Item 82 — Skill-firing concentration (Thread A)
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class FiringConcentration:
    """The top-heaviness scalar of registered-skill usage (item 82). Report-only.

    Attributes:
        top_skill_share: Fraction of ALL registered firings captured by the single
            most-fired skill.  0.0 when there are no firings.
        unused_share: Fraction of ALL REGISTERED skills with zero firings.
            1.0 when the entire registry is idle.
        total_firings: Total firing count over registered skills (unregistered
            firings are excluded from all three figures).
    """

    top_skill_share: float
    unused_share: float
    total_firings: int


def firing_concentration(
    usage_events: Iterable[dict],
    registry_skills: Iterable[str] | None = None,
    *,
    registry_path: Path | None = None,
) -> FiringConcentration:
    """The top-heaviness scalar that EXPLAINS item-60's long tail (item 82). READ-ONLY.

    A single number answers "how skewed is the firing distribution?" — a few skills hogging
    firings while many sit unused.  Shares ``_counts_per_registered_skill`` with item-60.

    All three figures operate over REGISTERED skills only; unregistered firings are excluded:
    - ``top_skill_share`` = firings_of_most_fired_skill / total_registered_firings (0.0 if none).
    - ``unused_share``    = never_fired_skills / total_registered_skills (1.0 if none fired).
    - ``total_firings``   = sum of registered-skill firing counts (not the raw event count).

    No ZeroDivision: when total_firings == 0, top_skill_share = 0.0; when registry is empty,
    unused_share = 0.0.  Never reads SurrealDB (caller injects events).
    """
    counts = _counts_per_registered_skill(usage_events, registry_skills, registry_path)

    total_registered = len(counts)
    total_firings = sum(counts.values())
    never_fired = sum(1 for c in counts.values() if c == 0)

    top_skill_share = max(counts.values()) / total_firings if total_firings > 0 else 0.0
    unused_share = never_fired / total_registered if total_registered > 0 else 0.0

    return FiringConcentration(
        top_skill_share=top_skill_share,
        unused_share=unused_share,
        total_firings=total_firings,
    )


# ---------------------------------------------------------------------------
# ## FUTURE HOOKS
# ---------------------------------------------------------------------------
# 82b: Expose firing_concentration via the compound health dashboard
#      (CompoundHealthResponse) so operators can see distribution skew at a glance.
# 82c: Feed into SkillRefiner: when top_skill_share > 0.7, the over-fired skill
#      is a candidate for decomposition (too broad → too general).
# 82d: Track concentration trend over ticks — convergence toward 1.0 means the
#      loop is increasingly relying on a single skill (brittleness signal).
