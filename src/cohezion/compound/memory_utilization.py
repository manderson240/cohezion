"""Item 106: Memory-utilization report — distillation bottleneck diagnostic.

Classifies SurrealDB memory-layer record counts into ``dormant``/``sparse``/``healthy``
and computes a **distillation ratio** (raw journey_points vs distilled summaries).

Live finding 2026-06-06: ``journey_point=278741`` vs ``neuron=18/learnings=10``
gives ~9955:1 raw:distilled — flagged as ``under_distilled``.  This report is the
"measure BEFORE bridging" gate for compound memory diagnostics (item 106).

Pure (injected counts; no live SurrealDB read).  Report-only.
"""

from __future__ import annotations

from dataclasses import dataclass

# The raw layer: the append-only journey record stream.
_RAW_LAYER: str = "journey_point"

# The distilled layers: neurons, learnings, compound summaries, mem0 snapshots.
# vault_notes is NOT a distilled layer — it is a separate knowledge store, not a
# compression of journey_points.
_DISTILLED_LAYERS: frozenset[str] = frozenset({"neuron", "learnings", "compound_learnings", "mem0"})


@dataclass(frozen=True)
class MemoryUtilizationReport:
    """Classification of SurrealDB memory-layer health (item 106). Report-only.

    Attributes
    ----------
    dormant:
        Layer names with ``count == 0`` — completely inactive, no records.
    sparse:
        Layer names with ``0 < count < floor`` — alive but under-populated.
    healthy:
        Layer names with ``count >= floor`` — adequately populated.
    distillation_ratio:
        ``journey_point_count / sum(distilled_layer_counts)`` — the raw:distilled
        compression ratio.  ``None`` when all distilled layers are absent or zero
        (avoids ZeroDivisionError).
    under_distilled:
        ``True`` when ``distillation_ratio >= under_distilled_threshold`` — the
        bottleneck signal that the distillation pipeline is not keeping pace with
        the raw event stream.  ``False`` when ratio is ``None`` or below threshold.
    """

    dormant: frozenset[str]
    sparse: frozenset[str]
    healthy: frozenset[str]
    distillation_ratio: float | None
    under_distilled: bool


def memory_utilization(
    layer_counts: dict[str, int],
    *,
    floor: int = 50,
    under_distilled_threshold: float = 100.0,
) -> MemoryUtilizationReport:
    """Classify memory-layer record counts and compute the distillation ratio (item 106).

    Args:
        layer_counts:
            Per-layer record counts, e.g.
            ``{"journey_point": 278741, "neuron": 18, "learnings": 10,
              "compound_learnings": 0, "mem0": 0, "vault_notes": 150}``.
            Injected — no live SurrealDB read is made.
        floor:
            Minimum count for a layer to be considered ``healthy``.  Layers with
            ``0 < count < floor`` are ``sparse``; layers with ``count == 0`` are
            ``dormant``.  Defaults to 50.
        under_distilled_threshold:
            Distillation ratio at or above which the report signals
            ``under_distilled=True``.  Defaults to 100.0 (100:1 raw:distilled).

    Returns:
        A :class:`MemoryUtilizationReport` with per-layer classification and
        distillation health flags.  Empty ``layer_counts`` → all sets empty,
        ``distillation_ratio=None``, ``under_distilled=False``.

    Pure (injected inputs; no inference, no DB call).
    """
    dormant: set[str] = set()
    sparse: set[str] = set()
    healthy: set[str] = set()

    for name, count in layer_counts.items():
        if count == 0:
            dormant.add(name)
        elif count < floor:
            sparse.add(name)
        else:
            healthy.add(name)

    # Compute distillation ratio: raw / sum(distilled layers present in counts).
    raw_count: int = layer_counts.get(_RAW_LAYER, 0)
    distilled_total: int = sum(layer_counts[k] for k in _DISTILLED_LAYERS if k in layer_counts)
    if distilled_total == 0:
        ratio: float | None = None
        under_distilled = False
    else:
        ratio = raw_count / distilled_total
        under_distilled = ratio >= under_distilled_threshold

    return MemoryUtilizationReport(
        dormant=frozenset(dormant),
        sparse=frozenset(sparse),
        healthy=frozenset(healthy),
        distillation_ratio=ratio,
        under_distilled=under_distilled,
    )
