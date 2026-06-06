"""RHO — Retrospective Harness Optimization self-preference selector (arXiv 2606.05922).

Item 22 (thread C). RHO (Pan et al., 2026) optimizes an agent's harness WITHOUT labeled
validation data: from past trajectories (the routing corpus, items 2/9), select a coreset of
hard (chronically-fallback) task classes, then pick the best candidate harness update by
PAIRWISE SELF-PREFERENCE — a round-robin tournament where the update that best covers the
demonstrated pain wins. No corpus / no candidates → honest UNPROVEN (``winner=None``), never a
fabricated pick.

This is the SELECTOR instrument only; wiring the winner INTO ``compound.SkillRefiner`` is a
separate behavior-change (deferred), so this module is additive + falsifiable. The preference
function is injectable — the default is a self-consistency proxy (coverage of the coreset); a
real deployment can swap in an LLM-judged pairwise self-preference without changing the
tournament logic.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path

from cohezion.models.routing_log import propose_tuning, read_routing_decisions


@dataclass(frozen=True)
class HarnessCandidate:
    """A candidate harness update to be evaluated by RHO self-preference."""

    candidate_id: str
    description: str
    targets: frozenset[str]  # task classes this update addresses


@dataclass(frozen=True)
class RHOSelection:
    """Result of an RHO pairwise self-preference tournament. ``winner=None`` == UNPROVEN."""

    winner: HarnessCandidate | None
    wins: dict[str, int]
    coreset: tuple[str, ...]  # the chronically-fallback task classes RHO re-solved
    rationale: str


# A preference function returns the preferred of two candidates given the fallback coreset.
PreferenceFn = Callable[[HarnessCandidate, HarnessCandidate, tuple[str, ...]], HarnessCandidate]


def _default_preference(
    a: HarnessCandidate, b: HarnessCandidate, coreset: tuple[str, ...]
) -> HarnessCandidate:
    """Self-consistency proxy: prefer the candidate covering MORE of the coreset's pain.

    Ties break on the lexicographically-smaller ``candidate_id`` — deterministic, no
    randomness (so the tournament is replay-safe, like the rest of the corpus tooling).
    """
    core = set(coreset)
    cov_a = len(a.targets & core)
    cov_b = len(b.targets & core)
    if cov_a != cov_b:
        return a if cov_a > cov_b else b
    return a if a.candidate_id <= b.candidate_id else b


def select_harness_update(
    records: list[dict],
    candidates: list[HarnessCandidate],
    *,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
    prefer: PreferenceFn | None = None,
) -> RHOSelection:
    """Pick the self-preferred harness update over the routing corpus's fallback coreset.

    The coreset is the set of chronically-fallback task classes (via :func:`propose_tuning`).
    With no coreset (fresh/healthy corpus) or no candidates, returns an UNPROVEN selection
    (``winner=None``) — never fabricates a pick. Otherwise runs a round-robin pairwise
    tournament under ``prefer`` and returns the candidate with the most wins (ties → smallest
    ``candidate_id``, deterministic).
    """
    prefer = prefer or _default_preference
    coreset = tuple(
        p.target
        for p in propose_tuning(
            records, min_samples=min_samples, fallback_threshold=fallback_threshold
        )
    )
    if not coreset:
        return RHOSelection(None, {}, coreset, "UNPROVEN: no chronically-fallback coreset")
    if not candidates:
        return RHOSelection(None, {}, coreset, "UNPROVEN: no candidate harness updates")

    wins: dict[str, int] = {c.candidate_id: 0 for c in candidates}
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            winner = prefer(candidates[i], candidates[j], coreset)
            wins[winner.candidate_id] += 1

    # Most wins; deterministic tie-break by ascending candidate_id (max returns first match).
    best_id = max(sorted(wins), key=lambda cid: wins[cid])
    winner = next(c for c in candidates if c.candidate_id == best_id)
    cov = len(winner.targets & set(coreset))
    return RHOSelection(
        winner=winner,
        wins=wins,
        coreset=coreset,
        rationale=(
            f"self-preferred {winner.candidate_id}: covers {cov}/{len(coreset)} of the "
            f"fallback coreset ({wins[best_id]} pairwise wins)"
        ),
    )


def select_harness_update_from_log(
    candidates: list[HarnessCandidate],
    *,
    path: Path | None = None,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
    prefer: PreferenceFn | None = None,
) -> RHOSelection:
    """Read the routing corpus and run RHO selection. No corpus → UNPROVEN (honest)."""
    return select_harness_update(
        read_routing_decisions(path=path),
        candidates,
        min_samples=min_samples,
        fallback_threshold=fallback_threshold,
        prefer=prefer,
    )


def generate_harness_candidates(
    records: list[dict],
    *,
    min_samples: int = 5,
    fallback_threshold: float = 0.5,
) -> list[HarnessCandidate]:
    """One ``HarnessCandidate`` per chronically-fallback task class (item 33).

    Closes item-27's loop: :func:`select_harness_update` needs candidates handed in; this
    derives them AUTONOMOUSLY from the routing corpus by reusing :func:`propose_tuning` (item 9).
    Each chronically-fallback task class becomes a candidate that recruits a task-specialist for
    it. A healthy or empty corpus yields ``[]`` (UNPROVEN — never a fabricated candidate), and a
    class below ``min_samples`` is noise, not a candidate (the same evidence gate as propose_tuning).
    """
    proposals = propose_tuning(
        records, min_samples=min_samples, fallback_threshold=fallback_threshold
    )
    return [
        HarnessCandidate(
            candidate_id=f"recruit:{p.target}",
            description=f"recruit a task-specialist for {p.target} ({p.metric:.0%} fallback)",
            targets=frozenset({p.target}),
        )
        for p in proposals
    ]
