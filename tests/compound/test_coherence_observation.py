"""E1-S2: the executor's composite coherence must reach the detector's trend analysis.

`InflectionDetector.detect_anomaly` only inspects coherence supplied UPSTREAM by an execute_fn
(``if "coherence" in result.metrics``). The executor computes a *composite* coherence at Step 5.8
(derived partly from the anomaly score, so it cannot precede detect_anomaly) and it never reached
trend analysis — a dead tripwire on the normal local-inference path.

Fix: a dedicated ``observe_coherence`` port on the detector, fed the composite coherence after
Step 5.8, with its OWN history (separate from detect_anomaly's execute_fn-coherence history so the
two sources never cross-contaminate). These tests are discriminating: a no-op impl fails the drop
case, an always-flag impl fails the stable case, and the wiring test fails if execute_task never
calls the port.
"""

from unittest.mock import MagicMock, patch

import pytest

from cohezion.compound.executor import CompoundExecutor
from cohezion.compound.inflection_detector import InflectionDetector


@pytest.fixture
def detector():
    return InflectionDetector(coherence_threshold=0.3)


def test_observe_coherence_stable_returns_no_issues(detector):
    """Healthy, stable coherence produces no issues."""
    issues = []
    for _ in range(5):
        issues = detector.observe_coherence(0.8)
    assert issues == []


def test_observe_coherence_low_value_flags(detector):
    """A value below the threshold is flagged as low."""
    issues = detector.observe_coherence(0.1)
    assert any("low" in i.lower() for i in issues)


def test_observe_coherence_detects_downward_trend(detector):
    """A >20% drop vs the recent average is flagged (needs >=4 history)."""
    for v in (0.9, 0.9, 0.9):
        assert detector.observe_coherence(v) == []
    issues = detector.observe_coherence(0.5)  # 0.5 < 0.9*0.8 = 0.72
    assert any("trend" in i.lower() for i in issues)


def test_observe_coherence_uses_separate_history(detector):
    """Composite-coherence history is distinct from detect_anomaly's coherence_history."""
    detector.observe_coherence(0.7)
    assert detector._composite_coherence_history == [0.7]
    assert detector.coherence_history == []  # detect_anomaly's history untouched


def test_reset_state_clears_composite_history(detector):
    """reset_state clears the new composite history too."""
    detector.observe_coherence(0.7)
    detector.reset_state()
    assert detector._composite_coherence_history == []


@pytest.fixture
def executor():
    with patch("cohezion.compound.exp_persistence.vault.VaultLogger"):
        return CompoundExecutor(MagicMock())


def test_execute_task_feeds_composite_coherence_to_detector(executor):
    """WIRING: execute_task records the computed composite coherence via observe_coherence."""
    with (
        patch.object(
            executor.logger, "get_experience_guidance", return_value={"context": "test"}
        ),
        patch.object(executor.logger, "log_execution_start", return_value="exp_path"),
        patch.object(executor.logger, "log_execution_result"),
        patch.object(executor.logger, "extract_execution_pattern", return_value="pattern_path"),
    ):
        result = executor.execute_task(
            task_description="t",
            skill_name="s",
            operation_type="generate",
            execute_fn=lambda _guidance: ("real output", {}),
        )
    hist = executor.inflection_detector._composite_coherence_history
    assert len(hist) == 1
    assert hist[0] == pytest.approx(result.metrics["coherence"])
