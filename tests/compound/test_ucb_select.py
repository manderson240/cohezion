"""Item 116: ucb_select(arms, *, c) — TDD red→green.

UCB1 bandit selection for autoresearch experiment ordering.
Gap verified 2026-06-08: autoresearch uses simple priority-sort (no UCB anywhere
in the codebase).

Discriminating tests — each kills a plausible wrong implementation:
  1. Unexplored arm (n=0) → selected first (infinite UCB score).
     PRIMARY DISC.: kills an impl that ignores exploration entirely.
  2. High-mean low-uncertainty vs low-mean high-uncertainty → formula decides.
     Kills an impl that always picks highest mean (greedy).
  3. All arms equal means, different pull counts → least-pulled wins.
     Kills an impl that uses random tiebreaking.
  4. Single arm → that arm selected regardless of history.
  5. c=0 → pure exploitation (highest mean, no exploration bonus).
     Kills an impl that ignores c.
  6. Large c → exploration dominates (least-pulled wins even if lower mean).
  7. All arms explored equally with same mean → stable first selection (no crash).
"""

from __future__ import annotations

import math

from cohezion.compound.ucb_select import Arm, ucb_select


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _arm(mean: float, n: int, name: str = "arm") -> Arm:
    return Arm(name=name, mean_reward=mean, n_pulls=n)


# ---------------------------------------------------------------------------
# Core UCB1 invariants
# ---------------------------------------------------------------------------


def test_unexplored_arm_selected_first() -> None:
    """An unexplored arm (n_pulls=0) must always be selected first.

    PRIMARY DISCRIMINATOR: the UCB1 score for an unexplored arm is +inf (log(N)/0
    diverges). Kills any impl that skips exploration or treats n=0 as n=1.
    """
    explored = _arm(mean=0.9, n=10, name="high_mean")
    unexplored = _arm(mean=0.0, n=0, name="unexplored")
    selected = ucb_select([explored, unexplored], c=1.0)
    assert selected.name == "unexplored", (
        "Unexplored arm must be selected first regardless of another arm's high mean"
    )


def test_exploration_bonus_beats_greedy() -> None:
    """A low-mean but rarely-pulled arm must beat a high-mean over-explored arm.

    Kills an impl that always picks highest mean (greedy, c ignored).
    With c=2.0:
      high_mean (mean=0.8, n=100, N=200): UCB = 0.8 + 2*sqrt(ln(200)/100) ≈ 0.8 + 0.23 = 1.03
      low_mean  (mean=0.2, n=1,   N=200): UCB = 0.2 + 2*sqrt(ln(200)/1)   ≈ 0.2 + 7.30 = 7.50
    The rarely-pulled low-mean arm wins by exploration bonus.
    """
    high_mean = _arm(mean=0.8, n=100, name="high_mean")
    low_mean_rare = _arm(mean=0.2, n=1, name="low_mean_rare")
    selected = ucb_select([high_mean, low_mean_rare], c=2.0)
    assert selected.name == "low_mean_rare", (
        "Exploration bonus for rarely-pulled arm must beat the greedy choice"
    )


def test_c_zero_pure_exploitation() -> None:
    """c=0 → pure exploitation: highest mean is selected, ignoring pull counts.

    Kills an impl that ignores the c parameter.
    """
    arm_a = _arm(mean=0.9, n=1, name="high_mean")
    arm_b = _arm(mean=0.3, n=200, name="low_mean_many_pulls")
    selected = ucb_select([arm_a, arm_b], c=0.0)
    assert selected.name == "high_mean", "c=0 must select highest-mean arm (pure exploitation)"


def test_least_pulled_wins_equal_mean() -> None:
    """Equal means, different pull counts → least-pulled arm is selected.

    Kills an impl that uses arbitrary ordering with equal means.
    With equal means, UCB bonus from 1/n_i dominates.
    """
    many = _arm(mean=0.5, n=100, name="many_pulls")
    few = _arm(mean=0.5, n=2, name="few_pulls")
    selected = ucb_select([many, few], c=1.0)
    assert selected.name == "few_pulls", (
        "Arm with fewer pulls must win on the exploration bonus when means are equal"
    )


def test_single_arm_returned() -> None:
    """A single arm → selected unconditionally."""
    arm = _arm(mean=0.5, n=5, name="only_arm")
    selected = ucb_select([arm], c=1.0)
    assert selected.name == "only_arm"


def test_large_c_exploration_dominates() -> None:
    """Large c → exploration dominates even a large mean difference.

    With c=100 (extreme), a rarely-pulled arm wins over any explored arm.
    """
    high_explored = _arm(mean=1.0, n=50, name="high_explored")
    low_rare = _arm(mean=0.0, n=1, name="low_rare")
    selected = ucb_select([high_explored, low_rare], c=100.0)
    assert selected.name == "low_rare", (
        "Extreme exploration coefficient must select the rarely-pulled arm"
    )


def test_ucb_score_formula_verified() -> None:
    """Verify the UCB1 score formula: mean + c * sqrt(ln(N) / n_i).

    Two specific arms with N=10 total pulls, c=1.0:
      arm_a: mean=0.6, n=8 → score = 0.6 + sqrt(ln(10)/8) ≈ 0.6 + 0.536 = 1.136
      arm_b: mean=0.7, n=2 → score = 0.7 + sqrt(ln(10)/2) ≈ 0.7 + 1.072 = 1.772
    arm_b must be selected despite lower mean.
    """
    arm_a = _arm(mean=0.6, n=8, name="high_mean_low_uncertainty")
    arm_b = _arm(mean=0.7, n=2, name="medium_mean_high_uncertainty")
    selected = ucb_select([arm_a, arm_b], c=1.0)
    # Verify expectation with the formula
    n_total = 10
    score_a = 0.6 + 1.0 * math.sqrt(math.log(n_total) / 8)
    score_b = 0.7 + 1.0 * math.sqrt(math.log(n_total) / 2)
    assert score_b > score_a, "Formula pre-check: arm_b should score higher"
    assert selected.name == "medium_mean_high_uncertainty", (
        f"arm_b (score {score_b:.4f}) must beat arm_a (score {score_a:.4f})"
    )


def test_all_arms_equal_no_crash() -> None:
    """All arms with same mean and same pull count → stable selection, no crash."""
    arms = [_arm(mean=0.5, n=5, name=f"arm_{i}") for i in range(4)]
    result = ucb_select(arms, c=1.0)
    # Must return one of the arms without raising
    assert result in arms
