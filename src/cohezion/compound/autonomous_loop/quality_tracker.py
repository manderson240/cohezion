"""Quality Tracker — Markov chain over skill improvement states.

Pulls quality history from SurrealDB vault_neuron and builds per-category
transition matrices. Used by _build_backlog() to weight task priority by
expected improvement delta rather than static integers.

States:
  FAILING   — quality_score < 0.3 (model output poor or empty)
  IMPROVING — 0.3 ≤ quality_score < 0.7 (partial improvement)
  PLATEAU   — quality_score ≥ 0.7 (consistently good output)
  REGRESSING — quality_score dropped > 0.3 from prior (backslide)

Recursive trace: walk the task's vault history backward N steps to
find its current state and estimate the transition probability to PLATEAU.
"""

from __future__ import annotations

import json
import logging
import urllib.request
from typing import Any


logger = logging.getLogger(__name__)

_SURREAL_URL = "http://localhost:8001/sql"
_SURREAL_HEADERS = {
    "Content-Type": "text/plain",
    "surreal-ns": "cohezion",
    "surreal-db": "main",
    "Accept": "application/json",
    "Authorization": "Basic cm9vdDpyb290",
}

# Quality state thresholds
_FAILING_MAX = 0.3
_PLATEAU_MIN = 0.7
_REGRESSION_DROP = 0.3

# State names
FAILING = "failing"
IMPROVING = "improving"
PLATEAU = "plateau"
REGRESSING = "regressing"


def _quality_state(score: float, prev_score: float | None = None) -> str:
    if prev_score is not None and (prev_score - score) >= _REGRESSION_DROP:
        return REGRESSING
    if score >= _PLATEAU_MIN:
        return PLATEAU
    if score < _FAILING_MAX:
        return FAILING
    return IMPROVING


def _surreal_query(sql: str, timeout: float = 3.0) -> list[dict[str, Any]]:
    try:
        req = urllib.request.Request(  # noqa: S310
            _SURREAL_URL,
            data=sql.encode(),
            headers=_SURREAL_HEADERS,
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=timeout) as resp:  # noqa: S310
            data = json.loads(resp.read())
        return data[0].get("result", []) if isinstance(data, list) else []
    except Exception as exc:
        logger.debug("SurrealDB quality query failed: %s", exc)
        return []


def _fetch_quality_history(category: str, limit: int = 100) -> list[tuple[str, float]]:
    """Return [(task_id, quality_score), ...] ordered oldest-first."""
    sql = (
        f"SELECT task_id, quality_score FROM vault_neuron "
        f"WHERE category = '{category}' AND quality_score IS NOT NULL "
        f"ORDER BY recorded_at ASC LIMIT {limit};"
    )
    rows = _surreal_query(sql)
    return [(r["task_id"], float(r["quality_score"])) for r in rows if "quality_score" in r]


class MarkovQualityTracker:
    """Markov chain estimator for skill quality improvement trajectories.

    Usage:
        tracker = MarkovQualityTracker.from_vault()
        priority_weight = tracker.expected_improvement("skill_improvement")
        # Returns float 0-1: higher = more expected improvement from next task
    """

    def __init__(
        self, transition_matrix: dict[str, dict[str, float]], current_states: dict[str, str]
    ) -> None:
        self._matrix = transition_matrix  # {from_state: {to_state: probability}}
        self._current = current_states  # {category: current_state}

    @classmethod
    def from_vault(cls, categories: list[str] | None = None) -> MarkovQualityTracker:
        """Build tracker from SurrealDB history. Falls back gracefully if offline."""
        if categories is None:
            categories = ["skill_improvement", "code_quality", "compound_health"]

        # Collect all transitions across categories
        all_transitions: list[tuple[str, str]] = []
        current_states: dict[str, str] = {}

        for cat in categories:
            history = _fetch_quality_history(cat)
            if len(history) < 2:
                current_states[cat] = FAILING
                continue

            scores = [q for _, q in history]
            states = []
            for i, score in enumerate(scores):
                prev = scores[i - 1] if i > 0 else None
                states.append(_quality_state(score, prev))

            # Current state = last state in history
            current_states[cat] = states[-1]

            # Collect transitions
            for i in range(len(states) - 1):
                all_transitions.append((states[i], states[i + 1]))

        # Build transition matrix from counts (Laplace smoothed)
        state_names = [FAILING, IMPROVING, PLATEAU, REGRESSING]
        counts: dict[str, dict[str, float]] = {
            s: dict.fromkeys(state_names, 0.1) for s in state_names
        }
        for from_s, to_s in all_transitions:
            counts[from_s][to_s] += 1.0

        # Normalize to probabilities
        matrix: dict[str, dict[str, float]] = {}
        for from_s, to_counts in counts.items():
            total = sum(to_counts.values())
            matrix[from_s] = {t: c / total for t, c in to_counts.items()}

        logger.debug(
            "Markov quality tracker built: %d transitions across %d categories",
            len(all_transitions),
            len(categories),
        )
        return cls(matrix, current_states)

    def expected_improvement(self, category: str, steps: int = 3) -> float:
        """Estimate probability of reaching PLATEAU within `steps` transitions.

        Used as a priority multiplier: high value = this category is likely to
        improve with more iterations; low value = stuck/plateau already.

        Returns float in [0, 1].
        """
        current = self._current.get(category, FAILING)

        if current == PLATEAU:
            # Already at plateau — marginal value in more tasks
            return 0.2

        # Recursive N-step probability: P(reach PLATEAU within steps)
        def p_reach_plateau(state: str, remaining: int) -> float:
            if remaining == 0:
                return 1.0 if state == PLATEAU else 0.0
            if state == PLATEAU:
                return 1.0
            transitions = self._matrix.get(state, {})
            return sum(
                prob * p_reach_plateau(next_state, remaining - 1)
                for next_state, prob in transitions.items()
            )

        return p_reach_plateau(current, steps)

    def suggest_priority_weight(self, category: str) -> float:
        """Return a multiplier for task priority in this category.

        FAILING + high improvement chance → 1.5x (invest more)
        IMPROVING → 1.0x (steady state)
        PLATEAU → 0.5x (already good, reduce investment)
        REGRESSING → 1.8x (needs attention)
        """
        current = self._current.get(category, FAILING)
        p_improve = self.expected_improvement(category)

        if current == REGRESSING:
            return 1.8
        if current == PLATEAU:
            return 0.5
        # Weight by improvement probability — high P(improve) → higher weight
        return 0.8 + p_improve

    def summary(self) -> str:
        """Human-readable summary of current states and improvement probabilities."""
        lines = []
        for cat, state in sorted(self._current.items()):
            p = self.expected_improvement(cat)
            w = self.suggest_priority_weight(cat)
            lines.append(f"  {cat}: state={state} P(plateau/3)={p:.2f} weight={w:.2f}")
        return "\n".join(lines) if lines else "  (no history)"
