"""Test CB13: routing accuracy invariant (RE-SCOPED 2026-07-19, E1-S3).

Original CB13 compared ``DegradationDetector.suggest_routing_tier()`` — a SINGLE system-wide
tier — per-prompt against 8 heterogeneous ``task_classifier.classify().node`` decisions. Because
the detector returns one scalar tier for the whole system, agreement was capped at the fraction of
prompts matching that tier (the classifier mode is 6/8 ``npu``), structurally below the asserted
>=90%. A perpetual grace-period ``xfail`` then meant the real assertion never ran — so the invariant
was simultaneously unreachable and untested (see harness.md CB13, 2026-07-06).

Re-scope: ``suggest_routing_tier()`` is a *system-wide health* signal, so the meaningful question is
whether it agrees with the classifier's DOMINANT tendency — the MODE of the 8 outputs — not each
prompt individually. The invariant now actually runs: once baselines are established (healthy state),
health-based routing must agree with the classifier's dominant tier. Do NOT rig baselines — this
feeds ordinary healthy metrics, the same pattern the DegradationDetector suite uses.
"""

from collections import Counter

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.inference.task_classifier import classify


# 8-prompt fixture from CL1 (harness.md)
FIXTURE_PROMPTS = [
    "Classify this text: sentiment analysis task.",  # classify
    "Route this request properly.",  # route
    "Summarize this document in one sentence.",  # summarize
    "Reason step by step about this problem.",  # reasoning
    "Write code to sort a list in Python.",  # code
    "Write a short essay about climate change.",  # essay
    "Is this statement true or false?",  # true/false
    "What is the capital of France?",  # factual
]

# Healthy metrics matching the DegradationDetector suite's baseline pattern.
_HEALTHY_METRICS = {
    "combined_hit_rate": 0.75,
    "tokens_per_second": 1000.0,
    "mean_coherence": 0.85,
    "elapsed_seconds": 1.0,
    "success_rate": 1.0,
}


def _classifier_mode() -> str:
    """Dominant classifier tier over the fixture, normalized into the detector's tri-state.

    The binary classifier emits ``npu``/``gpu``; ``gpu`` maps to the detector's ``igpu`` mid-tier.
    """
    nodes: list[str] = []
    for prompt in FIXTURE_PROMPTS:
        node = classify(prompt).node
        nodes.append("igpu" if node == "gpu" else node)
    return Counter(nodes).most_common(1)[0][0]


def test_cb13_grace_period_defaults_to_igpu():
    """A fresh detector (no baselines) routes to the safe mid-tier ``igpu``."""
    assert DegradationDetector().suggest_routing_tier() == "igpu"


def test_cb13_routing_tier_matches_classifier_mode():
    """CB13 (re-scoped): once healthy baselines exist, system-wide health-based routing agrees
    with the classifier's dominant tier. This assertion RUNS (no perpetual xfail).

    Discriminating: fails if suggest_routing_tier() cannot leave grace to reach the healthy tier,
    or if it disagrees with the classifier's dominant tendency.
    """
    detector = DegradationDetector()
    for _ in range(5):  # establish baselines → exit grace period (matches CB12 pattern)
        detector.check_degradation(_HEALTHY_METRICS)

    assert detector._baselines["coherence"].is_established, "baselines should be established"
    assert detector.suggest_routing_tier() == _classifier_mode()
