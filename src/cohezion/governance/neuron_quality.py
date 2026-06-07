"""Neuron-store deposit-quality audit (item 52, 2026-06-06) — report-only.

Prompted by arXiv 2605.31075 (TaskMem) — its memory-quality REWARD TAXONOMY
(non-redundancy / accuracy / format), NOT its RL-on-30B-VL method (off-stack/off-modality). Measures
those three dimensions over DEPOSITED neurons (items 15/16/24): the FleetHealthSpecialist (item 36)
COUNTS deposits but never assesses QUALITY — this closes that gap. Read-only complement to item-51's
write-time dedup; operates on an injected neuron list, so it never reads SurrealDB under pytest.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass


# A well-formed neuron must carry these (country+name for addressing, tags for recall — item 29
# recall_neurons filters by tags, so an untagged neuron is unrecallable = format-invalid).
_REQUIRED_FIELDS = ("country", "name", "tags")


@dataclass(frozen=True)
class DepositQualityReport:
    """TaskMem-style quality over deposited neurons. All three views are report-only."""

    redundant: dict[str, int]  # name -> count, for names deposited more than once
    low_evidence: list[str]  # neuron names whose reward is strictly below the evidence floor
    format_invalid: list[str]  # neuron names missing a required field (or "<unnamed>")


def deposit_quality_report(
    neurons: Iterable[object],
    *,
    evidence_floor: float = 0.5,
) -> DepositQualityReport:
    """Audit a neuron list on TaskMem's 3 dimensions (item 52). Pure — no SurrealDB, no writes.

    - **non-redundancy**: ``{name: count}`` for names deposited >1 time (the duplicates item-51's
      ``deposit_cerebellum_if_novel`` prevents at write time — this finds any already present).
    - **evidence**: neuron names whose ``reward`` is strictly ``< evidence_floor`` (weak evidence).
    - **format**: neuron names missing any of country/name/tags (an untagged neuron is unrecallable).

    Non-dict entries are ignored (fail-soft). A clean store yields all-empty views.
    """
    dicts = [n for n in neurons if isinstance(n, dict)]

    counts = Counter(str(n["name"]) for n in dicts if n.get("name"))
    redundant = {name: c for name, c in counts.items() if c >= 2}

    low_evidence = sorted(
        str(n.get("name", "<unnamed>"))
        for n in dicts
        if float(n.get("reward", 1.0)) < evidence_floor
    )

    format_invalid = sorted(
        str(n.get("name", "<unnamed>"))
        for n in dicts
        if any(not n.get(field) for field in _REQUIRED_FIELDS)
    )

    return DepositQualityReport(
        redundant=redundant,
        low_evidence=low_evidence,
        format_invalid=format_invalid,
    )
