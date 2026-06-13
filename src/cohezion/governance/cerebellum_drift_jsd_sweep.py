"""Cerebellum drift detection — routing coherence across task classes.

The cerebellum analogy: the biological cerebellum corrects motor drift by comparing
intended vs actual movement. Here we compare intended task routing (the model's
predicted class) vs the full class probability distribution over time.

Original implementation checked only the strongest class. Backlog item 126 extends
this to sweep ALL task classes so multi-class drift is caught (e.g. a model drifting
from 'classify' to 'reason' while 'code' quietly degrades).

Drift score: Jensen-Shannon divergence between the current distribution
and a reference baseline. JSD ∈ [0, 1]; JSD > 0.15 = alert threshold.
"""

from __future__ import annotations

import math
import logging
from dataclasses import dataclass, field


logger = logging.getLogger(__name__)

# Task classes matching task_classifier._TYPE_CONFIG keys
TASK_CLASSES = [
    "classify",
    "route",
    "summarize",
    "reason",
    "code",
    "essay",
    "true_false",
    "factual",
]

_JSD_ALERT_THRESHOLD = 0.15
_MIN_SAMPLES = 10


@dataclass
class DriftResult:
    """Result of a cerebellum drift check for one task class.

    Attributes:
        task_class: The class being evaluated.
        jsd: Jensen-Shannon divergence from baseline (0.0–1.0).
        baseline_prob: Reference probability for this class.
        current_prob: Observed probability in the current window.
        alert: True if JSD exceeds the alert threshold.
        sample_count: Number of samples in the current window.
    """

    task_class: str
    jsd: float
    baseline_prob: float
    current_prob: float
    alert: bool
    sample_count: int


@dataclass
class SweepResult:
    """Result of a full multi-class cerebellum drift sweep."""

    results: list[DriftResult]
    alerts: list[DriftResult] = field(default_factory=list)
    max_jsd: float = 0.0
    swept_classes: int = 0

    def __post_init__(self) -> None:
        self.alerts = [r for r in self.results if r.alert]
        self.max_jsd = max((r.jsd for r in self.results), default=0.0)
        self.swept_classes = len(self.results)


def _jsd(p: float, q: float) -> float:
    """Binary Jensen-Shannon divergence between two Bernoulli distributions."""
    if p <= 0 or p >= 1 or q <= 0 or q >= 1:
        return float(abs(p - q))
    m = (p + q) / 2.0

    def kl(a: float, b: float) -> float:
        if a <= 0 or b <= 0:
            return 0.0
        return a * math.log(a / b) + (1 - a) * math.log((1 - a) / (1 - b))

    return 0.5 * kl(p, m) + 0.5 * kl(q, m)


def cerebellum_drift_single(
    task_class: str,
    baseline_counts: dict[str, int],
    current_counts: dict[str, int],
) -> DriftResult:
    """Compute drift for a single task class.

    Args:
        task_class: Class name to evaluate (one of TASK_CLASSES).
        baseline_counts: Historical counts per class {class: count}.
        current_counts: Recent window counts per class {class: count}.

    Returns:
        DriftResult with JSD and alert flag.
    """
    baseline_total = max(sum(baseline_counts.values()), 1)
    current_total = max(sum(current_counts.values()), 1)

    baseline_p = baseline_counts.get(task_class, 0) / baseline_total
    current_p = current_counts.get(task_class, 0) / current_total

    # Clip to avoid log(0) in JSD
    baseline_p = max(1e-9, min(1.0 - 1e-9, baseline_p))
    current_p = max(1e-9, min(1.0 - 1e-9, current_p))

    jsd = _jsd(baseline_p, current_p)
    return DriftResult(
        task_class=task_class,
        jsd=jsd,
        baseline_prob=baseline_p,
        current_prob=current_p,
        alert=jsd > _JSD_ALERT_THRESHOLD,
        sample_count=current_total,
    )


def cerebellum_drift_sweep(
    baseline_counts: dict[str, int],
    current_counts: dict[str, int],
    classes: list[str] | None = None,
) -> SweepResult:
    """Sweep ALL task classes for drift (backlog item 126).

    Unlike `cerebellum_drift_single`, this checks every class in the taxonomy
    so multi-class degradation patterns are visible even when no single class
    dominates the drift signal.

    Args:
        baseline_counts: Historical class distribution {class: count}.
        current_counts: Current window class distribution {class: count}.
        classes: Class list to sweep. Defaults to TASK_CLASSES.

    Returns:
        SweepResult with per-class DriftResult list and summary fields.
    """
    classes = classes or TASK_CLASSES
    current_total = sum(current_counts.values())
    if current_total < _MIN_SAMPLES:
        logger.warning(
            "cerebellum_drift_sweep: only %d samples, need %d for reliable drift",
            current_total,
            _MIN_SAMPLES,
        )

    results = [cerebellum_drift_single(cls, baseline_counts, current_counts) for cls in classes]
    return SweepResult(results=results)


def drift_report(sweep: SweepResult) -> str:
    """Human-readable drift report for a sweep result."""
    lines = [
        f"Cerebellum Drift Sweep — {sweep.swept_classes} classes",
        f"Max JSD: {sweep.max_jsd:.4f}  Alerts: {len(sweep.alerts)}",
        "",
        f"{'Class':<20} {'Baseline':>9} {'Current':>9} {'JSD':>8} {'Alert':>6}",
        "-" * 60,
    ]
    for r in sweep.results:
        flag = "⚠" if r.alert else ""
        lines.append(
            f"{r.task_class:<20} {r.baseline_prob:>9.3%} {r.current_prob:>9.3%}"
            f" {r.jsd:>8.4f} {flag:>6}"
        )
    if sweep.alerts:
        lines += ["", "ALERTS:", *[f"  • {r.task_class} (JSD={r.jsd:.4f})" for r in sweep.alerts]]
    return "\n".join(lines)
