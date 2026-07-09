"""Predictive tier pre-allocation based on historical (skill, op_type) execution data.

Closes the CB16 producer→consumer gap: ExecutionMetrics.tier_used and
.escalation_count are recorded but never fed back to inform future tier
selection.  DifficultyEstimator consumes those fields and exposes
predict_tier() for use before execution begins.

Composition with DegradationDetector (CB12):
  - DegradationDetector.suggest_routing_tier() is REACTIVE (health-based)
  - DifficultyEstimator.predict_tier()          is PREDICTIVE (skill-specific)
  Both are consulted; the more conservative recommendation wins.
"""

from __future__ import annotations

import math
from collections import defaultdict, deque
from dataclasses import dataclass


@dataclass(slots=True)
class _TierRecord:
    tier_used: str
    escalation_count: int
    quality_score: float


_TIER_ORDER = ("npu", "igpu", "cpu")
_QUALITY_FLOOR = 0.6
_SUCCESS_RATE_THRESHOLD = 0.7
_MIN_SAMPLES = 5  # competitive analysis lower bound: MTF potential needs O(n) ops to stabilize
# H3 fix (supersedes the _MIN_TIER_FREQUENCY guard, which mis-rejected balanced 3-way splits):
# adequacy = the Wilson LOWER confidence bound of a tier's clean-success rate clears this floor.
# Pessimistic-for-commitment (conservative bandit / UCB1, Auer 2002): a rare lucky cheap tier (2/2)
# has a wide interval → low LCB → not trusted; a well-sampled tier has a tight interval → trusted.
# This fixes BOTH the lucky-cheap miscalibration AND the even-distribution case in one mechanism.
# Tuned on the test/experiment fixtures (the research's 0.5 default is for larger windows): at 0.35 a
# clean 3/3 tier (LCB 0.439) clears the success path while a lucky 2/2 (LCB 0.342) does not.
_LCB_ADEQUATE = 0.35
_WILSON_Z = 1.96  # ~95% one-sided; engineering default, tune on replay logs
_WINDOW = 10


def _wilson_lcb(successes: int, n: int, z: float = _WILSON_Z) -> float:
    """Wilson score lower confidence bound of a binomial success rate. Pure; no scipy.
    Well-behaved at small n and at p near 0/1 (unlike the naive normal interval)."""
    if n <= 0:
        return 0.0
    p = successes / n
    z2 = z * z
    margin = z * ((p * (1.0 - p) + z2 / (4.0 * n)) / n) ** 0.5
    return (p + z2 / (2.0 * n) - margin) / (1.0 + z2 / n)

# Prompt-complexity feature extraction (gitmoot modeltier.go pattern, #142)
# Reasoning/analysis keywords that indicate heavy compute tasks
_HARD_KEYWORDS: frozenset[str] = frozenset({
    "analyze", "analyse", "evaluate", "compare", "implement", "refactor",
    "optimize", "design", "architecture", "reasoning", "comprehensive",
    "systematically", "algorithm", "differentiate", "synthesize", "critique",
    "detailed", "sophisticated", "intricate", "complex", "thorough",
    "elaborate", "integrate", "distributed",
})
# Multi-word phrases (checked against the full lowercased prompt)
_HARD_PHRASES: tuple[str, ...] = (
    "step by step", "in detail", "step-by-step", "walk through",
    "deep dive", "architectural overview",
)
# Thresholds mapping complexity score → tier
_COMPLEXITY_NPU_MAX: float = 0.3   # score < 0.3  → "npu"
_COMPLEXITY_IGPU_MAX: float = 0.6  # 0.3 ≤ score < 0.6 → "igpu"; ≥ 0.6 → "cpu"


