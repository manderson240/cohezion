"""Item 146: oom_fallback_gaps — TDD red→green (2026-06-08).

``oom_fallback_gaps(registry, *, threshold_gb)`` scans each Task and flags those
whose preferred local candidate is large (size_gb > threshold) but has NO smaller
iGPU fallback — meaning the only escape from an OOM is the slow CPU lane or cloud.

Discriminating tests — each kills a plausible wrong implementation:

  1. CODE_GEN is NOT flagged post-item-144 (26B→12B iGPU fallback EXISTS)
     PRIMARY DISC.: kills "flag all tasks with a large preferred model"
  2. A large-preferred task with ONLY CPU fallback IS flagged
     Kills "never flag anything" / "always return []"
  3. A task with preferred size_gb=None → NOT flagged (non-fabricated — no size = skip)
     Kills an impl that flags None as > threshold
  4. A task with a preferred model UNDER threshold → NOT flagged
     Kills an impl that flags all tasks with multiple candidates
  5. Empty registry → []
     Kills an impl that crashes on empty input
"""

from __future__ import annotations

from cohezion.inference.oom_fallback_audit import oom_fallback_gaps
from cohezion.inference.registry import FleetRegistry, Lane, ModelEntry, Task, WeightQuant


# ---------------------------------------------------------------------------
# Registry fixture helpers
# ---------------------------------------------------------------------------

_BASE_TASK = Task.CODE_GEN


def _entry(
    model_id: str,
    lane: Lane,
    size_gb: float | None,
    priority: int,
    task: Task = _BASE_TASK,
) -> ModelEntry:
    return ModelEntry(
        model_id=model_id,
        lane=lane,
        endpoint="local://test",
        runtime_backend="test",
        weight_quant=WeightQuant.INT4,
        context_window=4096,
        task_affinity=frozenset({task}),
        priority=priority,
        size_gb=size_gb,
    )


def _registry(*entries: ModelEntry) -> FleetRegistry:
    return FleetRegistry(models={e.model_id: e for e in entries})


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


def test_code_gen_not_flagged_with_smaller_igpu_fallback() -> None:
    """CODE_GEN with 26B preferred + 12B iGPU fallback → NOT flagged.

    PRIMARY DISCRIMINATOR: kills an impl that flags any task with a large
    preferred model, ignoring whether a smaller iGPU safety net exists.

    Mirrors the post-item-144 state: 26B (15.7GB) + 12B (6.5GB) iGPU → COVERED.
    """
    reg = _registry(
        _entry("large-26b", Lane.IGPU_UNIFIED, size_gb=15.7, priority=15),
        _entry("small-12b", Lane.IGPU_ROCWMMA, size_gb=6.5, priority=18),
        _entry("cpu-model", Lane.CPU, size_gb=None, priority=30),
    )
    gaps = oom_fallback_gaps(reg, threshold_gb=10.0)
    assert _BASE_TASK.value not in gaps, (
        f"{_BASE_TASK.value} must NOT be flagged when a smaller iGPU fallback exists; got {gaps}"
    )


def test_large_preferred_with_only_cpu_fallback_flagged() -> None:
    """A task with large preferred + CPU-only fallback (no smaller iGPU) IS flagged.

    Kills an impl that always returns [] (never detects a gap).
    Mirrors pre-item-144 CODE_GEN: 26B iGPU → cpu only (no 12B).
    """
    reg = _registry(
        _entry("large-26b", Lane.IGPU_UNIFIED, size_gb=15.7, priority=15),
        _entry("cpu-model", Lane.CPU, size_gb=None, priority=30),
    )
    gaps = oom_fallback_gaps(reg, threshold_gb=10.0)
    assert _BASE_TASK.value in gaps, (
        f"{_BASE_TASK.value} must be flagged when only CPU fallback exists; got {gaps}"
    )


def test_unknown_size_preferred_not_flagged() -> None:
    """Preferred model with size_gb=None → NOT flagged (non-fabricated: skip unknowns).

    Kills an impl that treats None as > threshold (fabricates a size).
    """
    reg = _registry(
        _entry("unknown-size", Lane.IGPU_UNIFIED, size_gb=None, priority=15),
        _entry("cpu-model", Lane.CPU, size_gb=None, priority=30),
    )
    gaps = oom_fallback_gaps(reg, threshold_gb=10.0)
    assert _BASE_TASK.value not in gaps, (
        f"unknown-size model must NOT be flagged (no fabricated size); got {gaps}"
    )


def test_small_preferred_not_flagged() -> None:
    """Preferred model with size_gb <= threshold → NOT flagged (no OOM risk).

    Kills an impl that flags tasks with multiple local candidates regardless
    of whether the preferred is actually large.
    """
    reg = _registry(
        _entry("small-4b", Lane.IGPU_ROCWMMA, size_gb=4.6, priority=15),
        _entry("cpu-model", Lane.CPU, size_gb=None, priority=30),
    )
    gaps = oom_fallback_gaps(reg, threshold_gb=10.0)
    assert _BASE_TASK.value not in gaps, (
        f"small preferred (4.6GB < 10.0 threshold) must NOT be flagged; got {gaps}"
    )


def test_empty_registry_returns_empty() -> None:
    """Empty registry → [] (no crash)."""
    reg = _registry()
    assert oom_fallback_gaps(reg) == []
