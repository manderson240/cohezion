"""Item 88 — Experiential-loop closure instrument (report-only, Thread M).

Measures whether ACCEPTED agent outcomes were memorialized as neurons — the gap between
"outcome accepted by AUTODQA" and "outcome deposited as procedural memory".

  accepted + matching neuron  →  CLOSED  (the experiential loop closed for this outcome)
  accepted + no neuron        →  OPEN GAP (learning was accepted but not preserved)
  REJECTED outcome            →  EXCLUDED (never counted — AUTODQA I6 spirit; no back-door deposit)

The conjunction (accepted AND deposited) is the loop-closure discriminator.
Gate for item 90 (``LocalInferenceAgent`` auto-deposit behaviour-change).

Report-only: injected neurons list (no SurrealDB read under pytest); no writes.
"""

from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass


@dataclass(frozen=True)
class Outcome:
    """A single agent outcome — the unit the experiential loop processes.

    Attributes
    ----------
    key:
        The identifying token for this outcome: a skill name, task class, or session key.
        Used to look up a matching neuron in the deposited store (the neuron must have
        ``key`` in its ``tags``).
    accepted:
        ``True`` = AUTODQA verdict ACCEPTED — the outcome is a genuine learning candidate.
        ``False`` = REJECTED — excluded from all closure reporting (AUTODQA I6 spirit).
    """

    key: str
    accepted: bool


@dataclass(frozen=True)
class ClosureReport:
    """Experiential loop closure audit result.

    Attributes
    ----------
    closed:
        Sorted keys of ACCEPTED outcomes that have a matching neuron — the loop closed.
    open_gaps:
        Sorted keys of ACCEPTED outcomes with NO matching neuron — learning was accepted
        but not yet deposited (a gap the item-90 auto-deposit will fill).
    """

    closed: list[str]
    open_gaps: list[str]


def experiential_closure_report(
    outcomes: Iterable[Outcome],
    neurons: Iterable[object],
) -> ClosureReport:
    """Report which accepted outcomes are closed (have a matching neuron) vs open (do not).

    Args:
        outcomes: Agent outcomes carrying ``key`` + ``accepted`` status.  REJECTED
            outcomes (``accepted=False``) are excluded from both lists — they must never
            appear in either ``closed`` or ``open_gaps``.
        neurons:  Deposited neuron dicts (from the injected store; no SurrealDB call).
            Each dict must have a ``"tags"`` key (a list of strings).  Non-dict entries
            and entries without ``"tags"`` are ignored.

    Returns:
        :class:`ClosureReport` with ``closed`` and ``open_gaps`` both sorted for
        determinism.  A key that appears in multiple accepted outcomes is deduplicated
        (one closed/gap entry per unique key).

    An outcome is "closed" when its ``key`` appears in any neuron's ``"tags"`` list.
    The match is case-sensitive and key-exact (same token as deposited; typically a
    task_class string like ``"RERANK"`` or a skill name).

    Report-only: never writes; pure over injected data.
    """
    # 1. Build the tag-set covering ALL deposited neurons.
    #    O(N_neurons × avg_tags_per_neuron) — small in practice (fleet has <100 neurons).
    all_tags: set[str] = set()
    for neuron in neurons:
        if not isinstance(neuron, dict):
            continue
        for tag in neuron.get("tags") or []:
            all_tags.add(str(tag))

    # 2. Classify accepted outcomes; reject others entirely.
    closed: list[str] = []
    open_gaps: list[str] = []
    seen: set[str] = set()

    for outcome in outcomes:
        if not outcome.accepted:
            continue  # REJECTED — excluded from both lists (I6 spirit)
        if outcome.key in seen:
            continue  # dedup: one entry per unique key
        seen.add(outcome.key)

        if outcome.key in all_tags:
            closed.append(outcome.key)
        else:
            open_gaps.append(outcome.key)

    return ClosureReport(
        closed=sorted(closed),
        open_gaps=sorted(open_gaps),
    )