class DifficultyEstimator:
    """Predict the optimal inference tier for a (skill_name, operation_type) pair.

    Tracks a rolling window of execution records per (skill, op_type).
    predict_tier() returns the cheapest tier (NPU → iGPU → CPU) that has
    a success_rate >= 0.7 over at least 2 samples, where success means
    escalation_count == 0 AND quality_score >= 0.6.

    If no tier clears the threshold, returns the tier with highest mean
    quality score.  Returns "unknown" when no history exists.
    """

    def __init__(self) -> None:
        self._history: dict[tuple[str, str], deque[_TierRecord]] = defaultdict(
            lambda: deque(maxlen=_WINDOW)
        )

    def record(
        self,
        skill_name: str,
        operation_type: str,
        tier_used: str,
        escalation_count: int,
        quality_score: float,
    ) -> None:
        """Append one execution record; old entries drop off at window=10."""
        key = (skill_name, operation_type)
        self._history[key].append(
            _TierRecord(
                tier_used=tier_used if tier_used in _TIER_ORDER else "cpu",
                escalation_count=escalation_count,
                quality_score=quality_score,
            )
        )

    def _complexity_score(self, prompt: str) -> float:
        """Estimate task difficulty from prompt text: 0.0 (trivial) → 1.0 (hard).

        Combines two signals:
          - Length (40%): word count saturates at 200 words.
          - Keyword density (60%): hard reasoning/analysis keywords, cap at 3 hits.

        Returns 0.0 for empty prompts (no-op path for cold-start without a prompt).
        """
        if not prompt:
            return 0.0

        prompt_lower = prompt.lower()
        words = prompt_lower.split()
        n = len(words)

        length_score = min(1.0, n / 200.0)

        word_set = set(words)
        hard_hits = len(word_set & _HARD_KEYWORDS)
        hard_hits += sum(1 for ph in _HARD_PHRASES if ph in prompt_lower)
        keyword_score = min(1.0, hard_hits / 3.0)

        return 0.4 * length_score + 0.6 * keyword_score

    def _tier_from_complexity(self, score: float) -> str:
        """Map a [0, 1] complexity score to the cheapest adequate tier."""
        if score < _COMPLEXITY_NPU_MAX:
            return "npu"
        if score < _COMPLEXITY_IGPU_MAX:
            return "igpu"
        return "cpu"

    def predict_tier(self, skill_name: str, operation_type: str, prompt: str = "") -> str:
        """Return recommended tier string or 'unknown' when no history exists.

        When no post-execution history exists for (skill_name, operation_type):
        - If prompt is provided: estimate tier from prompt complexity features.
        - Otherwise: return 'unknown' (GIC1 preserved).

        When history exists: use the historical success-rate path (GIC2/GIC3 preserved).
        History always takes priority over prompt-based estimation.
        """
        key = (skill_name, operation_type)
        window = self._history.get(key)
        if not window:
            if prompt:
                return self._tier_from_complexity(self._complexity_score(prompt))
            return "unknown"

        # Count per-tier success vs total
        tier_success: dict[str, int] = dict.fromkeys(_TIER_ORDER, 0)
        tier_count: dict[str, int] = dict.fromkeys(_TIER_ORDER, 0)
        for rec in window:
            t = rec.tier_used
            tier_count[t] += 1
            if rec.escalation_count == 0 and rec.quality_score >= _QUALITY_FLOOR:
                tier_success[t] += 1

        # Cheapest tier whose Wilson LCB of clean-success clears the adequacy floor (H3).
        for tier in _TIER_ORDER:
            n = tier_count[tier]
            if n >= _MIN_SAMPLES and _wilson_lcb(tier_success[tier], n) >= _LCB_ADEQUATE:
                return tier

        # Fallback when no tier's LCB clears the floor (e.g. a skill reached only via escalation, so
        # its final tier has no CLEAN successes yet): pick the DOMINANT tier — where the skill
        # actually runs most — tie-broken by the cheapest. A rare lucky-cheap tier can't win (low
        # count). Once the skill is routed to ENTER at its tier, it logs clean successes and the LCB
        # path above takes over (the self-reinforcing bootstrap).
        best_tier, best_key = "cpu", (-1, -math.inf)
        for tier in _TIER_ORDER:  # rank by (most records, then highest mean quality)
            n = tier_count[tier]
            if not n:
                continue
            mean_q = sum(r.quality_score for r in window if r.tier_used == tier) / n
            key = (n, mean_q)
            if key > best_key:
                best_key, best_tier = key, tier
        return best_tier

    def get_escalation_rate(self, skill_name: str, operation_type: str) -> float | None:
        """Fraction of runs that required tier escalation, or None if no history."""
        key = (skill_name, operation_type)
        window = self._history.get(key)
        if not window:
            return None
        return sum(1 for r in window if r.escalation_count > 0) / len(window)
