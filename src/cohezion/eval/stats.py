"""Shared evaluation statistics — variance-honest scoring for coding/agent evals.

Implements the practices from OpenAI's "separating signal from noise in coding evaluations"
(work-queue d7f5e0e4808d), as reusable utilities so any eval site reports a DISTRIBUTION with
uncertainty instead of a single ``temp=0`` point estimate:

  - ``pass_at_k`` — the unbiased pass@k estimator (Chen et al. 2021, HumanEval/Codex).
  - ``bootstrap_ci`` / ``mean_ci`` — bootstrap 95% CI over N trials + a small-n caveat, so a
    reported score carries its uncertainty (a 0.60 over 3 noisy runs is not a 0.60 over 100).
  - ``contamination_probe`` — a cheap leak check: can the model reproduce a reference solution
    from a minimal cue? High similarity ⇒ the "score" may be memorization, not capability.

Numpy + stdlib only (no new deps). Complements ``metacognitive-calibration`` (proper scoring,
no substring matching) and the existing per-site bootstrap in ``eval/universe_evaluator.py``.
"""

from __future__ import annotations

import difflib
from dataclasses import dataclass
from math import comb

import numpy as np


# Below this many trials a CI is too wide to trust — callers should flag it, not hide it.
MIN_TRUSTWORTHY_TRIALS = 5


def pass_at_k(n_samples: int, n_correct: int, k: int) -> float:
    """Unbiased pass@k estimator (Chen et al. 2021): the probability that at least one of k
    samples drawn (without replacement) from ``n_samples`` is correct, given ``n_correct``
    were correct. Avoids the optimistic bias of ``1 - (1 - c/n)**k``.
    """
    if not (0 <= n_correct <= n_samples) or k < 1 or n_samples < 1:
        raise ValueError(f"invalid pass@k inputs: n={n_samples} c={n_correct} k={k}")
    if n_samples - n_correct < k:  # fewer than k failures → some correct sample is always drawn
        return 1.0
    return 1.0 - comb(n_samples - n_correct, k) / comb(n_samples, k)


def bootstrap_ci(
    values: list[float],
    *,
    n_bootstrap: int = 1000,
    ci_level: float = 0.95,
    seed: int = 42,
) -> tuple[float, float]:
    """Bootstrap (low, high) confidence bounds for the mean of ``values``. Matches the
    convention in ``eval/universe_evaluator.py``; returns (mean, mean) when n < 2 (no spread)."""
    if len(values) < 2:
        m = float(values[0]) if values else 0.0
        return (m, m)
    rng = np.random.default_rng(seed)
    arr = np.asarray(values, dtype=float)
    boot_means = [
        float(np.mean(rng.choice(arr, size=len(arr), replace=True))) for _ in range(n_bootstrap)
    ]
    alpha = (1 - ci_level) / 2
    return (
        float(np.percentile(boot_means, alpha * 100)),
        float(np.percentile(boot_means, (1 - alpha) * 100)),
    )


@dataclass
class MeanCI:
    """A variance-honest score: point estimate + bootstrap CI + a small-n caveat."""

    mean: float
    ci_low: float
    ci_high: float
    n: int
    small_n_warning: bool  # True when n < MIN_TRUSTWORTHY_TRIALS — CI too wide to trust


def mean_ci(values: list[float], *, ci_level: float = 0.95, seed: int = 42) -> MeanCI:
    """Report a metric over N trials as mean + 95% bootstrap CI, flagging small n.

    Use this instead of a single temp=0 shot: ``mean_ci([r.score for r in trials])`` so the
    reported number carries its uncertainty and small-n results are marked, not trusted blindly.
    """
    n = len(values)
    m = float(np.mean(values)) if values else 0.0
    low, high = bootstrap_ci(values, ci_level=ci_level, seed=seed)
    return MeanCI(mean=m, ci_low=low, ci_high=high, n=n, small_n_warning=n < MIN_TRUSTWORTHY_TRIALS)


@dataclass
class ContaminationResult:
    leaked: bool
    similarity: float  # 0..1 max similarity of any probe output to the reference
    threshold: float


def contamination_probe(
    model_fn,
    reference_solution: str,
    *,
    prompts: list[str] | None = None,
    threshold: float = 0.6,
) -> ContaminationResult:
    """Cheap leak check: does the model reproduce ``reference_solution`` from a MINIMAL cue?

    ``model_fn(prompt) -> str`` is injected (testable without a live model). Each minimal prompt
    is sent; the max normalized similarity (difflib ratio) of any output to the reference is the
    leak signal. ``leaked=True`` (similarity >= threshold) means a high score on this task may be
    memorization/contamination rather than capability — screen it before trusting the score.
    """
    probes = prompts or [
        "Provide the reference/canonical solution.",
        "Complete the known answer:",
    ]
    best = 0.0
    ref = reference_solution.strip()
    for p in probes:
        try:
            out = (model_fn(p) or "").strip()
        except Exception:  # noqa: S112 — a failed probe call is a non-signal; skip it, don't crash the probe
            continue
        best = max(best, difflib.SequenceMatcher(None, out, ref).ratio())
    return ContaminationResult(leaked=best >= threshold, similarity=best, threshold=threshold)
