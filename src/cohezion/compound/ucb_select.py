"""Item 116: UCB1 bandit selection for autoresearch experiment ordering.

Verified gap 2026-06-08: cohezion's autoresearch uses simple priority-sort (1-10
integer). No UCB/UCT anywhere in the codebase. This module fills the gap.

``ucb_select(arms, *, c)`` returns the arm that maximises the UCB1 score:

    score(i) = μᵢ + c * sqrt(ln(N) / nᵢ)

where:
  - μᵢ  = ``arm.mean_reward``        (estimated quality/yield)
  - N   = Σ nᵢ                       (total pulls across all arms)
  - nᵢ  = ``arm.n_pulls``            (pulls for this arm)
  - c   = exploration coefficient    (higher → more exploration)

Unexplored arms (nᵢ = 0) get score +∞ and are always selected first.
When c = 0, the selector degrades to pure greedy (highest mean).

Designed to compose with ``CompoundAutoresearch.opportunities()`` — the
``ImprovementOpportunity.priority`` field (1-10) can seed ``mean_reward``; nᵢ
is the number of times that experiment class has been tried so far.

Pure (no side effects, no network calls, no writes).  Report-only selector.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class Arm:
    """A bandit arm representing one experiment/curriculum item (item 116).

    Attributes
    ----------
    name:
        Human-readable identifier for the experiment or task class.
    mean_reward:
        Estimated quality or yield of this arm (e.g. coherence delta, metric
        improvement).  Should be in [0, 1] for UCB1 to behave predictably,
        but any float is accepted.
    n_pulls:
        Number of times this arm has been tried.  Zero means unexplored.
    """

    name: str
    mean_reward: float
    n_pulls: int


# ---------------------------------------------------------------------------
# ucb_select
# ---------------------------------------------------------------------------


def ucb_select(arms: list[Arm], *, c: float) -> Arm:
    """Return the arm that maximises the UCB1 score (item 116). READ-ONLY.

    Exploration-exploitation trade-off:
    - Unexplored arms (``n_pulls == 0``) always score +∞ → selected first.
    - When ``c == 0``, pure exploitation: highest ``mean_reward`` wins.
    - When ``c > 0``, rarely-pulled arms get an exploration bonus that
      decays as they accumulate pulls.

    Args:
        arms:
            Non-empty list of :class:`Arm` objects.  Must contain at least one
            element; behaviour on an empty list is undefined (raises IndexError).
        c:
            Exploration coefficient.  Typical values: 1.0 (balanced),
            sqrt(2) ≈ 1.414 (UCB1 default), 0.0 (pure greedy).

    Returns:
        The :class:`Arm` with the highest UCB1 score.  When multiple arms tie
        (identical scores), the first one in ``arms`` order is returned
        (stable, deterministic).

    Pure (no writes, no network calls).
    """
    n_total: int = sum(a.n_pulls for a in arms)

    best_arm: Arm = arms[0]
    best_score: float = _ucb_score(arms[0], n_total=n_total, c=c)

    for arm in arms[1:]:
        score = _ucb_score(arm, n_total=n_total, c=c)
        if score > best_score:
            best_score = score
            best_arm = arm

    return best_arm


def _ucb_score(arm: Arm, *, n_total: int, c: float) -> float:
    """Compute the UCB1 score for a single arm.

    Returns +inf for unexplored arms (``n_pulls == 0``) so they are always
    selected before any explored arm.

    When ``c == 0`` or ``n_total == 0``, the exploration term is 0.0 and
    the score reduces to ``mean_reward`` (pure exploitation).
    """
    if arm.n_pulls == 0:
        return math.inf

    if c == 0.0 or n_total <= 0:
        return arm.mean_reward

    exploration_bonus = c * math.sqrt(math.log(n_total) / arm.n_pulls)
    return arm.mean_reward + exploration_bonus
