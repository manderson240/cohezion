"""Per-task model tournament (item 99, Thread N).

Generalises the RHO selector (items 22/42/61) from harness updates to MODELS: given a
``Task`` and a list of candidate ``ModelEntry`` objects, run a round-robin pairwise
tournament under an injectable ``prefer`` function and return the winner + win-tally +
margin (reusing the rho_selection_margin confidence signal pattern).

Report-only — PROPOSES a per-task winner, never auto-swaps the registry.  The injectable
``prefer`` defaults to a deterministic proxy (task_affinity fit → verified_working →
priority → cost); a live deployment swaps in measured eval scores OR an LLM-judge (the
"arena-as-judge" pattern, distilled 2026-06-06 from a Marktechpost LLM-Eval tutorial).

LLM-judge seam
--------------
Any callable matching ``(ModelEntry, ModelEntry, Task) -> ModelEntry`` that routes to
Granite-4.1-8B-GGUF via ``:13305 POST /api/v1/chat/completions`` at temp=0 with blind
pairwise outputs (judge sees model-A and model-B text, not model identities) is a valid
drop-in for ``prefer``.  No change to this module is required; the inference-bearing arm
is a call-site concern (item 99 backlog note, 2026-06-07).

Falsifiable checks (pure, no I/O)
----------------------------------
- 0 candidates → UNPROVEN (winner=None, margin=None).
- 1 candidate → uncontested winner, margin=0 (no runner-up).
- 2 candidates → winner by ``prefer``, margin=1 (one pairwise match, one win vs zero).
- decisive winner → high margin.
"""

from __future__ import annotations

from collections.abc import Callable
from dataclasses import dataclass

from cohezion.inference.registry import ModelEntry, Task


# Preference function: (model_a, model_b, task) -> preferred model.
# Default is the deterministic proxy.  Swap in an LLM-judge at call-site.
PreferenceFn = Callable[[ModelEntry, ModelEntry, Task], ModelEntry]


@dataclass(frozen=True)
class TournamentResult:
    """Result of a per-task model tournament.  ``winner=None`` == UNPROVEN."""

    winner: ModelEntry | None
    wins: dict[str, int]  # model_id -> pairwise win count
    margin: int | None  # winner_wins - runner_up_wins; None when winner is None
    task: Task
    rationale: str


def _default_preference(a: ModelEntry, b: ModelEntry, task: Task) -> ModelEntry:
    """Deterministic proxy: task affinity > verified_working > priority > cost > model_id.

    Criteria are applied in order; the first discriminating criterion decides.
    Tie-break is ascending model_id — replay-safe, no randomness.
    """
    # 1. Task affinity: does the model explicitly cover this task?
    a_affinity = task in a.task_affinity
    b_affinity = task in b.task_affinity
    if a_affinity != b_affinity:
        return a if a_affinity else b

    # 2. Prefer models that have been successfully invoked at least once.
    if a.verified_working != b.verified_working:
        return a if a.verified_working else b

    # 3. Lower priority value = preferred (fleet.py convention: lower = higher precedence).
    if a.priority != b.priority:
        return a if a.priority < b.priority else b

    # 4. Lower total cost.
    a_cost = a.cost_per_1k_input_usd + a.cost_per_1k_output_usd
    b_cost = b.cost_per_1k_input_usd + b.cost_per_1k_output_usd
    if a_cost != b_cost:
        return a if a_cost < b_cost else b

    # 5. Tie-break: lexicographically smallest model_id (deterministic, replay-safe).
    return a if a.model_id <= b.model_id else b


def model_tournament(
    task: Task,
    candidates: list[ModelEntry],
    *,
    prefer: PreferenceFn | None = None,
) -> TournamentResult:
    """Round-robin pairwise tournament over ``candidates`` for ``task``.

    Args:
        task: The ``Task`` the candidates are competing on.
        candidates: ModelEntry objects to include in the bake-off.  May be empty.
        prefer: Pairwise preference function ``(a, b, task) -> winner``.  Defaults to
            the deterministic proxy.  Inject an LLM-judge here for the inference-bearing
            arm (item 99 backlog, 2026-06-07).

    Returns:
        :class:`TournamentResult` — always; never raises.  ``winner=None`` when no
        winner can be determined (0 candidates → UNPROVEN).
    """
    prefer = prefer or _default_preference

    if not candidates:
        return TournamentResult(
            winner=None,
            wins={},
            margin=None,
            task=task,
            rationale="UNPROVEN: no candidate models",
        )

    if len(candidates) == 1:
        sole = candidates[0]
        return TournamentResult(
            winner=sole,
            wins={sole.model_id: 0},
            margin=0,
            task=task,
            rationale=f"uncontested: {sole.model_id} is the only candidate (margin 0)",
        )

    wins: dict[str, int] = {c.model_id: 0 for c in candidates}
    for i in range(len(candidates)):
        for j in range(i + 1, len(candidates)):
            preferred = prefer(candidates[i], candidates[j], task)
            wins[preferred.model_id] += 1

    # Deterministic winner: most wins; ties broken by ascending model_id (max of sorted).
    best_id = max(sorted(wins), key=lambda mid: wins[mid])
    winner = next(c for c in candidates if c.model_id == best_id)

    sorted_counts = sorted(wins.values(), reverse=True)
    top = sorted_counts[0]
    second = sorted_counts[1] if len(sorted_counts) > 1 else 0
    margin = top - second

    return TournamentResult(
        winner=winner,
        wins=wins,
        margin=margin,
        task=task,
        rationale=(
            f"preferred {winner.model_id} for task={task}: "
            f"{wins[best_id]} pairwise wins, margin {margin}"
        ),
    )


def model_tournament_report(
    task: Task,
    candidates: list[ModelEntry],
    *,
    prefer: PreferenceFn | None = None,
) -> dict:
    """Run the tournament and return a human-reviewable report dict.

    Report-only: PROPOSES a winner, never auto-swaps the registry.  Corresponds to
    item 99 (Thread N) in ``docs/IMPROVEMENT_BACKLOG.md``.

    The ``judge`` field names the preference strategy in effect so the report is
    self-describing: ``"deterministic-proxy"`` (default) or ``"injected"`` (LLM-judge
    or custom eval).
    """
    result = model_tournament(task, candidates, prefer=prefer)
    return {
        "task": str(task),
        "winner_id": result.winner.model_id if result.winner else None,
        "wins": result.wins,
        "margin": result.margin,
        "candidate_count": len(candidates),
        "rationale": result.rationale,
        # Seam annotation: injected prefer= enables the inference-bearing LLM-judge arm.
        "judge": "deterministic-proxy" if prefer is None else "injected",
    }
