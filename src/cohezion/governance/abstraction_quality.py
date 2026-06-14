"""Items 92 + 152 + 154 — Neuron-deposit abstraction-quality audit and trend (report-only).

Grounded in arXiv 2606.04703 (ExpInternalization, June 2026):
  "Abstract principle-level experience beats instance-specific detail for stable self-evolution."

A neuron is INSTANCE-SPECIFIC when its content carries volatile tokens that anchor it to a
single occurrence rather than a generalizable principle: file paths, SHA/hex commit hashes,
ISO 8601 timestamps, UUIDs, and explicit line-number references.

Neurons that contain only incidental numbers (``"2-layer decoder"``, ``"beta below 0.01"``)
are NOT flagged — a bare number is not a volatile token.  The discrimination is:
  STRONG_PATTERN match → instance_specific = True  (path / SHA / UUID / timestamp / line-ref)
  No strong match      → instance_specific = False (principle level, even with numbers)

This is a fourth dimension on top of item-52 (non-redundancy / evidence / format) and
item-55 (coverage).  Read-only; pure over injected neuron list; no SurrealDB write.
"""

from __future__ import annotations

import re
from collections.abc import Iterable
from dataclasses import dataclass, field


# ---------------------------------------------------------------------------
# Volatile-token pattern catalogue (STRONG: one match → instance_specific)
# ---------------------------------------------------------------------------

_PATTERNS: list[tuple[str, re.Pattern[str]]] = [
    (
        "absolute_path",
        re.compile(
            r"""
            (?:
                /[A-Za-z0-9_.~-]+(?:/[A-Za-z0-9_.~-]+)+  # Unix absolute path ≥2 levels
            |
                [A-Z]:\\[A-Za-z0-9_.\\-]+                  # Windows absolute path
            )
            """,
            re.VERBOSE,
        ),
    ),
    (
        "sha_hex",
        re.compile(
            r"\b[0-9a-f]{10,}\b",  # 10+ hex chars (covers SHA-40, abbreviated SHA ≥10)
        ),
    ),
    (
        "uuid",
        re.compile(
            r"\b[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}\b",
            re.IGNORECASE,
        ),
    ),
    (
        "iso_timestamp",
        re.compile(
            r"\b\d{4}-\d{2}-\d{2}T\d{2}:\d{2}",  # ISO 8601 datetime (date + time part)
        ),
    ),
    (
        "line_reference",
        re.compile(
            r"""
            (?:
                \bline\s+\d+\b          # "line 231"
            |
                :\d+:\d*                # ":231:" or ":231:5" (file:line:col)
            |
                \.py:\d+                # "executor.py:231"
            )
            """,
            re.VERBOSE | re.IGNORECASE,
        ),
    ),
]


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class AbstractionFlag:
    """Abstraction-quality verdict for one neuron.

    Attributes
    ----------
    name:
        The neuron's ``name`` field (or empty string if absent).
    instance_specific:
        ``True`` when the neuron content carries at least one volatile token
        (path / SHA / UUID / ISO timestamp / line reference).
        ``False`` for principle-level abstractions.
    reasons:
        The volatile token pattern names that matched (empty when not flagged).
    """

    name: str
    instance_specific: bool
    reasons: list[str] = field(default_factory=list)


def abstraction_quality(neurons: Iterable[object]) -> list[AbstractionFlag]:
    """Audit each neuron for instance-specific (volatile) content.

    Args:
        neurons: Iterable of neuron dicts; each should have a ``"name"`` string
            and a ``"content"`` string.  Non-dict entries are silently skipped.
            Missing ``"name"`` or ``"content"`` keys fall back to empty strings.

    Returns:
        One :class:`AbstractionFlag` per neuron dict, in input order.
        ``instance_specific=True`` when at least one STRONG volatile-token pattern
        matches the content.  ``False`` for clean, principle-level neurons.

    Pure (no I/O, no SurrealDB).  Use an injected neuron list in tests.
    """
    flags: list[AbstractionFlag] = []

    for neuron in neurons:
        if not isinstance(neuron, dict):
            continue

        name = str(neuron.get("name") or "")
        content = str(neuron.get("content") or "")

        matched: list[str] = []
        for label, pattern in _PATTERNS:
            if pattern.search(content):
                matched.append(label)

        flags.append(
            AbstractionFlag(
                name=name,
                instance_specific=bool(matched),
                reasons=matched,
            )
        )

    return flags


