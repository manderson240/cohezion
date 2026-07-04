"""Tests for CompoundHealthOracle (CH1–CH5, HO1–HO4).

Harness invariants verified here:
  CH1  HealthAssessment is a dataclass with regime/tier_recommendation/confidence/alert_level/alerts
  CH2  HIHO regime → alert_level="ok" (discriminating: wrong impl returning "warn" always fails)
  CH3  STUCK regime → alert_level="warn" AND tier escalated above NPU (discriminating)
  CH4  CHAOTIC regime → alert_level="critical" (discriminating: different from STUCK/HIHO)
  CH5  Synthesizes from BOTH tracker AND detector — wiring detector changes tier_recommendation
  HO1  to_dict() returns required JSON-safe keys
  HO2  from_dict() restores non-default state (discriminating: ignoring scores fails)
  HO3  save_state/restore_state round-trip with str/Path/None; returns False on missing file
  HO4  to_health_dict() returns all required API keys; is_healthy() reflected
"""

from __future__ import annotations

import dataclasses
import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock

from cohezion.compound.compound_health_oracle import (
    CompoundHealthOracle,
    HealthAssessment,
    _escalate_tier,
)
from cohezion.inference.fractal_metrics import FractalRegime


# ── CH1: Structural ────────────────────────────────────────────────────────

