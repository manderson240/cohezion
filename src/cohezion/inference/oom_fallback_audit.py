"""Registry OOM-fallback coverage audit (backlog item 146, 2026-06-08).

Generalizes item 144: a Task whose preferred iGPU model is LARGE should not silently fall to
CPU/cloud under memory pressure when a SMALLER iGPU model could serve it. ``oom_fallback_gaps``
walks ``registry.for_task(task)`` (priority-sorted) for every Task and flags the ones where the
preferred local candidate is a large iGPU model with no smaller iGPU fallback — so the only
option below the big model is the slow CPU lane or paid cloud.

Structural-before-behavioral (L366): a $0, deterministic, report-only audit over the live
registry. A candidate with unknown ``size_gb`` is never treated as large (non-fabricated). It
does NOT mutate the registry — closing a flagged gap (registering a mid-size iGPU model, as
item 144 did) is a separate gated action.
"""

from __future__ import annotations

from typing import Any

from cohezion.inference.registry import Lane, Task


_IGPU_LANES = frozenset({Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED})
_CLOUD_LANES = frozenset({Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE, Lane.CLOUD_GEMINI})


def oom_fallback_gaps(registry: Any, *, large_threshold_gb: float = 10.0) -> list[Task]:
    """Tasks whose preferred LARGE iGPU model has no smaller iGPU fallback (item 146).

    For each :class:`Task`, walk ``registry.for_task(task)`` (priority-sorted, preferred first).
    If the preferred LOCAL (non-cloud) candidate is an iGPU model larger than ``large_threshold_gb``
    AND no OTHER iGPU candidate for that Task is smaller than it, the only fallback below the big
    model is CPU/cloud → flag an OOM-fallback gap. A candidate with unknown ``size_gb`` is never
    treated as large (no fabrication). Report-only. Returns the flagged Tasks sorted by name.
    """
    gaps: list[Task] = []
    for task in Task:
        candidates = list(registry.for_task(task))
        local = [c for c in candidates if c.lane not in _CLOUD_LANES]
        if not local:
            continue
        preferred = local[0]
        if preferred.lane not in _IGPU_LANES:
            continue
        size = preferred.size_gb
        if size is None or size <= large_threshold_gb:
            continue  # not large (or unknown size → don't fabricate)
        has_smaller_igpu = any(
            c is not preferred
            and c.lane in _IGPU_LANES
            and c.size_gb is not None
            and c.size_gb < size
            for c in candidates
        )
        if not has_smaller_igpu:
            gaps.append(task)
    return sorted(gaps, key=lambda t: t.name)
