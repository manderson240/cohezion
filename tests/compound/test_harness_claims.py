"""Tests written directly FROM harness.md invariant claims that had none.

Why this file exists
--------------------
The E5 doc-code check (harness DOC1) found 13 invariants citing tests that are defined
nowhere. Triage split them cleanly:

  * 11 where the FEATURE exists and only the test was missing -> writable, and each one
    written here removes an entry from KNOWN_PHANTOM_TESTS.
  * 2 where the claimed SYMBOL is absent too (MB1's `value_bounds`, TR1's
    `_TIER_TEMPERATURE`) -> the whole invariant is phantom and is marked REMOVED.

Each test below asserts the invariant's own stated assertion, verbatim from harness.md.
That makes the doc the spec: writing the test either verifies the claim or falsifies it,
and both are useful. Every one here VERIFIED — the features were real, only undocumented
by test.

Discipline: these are discriminating, not smoke tests. Each one fails against the most
plausible wrong implementation of the mechanism it guards, noted per test.
"""

from __future__ import annotations

from cohezion.compound.degradation_detector import DegradationDetector
from cohezion.compound.skill_refiner import ExecutionMetrics, SkillRefiner


class TestLT1EmaThresholdSensitivity:
    """LT1: learned EMA thresholds are MORE sensitive than the fixed threshold.

    harness.md: "after 10 observations of 0.90 (alpha=0.3), EMA threshold rises well
    above initial 0.50 seed -- more sensitive to drops from a high baseline".
    """

    def test_use_ema_thresholds_more_sensitive_than_fixed(self):
        fixed_threshold = 0.50
        det = DegradationDetector(coherence_threshold=fixed_threshold, use_ema_thresholds=True)

        # The dict key is "mean_coherence", not "coherence" -- check_degradation reads
        # metrics.get("mean_coherence"), and a wrong key silently yields None, which
        # skips the EMA update entirely and leaves the threshold at its seed. That is
        # exactly how this test failed on the first run; the detector was fine.
        for _ in range(10):
            det.check_degradation({"mean_coherence": 0.90})

        learned = det.get_learned_threshold("coherence")
        observed = 0.65

        # Discriminating: an implementation that never updates the EMA leaves `learned`
        # at the 0.50 seed, and 0.65 would clear BOTH thresholds -- so the test hinges
        # on the learned bar having actually moved above the observation.
        assert learned > fixed_threshold, (
            f"EMA threshold did not rise above the {fixed_threshold} seed after 10 "
            f"observations of 0.90 (got {learned:.4f}) -- the EMA is not updating."
        )
        assert observed < learned, f"{observed} should trip the LEARNED bar ({learned:.4f})"
        assert observed > fixed_threshold, (
            f"{observed} must NOT trip the FIXED bar ({fixed_threshold}) -- otherwise "
            "this proves nothing about relative sensitivity."
        )


class TestRV2FrequencyPenalty:
    """RV2: the 1/(1+wins) penalty stops one perspective monopolising selection."""

    @staticmethod
    def _metrics() -> ExecutionMetrics:
        return ExecutionMetrics(
            success=True,
            duration_seconds=1.0,
            tokens_used=50,
            token_efficiency=50.0,
            quality_score=0.5,
            anomaly_score=0.5,
            cached_hits=0,
        )

    def test_repeated_winner_gets_lower_score_on_next_call(self):
        refiner = SkillRefiner()
        metrics = self._metrics()

        winners = [
            refiner._autodata_select(refiner._autodata_candidates(metrics, "generate"), metrics)
            for _ in range(20)
        ]

        # Discriminating: WITHOUT the frequency penalty, _autodata_select is
        # deterministic over identical inputs and returns the same candidate all 20
        # times, giving len(set()) == 1. Requiring >1 is precisely the anti-monopoly
        # property; asserting only "a winner exists" would pass either way.
        assert len(set(winners)) > 1, (
            f"one perspective monopolised all 20 selections ({winners[0]!r}) -- the "
            "1/(1+wins) frequency penalty is not being applied"
        )
        assert refiner._autodata_wins, "_autodata_wins was never populated"
        assert sum(refiner._autodata_wins.values()) == 20, (
            f"win tally {sum(refiner._autodata_wins.values())} != 20 selections"
        )