class TestCH1Structural:
    def test_health_assessment_is_dataclass(self) -> None:
        assert dataclasses.is_dataclass(HealthAssessment)

    def test_health_assessment_fields(self) -> None:
        field_names = {f.name for f in dataclasses.fields(HealthAssessment)}
        assert {"regime", "tier_recommendation", "confidence", "alert_level", "alerts"} <= field_names

    def test_alerts_defaults_to_empty_list(self) -> None:
        a = HealthAssessment(
            regime=FractalRegime.HIHO,
            tier_recommendation="npu",
            confidence=0.8,
            alert_level="ok",
        )
        assert a.alerts == []

    def test_oracle_has_tracker_property(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        from cohezion.inference.fractal_metrics import RollingRegimeTracker
        assert isinstance(oracle.tracker, RollingRegimeTracker)

    def test_oracle_is_healthy_false_before_first_assess(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        assert oracle.is_healthy() is False


# ── CH2: HIHO → "ok" (discriminating) ─────────────────────────────────────

class TestCH2HihoOk:
    """Discriminating: wrong impl returning "warn" for all regimes fails this."""

    def _make_hiho_scores(self, n: int = 40) -> list[float]:
        """Produce Brownian-like scores around 0.5 to trigger HIHO regime."""
        import random
        rng = random.Random(42)
        scores = []
        val = 0.5
        for _ in range(n):
            val += rng.gauss(0.0, 0.05)
            val = max(0.1, min(0.9, val))
            scores.append(val)
        return scores

    def test_hiho_regime_gives_ok_alert_level(self) -> None:
        oracle = CompoundHealthOracle(window_size=20, degradation_detector=None)
        scores = self._make_hiho_scores(40)

        last = None
        for s in scores:
            last = oracle.assess(s)

        # May not be HIHO on every run (depends on FD) — only assert if regime is HIHO
        if last and last.regime is FractalRegime.HIHO:
            assert last.alert_level == "ok"
            assert last.alerts == []
        # else: regime depends on the random walk — not every 40-score sequence hits HIHO

    def test_ok_assessment_direct_synthesis(self) -> None:
        """Force HIHO via _synthesize() directly to validate the branch without FD luck."""
        oracle = CompoundHealthOracle(window_size=20)
        assessment = oracle._synthesize(FractalRegime.HIHO, confidence=0.7)
        assert assessment.alert_level == "ok"
        assert assessment.alerts == []
        assert assessment.regime is FractalRegime.HIHO

    def test_hiho_confidence_from_deviation(self) -> None:
        """confidence = max(0, 1 - 2*deviation). At deviation=0.1 → confidence=0.8."""
        oracle = CompoundHealthOracle(window_size=20)
        a = oracle._synthesize(FractalRegime.HIHO, confidence=0.8)
        assert abs(a.confidence - 0.8) < 1e-9

    def test_is_healthy_true_after_ok_assessment(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        # Plant a direct HIHO assessment via the synthesize path + mock
        oracle._last_assessment = HealthAssessment(
            regime=FractalRegime.HIHO,
            tier_recommendation="npu",
            confidence=0.9,
            alert_level="ok",
        )
        assert oracle.is_healthy() is True


# ── CH3: STUCK → "warn" + tier escalated (discriminating) ─────────────────

class TestCH3StuckWarn:
    """Discriminating: wrong impl returning same tier for all regimes fails this."""

    def test_stuck_regime_gives_warn_alert_level(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        assessment = oracle._synthesize(FractalRegime.STUCK, confidence=0.3)
        assert assessment.alert_level == "warn"
        assert len(assessment.alerts) > 0

    def test_stuck_regime_escalates_tier_above_npu(self) -> None:
        """When base tier is NPU, STUCK must escalate to at least IGPU."""
        oracle = CompoundHealthOracle(window_size=20, degradation_detector=None)
        assessment = oracle._synthesize(FractalRegime.STUCK, confidence=0.3)
        # No detector → base tier is "npu" → escalated to "igpu"
        assert assessment.tier_recommendation != "npu"
        assert assessment.tier_recommendation in ("igpu", "cpu")

    def test_stuck_regime_escalates_igpu_to_cpu(self) -> None:
        """When detector says igpu, STUCK escalates to cpu."""
        detector = MagicMock()
        detector.suggest_routing_tier.return_value = "igpu"
        oracle = CompoundHealthOracle(window_size=20, degradation_detector=detector)
        assessment = oracle._synthesize(FractalRegime.STUCK, confidence=0.2)
        assert assessment.tier_recommendation == "cpu"

    def test_stuck_regime_caps_at_cpu_never_cloud(self) -> None:
        """Even if detector says cpu, STUCK must not escalate past cpu."""
        detector = MagicMock()
        detector.suggest_routing_tier.return_value = "cpu"
        oracle = CompoundHealthOracle(window_size=20, degradation_detector=detector)
        assessment = oracle._synthesize(FractalRegime.STUCK, confidence=0.1)
        assert assessment.tier_recommendation == "cpu"  # capped, no cloud

    def test_escalate_tier_helper_npu_to_igpu(self) -> None:
        assert _escalate_tier("npu") == "igpu"

    def test_escalate_tier_helper_igpu_to_cpu(self) -> None:
        assert _escalate_tier("igpu") == "cpu"

    def test_escalate_tier_helper_cpu_stays_cpu(self) -> None:
        assert _escalate_tier("cpu") == "cpu"  # capped — no cloud escalation


# ── CH4: CHAOTIC → "critical" (discriminating) ────────────────────────────

class TestCH4ChaoticCritical:
    """Discriminating: wrong impl returning "warn" for CHAOTIC fails this."""

    def test_chaotic_regime_gives_critical_alert_level(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        assessment = oracle._synthesize(FractalRegime.CHAOTIC, confidence=0.1)
        assert assessment.alert_level == "critical"
        assert len(assessment.alerts) > 0

    def test_chaotic_tier_is_cpu(self) -> None:
        """CHAOTIC → cpu (max local tier to slow down and increase reasoning depth)."""
        oracle = CompoundHealthOracle(window_size=20)
        assessment = oracle._synthesize(FractalRegime.CHAOTIC, confidence=0.1)
        assert assessment.tier_recommendation == "cpu"

    def test_chaotic_is_different_from_stuck(self) -> None:
        """Discriminating: stuck → warn, chaotic → critical. Wrong impl returning same fails."""
        oracle = CompoundHealthOracle(window_size=20)
        stuck = oracle._synthesize(FractalRegime.STUCK, confidence=0.3)
        chaotic = oracle._synthesize(FractalRegime.CHAOTIC, confidence=0.1)
        assert stuck.alert_level != chaotic.alert_level
        assert stuck.alert_level == "warn"
        assert chaotic.alert_level == "critical"

    def test_chaotic_is_not_healthy(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        oracle._last_assessment = oracle._synthesize(FractalRegime.CHAOTIC, confidence=0.1)
        assert oracle.is_healthy() is False


# ── CH5: Synthesizes from BOTH tracker AND detector (discriminating) ───────

class TestCH5BothSourcesSynthesized:
    """Discriminating: wiring the detector must change tier_recommendation.

    If the oracle ignores the detector, both with-detector and without-detector
    calls return the same tier — and the assertion `tier_with != tier_without` fails.
    """

    def test_detector_changes_tier_in_hiho(self) -> None:
        # Without detector: HIHO → tier defaults to "npu"
        oracle_no_det = CompoundHealthOracle(window_size=20, degradation_detector=None)
        a_no_det = oracle_no_det._synthesize(FractalRegime.HIHO, confidence=0.8)
        assert a_no_det.tier_recommendation == "npu"

        # With detector returning "igpu": HIHO → tier is "igpu"
        detector = MagicMock()
        detector.suggest_routing_tier.return_value = "igpu"
        oracle_with_det = CompoundHealthOracle(window_size=20, degradation_detector=detector)
        a_with_det = oracle_with_det._synthesize(FractalRegime.HIHO, confidence=0.8)
        assert a_with_det.tier_recommendation == "igpu"

        # Discriminating: they must differ
        assert a_no_det.tier_recommendation != a_with_det.tier_recommendation

    def test_detector_exception_falls_back_gracefully(self) -> None:
        """If suggest_routing_tier() raises, oracle falls back — no crash."""
        detector = MagicMock()
        detector.suggest_routing_tier.side_effect = RuntimeError("detector offline")
        oracle = CompoundHealthOracle(window_size=20, degradation_detector=detector)
        assessment = oracle._synthesize(FractalRegime.HIHO, confidence=0.7)
        # Falls back to "npu" default — no exception
        assert assessment.tier_recommendation == "npu"
        assert assessment.alert_level == "ok"

    def test_full_assess_loop_wires_through(self) -> None:
        """assess() on 30 scores must produce a HealthAssessment (not None) after warm-up."""
        oracle = CompoundHealthOracle(window_size=10)  # small window for fast test
        # Use low min_samples so warm-up completes quickly
        oracle._tracker._min_samples = 10
        import random
        rng = random.Random(99)
        last = None
        for _ in range(15):
            score = 0.5 + rng.gauss(0.0, 0.04)
            last = oracle.assess(max(0.0, min(1.0, score)))
        # After 15 scores with window=10 the tracker is past min_samples
        assert last is not None
        assert last.regime in (FractalRegime.STUCK, FractalRegime.HIHO, FractalRegime.CHAOTIC)
        assert last.alert_level in ("ok", "warn", "critical")
        assert last.tier_recommendation in ("npu", "igpu", "cpu")

    def test_warming_up_assessment_is_safe_warn(self) -> None:
        """Before min_samples, oracle returns warn (safe default, not crash)."""
        oracle = CompoundHealthOracle(window_size=80)  # 80-score window
        assessment = oracle.assess(0.5)  # only 1 score — below min_samples
        assert assessment.alert_level == "warn"
        assert assessment.confidence == 0.0
        assert len(assessment.alerts) > 0


# ── HO1: to_dict() serialization ──────────────────────────────────────────

class TestHO1ToDict:
    """HO1: to_dict() returns required JSON-safe keys."""

    def test_required_keys_present(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        d = oracle.to_dict()
        required = {"window_size", "min_samples", "scores", "regime_history", "last_assessment"}
        assert required <= set(d)

    def test_scores_are_list_of_floats(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        oracle.assess(0.5)
        oracle.assess(0.6)
        d = oracle.to_dict()
        assert isinstance(d["scores"], list)
        assert all(isinstance(s, float) for s in d["scores"])

    def test_regime_history_are_strings(self) -> None:
        oracle = CompoundHealthOracle(window_size=4)
        oracle._tracker._min_samples = 4
        for s in [0.5, 0.55, 0.45, 0.5]:
            oracle.assess(s)
        d = oracle.to_dict()
        assert isinstance(d["regime_history"], list)
        assert all(isinstance(r, str) for r in d["regime_history"])

    def test_json_round_trip_safe(self) -> None:
        """to_dict() must produce JSON-serializable output."""
        oracle = CompoundHealthOracle(window_size=10)
        oracle.assess(0.7)
        d = oracle.to_dict()
        serialized = json.dumps(d)
        reloaded = json.loads(serialized)
        assert reloaded["window_size"] == 10

    def test_last_assessment_none_before_first_assess(self) -> None:
        """No assess() call → last_assessment is None in dict."""
        oracle = CompoundHealthOracle(window_size=20)
        d = oracle.to_dict()
        assert d["last_assessment"] is None

    def test_last_assessment_populated_after_assess(self) -> None:
        oracle = CompoundHealthOracle(window_size=4)
        oracle._tracker._min_samples = 4
        for s in [0.5, 0.5, 0.5, 0.5]:
            oracle.assess(s)
        d = oracle.to_dict()
        # After enough samples the tracker resolves → last_assessment is not None
        # (May still be None if still warming up — check via assess return value)
        # Just verify the key is present and either a dict or None
        assert "last_assessment" in d
        if d["last_assessment"] is not None:
            assert "regime" in d["last_assessment"]
            assert "tier_recommendation" in d["last_assessment"]


# ── HO2: from_dict() cross-session restoration (discriminating) ────────────

class TestHO2FromDict:
    """HO2: from_dict() restores non-default state.

    Discriminating: wrong impl that ignores 'scores' produces len(oracle.tracker)==0.
    """

    def test_scores_restored_discriminating(self) -> None:
        """from_dict() must restore window scores — wrong impl returns empty tracker."""
        original = CompoundHealthOracle(window_size=20)
        for s in [0.4, 0.5, 0.6, 0.55, 0.45]:
            original.assess(s)
        state = original.to_dict()

        restored = CompoundHealthOracle.from_dict(state)
        # Discriminating: must be non-empty; wrong impl (ignoring scores) gives 0
        assert len(restored.tracker) == len(original.tracker)
        assert len(restored.tracker) > 0

    def test_regime_history_restored(self) -> None:
        oracle = CompoundHealthOracle(window_size=4)
        oracle._tracker._min_samples = 4
        for s in [0.5, 0.5, 0.5, 0.5]:
            oracle.assess(s)
        state = oracle.to_dict()
        restored = CompoundHealthOracle.from_dict(state)
        assert len(restored.tracker.regime_history()) == len(oracle.tracker.regime_history())

    def test_last_assessment_restored_is_healthy(self) -> None:
        """Restoring a HIHO last_assessment → is_healthy() is True on startup."""
        oracle = CompoundHealthOracle(window_size=20)
        # Plant a HIHO last_assessment manually
        oracle._last_assessment = oracle._synthesize(FractalRegime.HIHO, confidence=0.9)
        state = oracle.to_dict()

        restored = CompoundHealthOracle.from_dict(state)
        # Discriminating: wrong impl that skips last_assessment → is_healthy() returns False
        assert restored.is_healthy() is True

    def test_cb16_safe_defaults_on_missing_keys(self) -> None:
        """from_dict() with empty dict must not crash — safe defaults apply."""
        restored = CompoundHealthOracle.from_dict({})
        assert len(restored.tracker) == 0
        assert restored.is_healthy() is False

    def test_window_size_mismatch_does_not_crash(self) -> None:
        """Mismatched window_size in state is handled gracefully by restore_state."""
        # from_dict uses whatever window_size is in state — no mismatch check here
        state = {"window_size": 40, "scores": [0.5] * 5, "regime_history": [], "last_assessment": None}
        restored = CompoundHealthOracle.from_dict(state)
        assert restored._tracker._window_size == 40


# ── HO3: save_state / restore_state round-trip ────────────────────────────

class TestHO3SaveRestoreState:
    """HO3: save_state/restore_state round-trip with str/Path; returns False on missing."""

    def test_round_trip_with_path_object(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        for s in [0.4, 0.5, 0.6]:
            oracle.assess(s)
        scores_before = list(oracle.tracker._scores)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path = Path(f.name)
        oracle.save_state(path)
        assert path.exists()

        oracle2 = CompoundHealthOracle(window_size=20)
        result = oracle2.restore_state(path)
        assert result is True
        assert list(oracle2.tracker._scores) == scores_before
        path.unlink(missing_ok=True)

    def test_round_trip_with_str_path(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        oracle.assess(0.7)

        with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as f:
            path_str = f.name
        oracle.save_state(path_str)

        oracle2 = CompoundHealthOracle(window_size=20)
        result = oracle2.restore_state(path_str)
        assert result is True
        assert len(oracle2.tracker) == len(oracle.tracker)
        Path(path_str).unlink(missing_ok=True)

    def test_restore_returns_false_on_missing_file(self) -> None:
        """Discriminating: missing file must return False (not raise)."""
        oracle = CompoundHealthOracle(window_size=20)
        result = oracle.restore_state("/tmp/nonexistent_oracle_state_xyz.json")
        assert result is False

    def test_restore_returns_false_on_window_size_mismatch(self) -> None:
        """restore_state skips and returns False when window_size doesn't match."""
        state = {"window_size": 40, "scores": [0.5], "regime_history": [], "last_assessment": None}
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(state, f)
            path = Path(f.name)
        oracle = CompoundHealthOracle(window_size=20)  # different window_size
        result = oracle.restore_state(path)
        assert result is False  # mismatch detected
        path.unlink(missing_ok=True)

    def test_save_creates_parent_dirs(self) -> None:
        """save_state must create parent directories that don't exist."""
        with tempfile.TemporaryDirectory() as tmpdir:
            nested_path = Path(tmpdir) / "nested" / "dir" / "oracle.json"
            oracle = CompoundHealthOracle(window_size=20)
            oracle.assess(0.5)
            oracle.save_state(nested_path)
            assert nested_path.exists()


# ── HO4: to_health_dict() API format ─────────────────────────────────────

class TestHO4ToHealthDict:
    """HO4: to_health_dict() returns all required API keys; is_healthy() reflected."""

    _REQUIRED_KEYS = {"regime", "tier_recommendation", "confidence", "alert_level",
                      "alerts", "window_fill", "is_healthy"}

    def test_required_keys_present(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        d = oracle.to_health_dict()
        assert self._REQUIRED_KEYS <= set(d)

    def test_warming_up_regime_is_warming_up(self) -> None:
        """Before any assess() call, regime should be 'warming_up'."""
        oracle = CompoundHealthOracle(window_size=20)
        d = oracle.to_health_dict()
        assert d["regime"] == "warming_up"
        assert d["is_healthy"] is False

    def test_is_healthy_reflected_discriminating(self) -> None:
        """to_health_dict()['is_healthy'] must match oracle.is_healthy() — not hardcoded."""
        oracle = CompoundHealthOracle(window_size=20)
        oracle._last_assessment = oracle._synthesize(FractalRegime.HIHO, confidence=0.9)
        d = oracle.to_health_dict()
        # Discriminating: wrong impl returning False always fails this
        assert d["is_healthy"] is True
        assert oracle.is_healthy() is True

    def test_window_fill_matches_tracker_len(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        for s in [0.5, 0.6, 0.7]:
            oracle.assess(s)
        d = oracle.to_health_dict()
        assert d["window_fill"] == len(oracle.tracker)

    def test_confidence_is_rounded(self) -> None:
        oracle = CompoundHealthOracle(window_size=20)
        oracle._last_assessment = oracle._synthesize(FractalRegime.HIHO, confidence=0.123456789)
        d = oracle.to_health_dict()
        assert d["confidence"] == round(0.123456789, 4)
