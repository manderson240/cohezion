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

_NEURON_COUNTRIES = ("inference", "skill", "cerebellum")
# A neuron's tags mix the task_class with structural labels and the lane (schemas differ per country:
# inference=[lane,"rewarded",task_class], skill=["skill",skill_name], cerebellum=[country,"procedural",
# task_class,lane]). The task_class is read from the tags by EXCLUDING this structural/lane denylist.
# Documented limitation: a task_class that collides with a structural/lane token would be excluded
# (rare; a coverage list is a smell, not a verdict).
_STRUCTURAL_TAGS = frozenset(
    {
        "inference",
        "skill",
        "cerebellum",  # country labels
        "procedural",
        "rewarded",
        "distilled",  # deposit structural labels
        "npu",
        "igpu",
        "cpu",
        "igpu_unified",
        "igpu_rocwmma",
        "cloud",
        "cli",  # lane vocabulary
    }
)


def _task_classes_of(neuron: dict) -> set[str]:
    """The task_class tag(s) of a neuron = its tags minus the structural/lane denylist."""
    return {str(t) for t in (neuron.get("tags") or []) if str(t) not in _STRUCTURAL_TAGS}


def memory_coverage(store: Iterable[object]) -> dict[str, set[str]]:
    """Per neuron country, the SET of task classes the fleet has procedural memory for (item 55).

    "What does the fleet remember?" — the observability complement to item-37's per-task recall.
    Reads the task_class from each neuron's TAGS (not its name) via ``_task_classes_of``. Always
    returns exactly the three country keys; a country with no neurons maps to an empty set. Pure —
    read-only over the injected ``store`` (no SurrealDB), non-dict entries ignored.
    """
    coverage: dict[str, set[str]] = {c: set() for c in _NEURON_COUNTRIES}
    for neuron in store:
        if not isinstance(neuron, dict):
            continue
        country = str(neuron.get("country", ""))
        if country in coverage:
            coverage[country] |= _task_classes_of(neuron)
    return coverage


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
