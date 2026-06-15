"""CB13 invariant: DegradationDetector.suggest_routing_tier() and task_classifier.classify()
must agree on routing tier for ≥90% of the standard 8-test fixture.

Structural guard first (method existence), then behavioral agreement check.
Gracefully skips when task_classifier or suggest_routing_tier are unavailable
(branches that haven't merged those features yet pass vacuously).

Reference: harness.md CB13 — routing accuracy invariant (2026-06-14).
"""

from __future__ import annotations

import pytest

task_classifier_mod = pytest.importorskip(
    "cohezion.inference.task_classifier",
    reason="task_classifier not available in this checkout — skip CB13",
)
classify = task_classifier_mod.classify


# --- Structural guard: suggest_routing_tier must exist ---

def test_cb13_structural_suggest_routing_tier_exists():
    """suggest_routing_tier() must be a method on DegradationDetector."""
    from cohezion.compound.degradation_detector import DegradationDetector

    assert hasattr(DegradationDetector, "suggest_routing_tier"), (
        "CB13: DegradationDetector.suggest_routing_tier() must exist — "
        "closes the monitoring→routing feedback loop."
    )


def test_cb13_structural_suggest_routing_tier_is_callable():
    from cohezion.compound.degradation_detector import DegradationDetector

    d = DegradationDetector()
    if not hasattr(d, "suggest_routing_tier"):
        pytest.skip("suggest_routing_tier not yet implemented in this checkout")
    assert callable(d.suggest_routing_tier)


def test_cb13_structural_suggest_routing_tier_returns_valid_tier():
    """Grace period (no baselines) → must return 'igpu' (safe middle tier)."""
    from cohezion.compound.degradation_detector import DegradationDetector

    d = DegradationDetector()
    if not hasattr(d, "suggest_routing_tier"):
        pytest.skip("suggest_routing_tier not yet implemented in this checkout")

    result = d.suggest_routing_tier()
    assert result in {"npu", "igpu", "cpu"}, (
        f"suggest_routing_tier() returned {result!r}, expected one of 'npu'/'igpu'/'cpu'"
    )


def test_cb13_structural_suggest_routing_tier_grace_period():
    """Fresh detector (no metrics yet) → 'igpu' grace-period default."""
    from cohezion.compound.degradation_detector import DegradationDetector

    d = DegradationDetector()
    if not hasattr(d, "suggest_routing_tier"):
        pytest.skip("suggest_routing_tier not yet implemented in this checkout")

    # With composite_score=None (no data yet), must default to igpu
    result = d.suggest_routing_tier()
    assert result == "igpu", (
        f"Grace-period suggest_routing_tier() returned {result!r}, expected 'igpu'"
    )


# --- Behavioral: ≥90% agreement across the CL1 8-test fixture ---

# The canonical 8-test fixture from CL1 (classify/route/summarize/reason/code/essay/true-false/factual)
# Maps prompt → expected tier from task_classifier.classify().node
_CL1_FIXTURE = [
    ("Reply with one word only: is this positive or negative? Text: I love it.", "npu"),
    ("Route this message to the appropriate handler.", "npu"),
    ("Summarize this in one sentence: The cat sat on the mat and fell asleep.", "npu"),
    ("Reason step by step: If all mammals breathe air and dogs are mammals, do dogs breathe air?", "gpu"),
    ("Write a Python function to reverse a string.", "gpu"),
    ("Write a 3-paragraph essay on the benefits of exercise.", "gpu"),
    ("Reply with true or false only: The sky is blue.", "npu"),
    ("What is the capital of France?", "npu"),
]


@pytest.mark.parametrize("prompt,_expected_tier", _CL1_FIXTURE)
def test_cb13_task_classifier_individual(prompt: str, _expected_tier: str):
    """Each CL1 fixture prompt classifies without error."""
    decision = classify(prompt)
    # Map gpu → igpu for comparison (task_classifier uses npu/gpu, not npu/igpu/cpu)
    actual = "igpu" if decision.node == "gpu" else decision.node
    assert actual in {"npu", "igpu"}, f"Unexpected tier: {actual}"


def test_cb13_routing_accuracy_agreement():
    """DegradationDetector.suggest_routing_tier() and task_classifier must agree ≥90%.

    CB13: If the detector is in grace period (composite_score=None), the invariant is
    skipped — baselines not yet established. Once baselines are established, the
    agreement requirement kicks in.
    """
    from cohezion.compound.degradation_detector import DegradationDetector

    if not hasattr(DegradationDetector, "suggest_routing_tier"):
        pytest.skip("suggest_routing_tier not yet implemented — CB13 structural guards above capture this")

    d = DegradationDetector()
    tier = d.suggest_routing_tier()

    # Grace period: composite_score is None — invariant vacuously passes
    # (can't assess agreement when detector hasn't established baselines)
    has_composite = hasattr(d, "composite_score") or hasattr(d, "_composite_score")
    if tier == "igpu" and not has_composite:
        pytest.skip("DegradationDetector in grace period — baselines not yet established")

    agreements = 0
    for prompt, expected_task_tier in _CL1_FIXTURE:
        decision = classify(prompt)
        classifier_tier = "igpu" if decision.node == "gpu" else "npu"
        # Both agree if detector tier == classifier tier (coarse: npu or igpu/gpu)
        if tier == "igpu":
            if classifier_tier == "igpu":
                agreements += 1
        elif tier == "npu":
            if classifier_tier == "npu":
                agreements += 1
        elif tier == "cpu":
            pass  # cpu is a fallback; skip agreement for cpu tier

    total = len(_CL1_FIXTURE)
    ratio = agreements / total
    assert ratio >= 0.9, (
        f"CB13 routing accuracy {ratio:.1%} ({agreements}/{total}) below 90% threshold. "
        f"DegradationDetector tier={tier!r} diverges from task_classifier outputs."
    )
