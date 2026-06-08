"""Item 146: OOM-fallback coverage audit — report-only (2026-06-08).

``oom_fallback_gaps(registry)`` generalises item 131 (fleet OOM gate) and item 144
(the 12B iGPU mid-tier that filled the 26B→qwen3-coder gap) into a structural audit:

For each Task, check whether a Task whose preferred local model is large
(size_gb > threshold) has a SMALLER iGPU-lane fallback.  If not, and the
next escape is CPU or cloud, it is an "OOM-fallback gap": under memory pressure
the fleet silently drops from fast iGPU to slow CPU/cloud with no intermediate.

The audit would have FLAGGED CODE_GEN pre-item-144 (26B iGPU → qwen3-coder CPU)
and returns it as COVERED post-144 (26B iGPU → 12B iGPU).

NON-FABRICATED: reads the live registry; only flags tasks with a DOCUMENTED
(non-None) size_gb for the preferred local model.  Report-only — no writes.
"""

from __future__ import annotations

from cohezion.inference.registry import FleetRegistry, Lane, Task


# Lane sets for classification.
_CLOUD_LANES = frozenset({Lane.CLOUD_OLLAMA, Lane.CLOUD_CLAUDE, Lane.CLOUD_GEMINI})
_IGPU_LANES = frozenset({Lane.IGPU_ROCWMMA, Lane.IGPU_UNIFIED})

# Default threshold: models above 10 GB on the iGPU tier may OOM under pressure.
_DEFAULT_THRESHOLD_GB = 10.0


def oom_fallback_gaps(
    registry: FleetRegistry,
    *,
    threshold_gb: float = _DEFAULT_THRESHOLD_GB,
) -> list[str]:
    """Flag Tasks with a large preferred local model and no smaller iGPU fallback.

    For each Task:
    1. Collect all local (non-cloud) candidates sorted by priority (preferred first).
    2. If the preferred local model has a DOCUMENTED size_gb > threshold, check
       whether any OTHER local iGPU-lane model has size_gb < preferred.size_gb.
    3. If NO such smaller-iGPU fallback exists → flag as an OOM-fallback gap.

    The preferred model with size_gb=None is skipped (non-fabricated — we never
    invent a size).  Tasks with no local candidates are also skipped.

    Args:
        registry:
            The live (or injected) :class:`FleetRegistry` to audit.
        threshold_gb:
            Models with size_gb above this value are considered "large".
            Defaults to 10.0 GB (appropriate for the strix-halo fleet).

    Returns:
        Sorted list of :attr:`Task.value` strings for flagged tasks.
        Empty when every large-preferred task has a smaller iGPU safety net.

    Report-only — no registry writes.
    """
    gaps: list[str] = []

    for task in Task:
        entries = registry.for_task(task)  # sorted by priority ascending
        local = [e for e in entries if e.lane not in _CLOUD_LANES]

        if not local:
            continue  # no local candidates at all — not an OOM-fallback gap

        preferred = local[0]  # lowest priority = most preferred

        # Only flag when the preferred size is documented AND large.
        if preferred.size_gb is None or preferred.size_gb <= threshold_gb:
            continue

        # Is there a smaller iGPU candidate that could serve as a mid-tier?
        has_smaller_igpu = any(
            e.lane in _IGPU_LANES and e.size_gb is not None and e.size_gb < preferred.size_gb
            for e in local
            if e is not preferred
        )

        if not has_smaller_igpu:
            gaps.append(task.value)

    return sorted(gaps)
