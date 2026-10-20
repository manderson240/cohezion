"""The health-oracle tier must not freeze when quality is unmeasured.

Review 2026-09-22 (C3): ``SkillRefiner._generate_learning_signal`` returns before
``CompoundHealthOracle.assess`` whenever quality is None -- every non-code task. The assessment
restored from ``~/.cohezion/oracle_state.json`` (live: stuck/cpu, written by an older
``_synthesize``) was therefore never recomputed, and ``_resolve_tier`` (max-capability) entered
every task at cpu. Recomputing from the SAME measured window says npu/ok. Fix: ``reassess()``
re-runs only the synthesis over already-measured scores -- no stand-in score is ingested.
"""

from __future__ import annotations

import json

from cohezion.compound.compound_health_oracle import CompoundHealthOracle
from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner


def _unmeasured() -> ExecutionMetrics:
    return ExecutionMetrics(
        success=True,
        duration_seconds=1.0,
        tokens_used=10,
        token_efficiency=10.0,
        quality_score=None,
        anomaly_score=0.0,
        cached_hits=0,
    )


def _stale_state(tmp_path):
    """The live file's shape: 80 measured 1.0s, but a stuck/cpu assessment."""
    path = tmp_path / "oracle_state.json"
    path.write_text(
        json.dumps(
            {
                "window_size": 80,
                "min_samples": 80,
                "scores": [1.0] * 80,
                "regime_history": ["stuck"] * 5,
                "last_assessment": {
                    "regime": "stuck",
                    "tier_recommendation": "cpu",
                    "confidence": 0.0,
                    "alert_level": "warn",
                    "alerts": [],
                },
            }
        )
    )
    return path


def test_unmeasured_signals_recompute_a_stale_restored_tier(tmp_path):
    oracle = CompoundHealthOracle()
    assert oracle.restore_state(_stale_state(tmp_path))
    assert oracle._last_assessment.tier_recommendation == "cpu"
    refiner = SkillRefiner(health_oracle=oracle)
    for _ in range(20):
        assert refiner._generate_learning_signal("s", "op", _unmeasured()) is None
    assert oracle._last_assessment.tier_recommendation == "npu"
    assert oracle._last_assessment.alert_level == "ok"
    # nothing was ingested: the window is still exactly the 80 measured scores
    assert list(oracle.tracker._scores) == [1.0] * 80


def test_reassess_leaves_a_cold_oracle_alone():
    """Below min_samples there is no regime to re-derive; do not write a placeholder."""
    oracle = CompoundHealthOracle()
    assert oracle.reassess() is None and oracle._last_assessment is None
