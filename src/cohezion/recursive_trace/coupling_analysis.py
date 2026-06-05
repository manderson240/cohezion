"""Non-circular coupling analysis: is the resolving strategy dependent on the failure class?

Design: docs/research/FAILURE_RESOLUTION_COLLECTION_DESIGN_2026-06-05.md

The value question for recursive-trace, measured from REAL resolved `(failure_class,
strategy)` pairs (no hand-written map):

  conditional ordering (rank strategies by P(strategy | failure_class))
  vs marginal ordering (rank by global P(strategy))  -- which resolves in fewer attempts?

`Δ = E_attempts[marginal] − E_attempts[conditional]`. Δ > 0 means knowing the failure
class lets you reach the resolver sooner. Significance via a label-PERMUTATION null:
shuffle the strategy labels (destroying any failure→strategy dependence) and check that
the real Δ beats the 95th percentile of shuffled Δ. If failures are independent of what
fixes them, Δ falls inside the null and the verdict is RETIRE — honestly.
"""
from __future__ import annotations

import random
from collections import Counter, defaultdict


def _expected_attempts(pairs: list[tuple[str, str]], conditional: bool) -> float:
    """Mean attempts-to-first-success ranking strategies by frequency.

    For each (fc, rs): attempts = (#strategies scored strictly above rs) +
    (expected position of rs within its tied score-group) = before + (t+1)/2.
    Ties are averaged so neither policy is rewarded for arbitrary tie-breaks.
    """
    marginal = Counter(rs for _, rs in pairs)
    per_fc: dict[str, Counter] = defaultdict(Counter)
    for fc, rs in pairs:
        per_fc[fc][rs] += 1

    total = 0.0
    for fc, rs in pairs:
        scores = per_fc[fc] if conditional else marginal
        my = scores[rs]
        before = sum(1 for c in scores.values() if c > my)
        tied = sum(1 for c in scores.values() if c == my)  # includes rs itself
        total += before + (tied + 1) / 2.0
    return total / len(pairs)


def coupling_delta(pairs: list[tuple[str, str]]) -> float:
    """Δ = E_attempts[marginal] − E_attempts[conditional]. >0 ⇒ failure-class helps."""
    if not pairs:
        return 0.0
    return _expected_attempts(pairs, conditional=False) - _expected_attempts(
        pairs, conditional=True
    )


def permutation_pvalue(
    pairs: list[tuple[str, str]], *, n_perm: int = 2000, seed: int = 20260605
) -> tuple[float, float]:
    """Return (real_delta, p_value). p = fraction of shuffled Δ ≥ real Δ.

    The null shuffles strategy labels across pairs, breaking failure→strategy dependence
    while preserving both marginals. This also absorbs the optimism of estimating the
    conditional from the same data (the shuffled deltas overfit identically).
    """
    real = coupling_delta(pairs)
    if real <= 0 or len(pairs) < 2:
        return real, 1.0
    fcs = [fc for fc, _ in pairs]
    strategies = [rs for _, rs in pairs]
    rng = random.Random(seed)
    ge = 0
    for _ in range(n_perm):
        shuffled = strategies[:]
        rng.shuffle(shuffled)
        if coupling_delta(list(zip(fcs, shuffled))) >= real:
            ge += 1
    return real, (ge + 1) / (n_perm + 1)  # +1 = unbiased (real counts as one draw)


def analyze_domain(
    pairs: list[tuple[str, str]],
    *,
    n_min: int = 60,
    k_min: int = 3,
    alpha: float = 0.05,
    n_perm: int = 2000,
) -> dict:
    """Per-domain verdict: KEEP / RETIRE / UNPROVEN with the evidence behind it."""
    n = len(pairs)
    k = len({fc for fc, _ in pairs})
    n_strat = len({rs for _, rs in pairs})
    if n < n_min or k < k_min or n_strat < 2:
        return {
            "verdict": "UNPROVEN",
            "reason": f"below floor (n={n}<{n_min} or k={k}<{k_min} or strategies={n_strat}<2)",
            "n": n, "k": k, "n_strategies": n_strat,
        }
    delta, p = permutation_pvalue(pairs, n_perm=n_perm)
    if delta > 0 and p < alpha:
        verdict = "KEEP"
        reason = f"failure-class predicts resolver: Δ={delta:.3f} attempts saved, p={p:.4f}"
    else:
        verdict = "RETIRE"
        reason = f"strategy ⊥ failure-class: Δ={delta:.3f}, p={p:.4f} (within permutation null)"
    return {
        "verdict": verdict, "reason": reason,
        "delta": delta, "p_value": p, "n": n, "k": k, "n_strategies": n_strat,
    }