def abstraction_quality_delta(
    before_flags: list[AbstractionFlag],
    after_flags: list[AbstractionFlag],
) -> dict[str, list[AbstractionFlag]]:
    """Delta between two abstraction-quality snapshots — item 152 (2026-06-08).

    Compares before/after :class:`AbstractionFlag` snapshots by neuron ``name``
    and classifies each change:

    - **improved**: ``instance_specific=True`` in before, ``False`` in after
      (was volatile / polluted with concrete tokens; now principle-level).
    - **degraded**: ``instance_specific=False`` in before, ``True`` in after
      (was principled; now carries volatile tokens).

    Neurons stable in both snapshots (no change to ``instance_specific``) are
    in neither list.  Neurons absent from one snapshot are also excluded.

    Args:
        before_flags:
            Abstraction flags from the EARLIER snapshot (output of
            :func:`abstraction_quality`).
        after_flags:
            Abstraction flags from the LATER snapshot.

    Returns:
        ``{"improved": [...], "degraded": [...]}`` — only the flags that
        changed direction, matched by name.

    Pure (no I/O).  Report-only.
    """
    before_by_name: dict[str, AbstractionFlag] = {f.name: f for f in before_flags}
    after_by_name: dict[str, AbstractionFlag] = {f.name: f for f in after_flags}

    improved: list[AbstractionFlag] = []
    degraded: list[AbstractionFlag] = []

    for name, after_flag in after_by_name.items():
        before_flag = before_by_name.get(name)
        if before_flag is None:
            continue  # new neuron — not a delta (no baseline to compare against)
        if before_flag.instance_specific and not after_flag.instance_specific:
            improved.append(after_flag)
        elif not before_flag.instance_specific and after_flag.instance_specific:
            degraded.append(after_flag)
        # else: stable — in neither list

    return {"improved": improved, "degraded": degraded}


def abstraction_quality_trend(
    deltas: list[dict[str, list[AbstractionFlag]]],
) -> dict[str, object]:
    """Summarise a time-series of abstraction-quality deltas — item 154 (2026-06-08).

    Folds a list of :func:`abstraction_quality_delta` outputs into a single
    trend report.  Each element of *deltas* contributes its ``len(improved)``
    and ``len(degraded)`` to the running totals; no deduplication by neuron name
    is performed (a neuron that improves in tick 1 and degrades in tick 2
    contributes 1 to each total — intentional, records both events).

    Args:
        deltas:
            A ``list[dict]`` where each dict has ``"improved"`` and
            ``"degraded"`` keys each holding a ``list[AbstractionFlag]``
            (the direct output of :func:`abstraction_quality_delta`).  An
            empty list is valid and returns all-zero totals.

    Returns:
        A dict with three keys:

        - ``"net_improved"`` (:class:`int`) — total improved-flag events
          across all ticks.
        - ``"net_degraded"`` (:class:`int`) — total degraded-flag events
          across all ticks.
        - ``"trend"`` (``"improving" | "degrading" | "stable"``) — set to
          ``"improving"`` when ``net_improved > net_degraded``, ``"degrading"``
          when ``net_degraded > net_improved``, and ``"stable"`` when equal
          (including the zero-zero case from an empty list).

    Pure (no I/O).  Report-only.
    """
    net_improved: int = 0
    net_degraded: int = 0

    for delta in deltas:
        net_improved += len(delta.get("improved") or [])
        net_degraded += len(delta.get("degraded") or [])

    if net_improved > net_degraded:
        trend = "improving"
    elif net_degraded > net_improved:
        trend = "degrading"
    else:
        trend = "stable"

    return {
        "net_improved": net_improved,
        "net_degraded": net_degraded,
        "trend": trend,
    }
