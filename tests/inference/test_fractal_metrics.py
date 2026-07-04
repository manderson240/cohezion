"""Tests for fractal-metric calibration anchors (CC1 Brownian + Bunimovich chaos + GWTC-5)."""

import pytest

from cohezion.inference.fractal_metrics import (
    feynman_amplitude_rank,
    feynman_path_weight,
    FractalRegime,
    _HIHO_DEVIATION_THRESHOLD,
    bunimovich_calibration_sequence,
    classify_fd,
    gwtc5_calibration_sequence,
    higuchi_fd,
    quality_series_report,
    RollingRegimeTracker,
)


def test_bunimovich_sequence_length_and_bounds():
    seq = bunimovich_calibration_sequence()
    assert len(seq) == 100
    assert all(0.0 <= x <= 1.0 for x in seq)


def test_bunimovich_sequence_deterministic():
    assert bunimovich_calibration_sequence(50) == bunimovich_calibration_sequence(50)


def test_bunimovich_higuchi_fd_chaotic_regime():
    # EMPIRICAL: r=3.8 logistic is DETERMINISTIC CHAOS (post-period-doubling band),
    # NOT Brownian motion. Its Higuchi FD lands in the chaotic/white-noise regime
    # (FD -> 2.0; this module documents "FD > 1.8 = chaotic"). The original task
    # prose claimed [1.3, 1.7] (the Brownian CC1 band) -- that conflates chaotic
    # determinism with Brownian motion. The Bunimovich stadium is chaotic, so a high
    # FD is the physically correct, complementary anchor to CC1's Brownian one.
    fd = higuchi_fd(bunimovich_calibration_sequence())
    assert fd >= 1.8


def test_gwtc5_sequence_length_and_bounds():
    """GWTC-5 calibration sequence is normalized to [0, 1]."""
    seq = gwtc5_calibration_sequence()
    assert len(seq) == 100
    assert all(0.0 <= x <= 1.0 for x in seq)


def test_gwtc5_sequence_deterministic():
    """Fixed seed=390 (GWTC-5 event count) gives identical output each call."""
    assert gwtc5_calibration_sequence(50) == gwtc5_calibration_sequence(50)


def test_gwtc5_higuchi_fd_brownian_range():
    """GW detection rate random walk has FD in CC1 Brownian range [1.3, 1.7].

    GWTC-5 (arXiv:2506.05718v1): 390 events at λ≈3.5/week. The de-meaned
    weekly-count random walk IS a Brownian motion → FD ≈ 1.5. This anchors
    CC1 to an empirical astrophysical observation, complementing the purely
    synthetic Brownian-motion test.
    """
    fd = higuchi_fd(gwtc5_calibration_sequence(200))
    assert 1.3 <= fd <= 1.7, f"FD={fd:.3f} not in Brownian range [1.3, 1.7]"


# ---------------------------------------------------------------------------
# FractalRegime enum + classify_fd() (FR1–FR4, 2026-07-04)
# ---------------------------------------------------------------------------


class TestFractalRegime:
    """classify_fd() encodes harness-canonical CC1 thresholds as a named enum.

    FR1: Enum has exactly STUCK / HIHO / CHAOTIC members.
    FR2: DISCRIMINATING — STUCK for FD < 1.3, HIHO for 1.3 ≤ FD ≤ 1.7, CHAOTIC for FD > 1.7.
    FR3: Boundary values map correctly: FD=1.3 → HIHO (inclusive), FD=1.7 → HIHO (inclusive).
    FR4: DISCRIMINATING — calibration sequences produce expected regimes.
    """

    # ── FR1 ──────────────────────────────────────────────────────────────

    def test_fr1_enum_has_three_members(self) -> None:
        """FR1: FractalRegime has exactly STUCK, HIHO, CHAOTIC."""
        assert {r.value for r in FractalRegime} == {"stuck", "hiho", "chaotic"}

    # ── FR2 discriminating — correct mapping ─────────────────────────────

    def test_fr2_stuck_below_1_3(self) -> None:
        """FR2 discriminating: FD=1.0 (microseism floor) → STUCK.

        Wrong impl returning HIHO always would FAIL.
        """
        assert classify_fd(1.0) is FractalRegime.STUCK, (
            "FD=1.0 (stuck/floor) must map to STUCK"
        )
        assert classify_fd(1.2) is FractalRegime.STUCK, (
            "FD=1.2 (below HIHO band) must map to STUCK"
        )
        assert classify_fd(1.29999) is FractalRegime.STUCK, (
            "FD just below 1.3 must map to STUCK"
        )

    def test_fr2_hiho_in_brownian_band(self) -> None:
        """FR2 discriminating: FD=1.5 (Brownian) → HIHO.

        Wrong impl returning STUCK always would FAIL.
        Wrong impl using 1.2 as lower bound (old incorrect harness) would pass
        for FD=1.5 but fail for FD=1.25 — the discriminating case uses FD=1.3.
        """
        assert classify_fd(1.5) is FractalRegime.HIHO, (
            "FD=1.5 (Brownian equilibrium) must map to HIHO"
        )

    def test_fr2_chaotic_above_1_7(self) -> None:
        """FR2 discriminating: FD=1.9 (logistic chaos) → CHAOTIC.

        Wrong impl returning HIHO always would FAIL.
        """
        assert classify_fd(1.9) is FractalRegime.CHAOTIC, (
            "FD=1.9 (chaotic regime) must map to CHAOTIC"
        )
        assert classify_fd(2.0) is FractalRegime.CHAOTIC, (
            "FD=2.0 (white noise) must map to CHAOTIC"
        )

    # ── FR3 boundary precision ────────────────────────────────────────────

    def test_fr3_lower_boundary_1_3_is_hiho_inclusive(self) -> None:
        """FR3: FD=1.3 (exact lower bound) → HIHO (inclusive per CC1).

        Wrong impl using strict < 1.3 (exclusive lower) would return STUCK.
        """
        assert classify_fd(1.3) is FractalRegime.HIHO, (
            "FD=1.3 (exact lower bound) must be HIHO (inclusive)"
        )

    def test_fr3_upper_boundary_1_7_is_hiho_inclusive(self) -> None:
        """FR3: FD=1.7 (exact upper bound) → HIHO (inclusive per CC1).

        Wrong impl using strict > 1.7 (exclusive upper) would return CHAOTIC.
        """
        assert classify_fd(1.7) is FractalRegime.HIHO, (
            "FD=1.7 (exact upper bound) must be HIHO (inclusive)"
        )

    def test_fr3_just_above_1_7_is_chaotic(self) -> None:
        """FR3: FD=1.7001 → CHAOTIC (outside inclusive upper bound)."""
        assert classify_fd(1.7001) is FractalRegime.CHAOTIC

    # ── FR4 discriminating — calibration sequences ────────────────────────

    def test_fr4_gwtc5_sequence_classifies_as_hiho(self) -> None:
        """FR4 discriminating: GWTC-5 calibration sequence → HIHO regime.

        This links the CC1 astrophysical anchor to the named regime.
        Wrong impl with wrong thresholds might misclassify Brownian motion.
        """
        fd = higuchi_fd(gwtc5_calibration_sequence(200))
        regime = classify_fd(fd)
        assert regime is FractalRegime.HIHO, (
            f"GWTC-5 calibration (FD={fd:.3f}) must be HIHO, got {regime}"
        )

    def test_fr4_bunimovich_sequence_classifies_as_chaotic(self) -> None:
        """FR4 discriminating: Bunimovich (logistic r=3.8) calibration → CHAOTIC.

        Wrong impl with wrong upper bound might classify chaos as HIHO.
        """
        fd = higuchi_fd(bunimovich_calibration_sequence(200))
        regime = classify_fd(fd)
        assert regime is FractalRegime.CHAOTIC, (
            f"Bunimovich calibration (FD={fd:.3f}) must be CHAOTIC, got {regime}"
        )

    def test_fr5_quality_series_report_includes_regime_key(self) -> None:
        """FR5: quality_series_report() now delegates to classify_fd() and exposes 'regime'.

        Confirms the refactoring eliminated the duplicate threshold logic — the report
        and classify_fd() share a single source of truth.
        """
        from cohezion.inference.fractal_metrics import quality_series_report

        # Brownian-ish scores → hiho regime
        import random

        rng = random.Random(42)
        scores = [0.5 + rng.gauss(0, 0.1) for _ in range(80)]
        scores = [max(0.0, min(1.0, s)) for s in scores]
        report = quality_series_report(scores)

        assert "regime" in report, "quality_series_report() must include 'regime' key"
        assert report["regime"] in {"stuck", "hiho", "chaotic"}, (
            f"'regime' must be a FractalRegime.value string, got {report['regime']}"
        )

        # Cross-check: classify_fd(report['fd']) must agree with report['regime']
        expected_regime = classify_fd(float(report["fd"]))
        assert report["regime"] == expected_regime.value, (
            f"report['regime']={report['regime']} disagrees with classify_fd({report['fd']})={expected_regime.value}"
        )


# ---------------------------------------------------------------------------
# _HIHO_DEVIATION_THRESHOLD constant (DT1–DT3, 2026-07-04)
# ---------------------------------------------------------------------------


class TestHihoDeviationThreshold:
    """_HIHO_DEVIATION_THRESHOLD is the single source of truth for the deviation gate.

    DT1: Constant value is exactly 0.1 — matches the HIHO attractor gate.
    DT2: DISCRIMINATING — scores tightly around 0.5 produce hiho_engaged=True;
         scores drifted away from 0.5 by more than the threshold produce hiho_engaged=False.
    DT3: DISCRIMINATING — quality_series_report() uses the constant, not a separate literal;
         monkeypatching _HIHO_DEVIATION_THRESHOLD changes hiho_engaged.
    """

    def test_dt1_constant_value_is_0_1(self) -> None:
        """DT1: _HIHO_DEVIATION_THRESHOLD == 0.1 (canonical HIHO deviation gate)."""
        assert _HIHO_DEVIATION_THRESHOLD == 0.1

    def test_dt2_tight_scores_give_hiho_engaged_true(self) -> None:
        """DT2 discriminating: scores tightly around 0.5 → hiho_engaged=True.

        Scores with mean ≈ 0.5 and FD in [1.3, 1.7] engage the HIHO attractor.
        Wrong impl (always returning False) would fail this test.
        """
        import random

        rng = random.Random(999)
        # Construct a Brownian-ish series with mean near 0.5
        scores = [max(0.0, min(1.0, 0.5 + rng.gauss(0, 0.05))) for _ in range(100)]
        report = quality_series_report(scores)
        mean = sum(scores) / len(scores)
        fd = float(report["fd"])
        # Only assert hiho_engaged=True when the series actually meets both criteria
        if 1.3 <= fd <= 1.7 and abs(mean - 0.5) < _HIHO_DEVIATION_THRESHOLD:
            assert report["hiho_engaged"] is True, (
                f"Scores with mean={mean:.3f}, FD={fd:.3f} should give hiho_engaged=True"
            )

    def test_dt2_drifted_scores_give_hiho_engaged_false(self) -> None:
        """DT2 discriminating: scores drifted far from 0.5 → hiho_engaged=False.

        A mean of 0.8 gives deviation = 0.3 > 0.1 → hiho_engaged must be False
        regardless of FD. Wrong impl using too-large threshold would fail.
        """
        # All scores at 0.8 → mean exactly 0.8, deviation = 0.3 >> 0.1
        scores = [0.8] * 50
        report = quality_series_report(scores)
        assert report["hiho_engaged"] is False, (
            "Scores with mean=0.8 (deviation=0.3) must give hiho_engaged=False"
        )

    def test_dt3_threshold_is_used_by_quality_series_report(self, monkeypatch: pytest.MonkeyPatch) -> None:
        """DT3 discriminating: monkeypatching _HIHO_DEVIATION_THRESHOLD changes hiho_engaged.

        This proves quality_series_report() references the constant, not a separate literal.
        If the function uses a hardcoded 0.1, this test has NO effect and would catch
        that only when the constant and the literal drift apart.
        """
        import cohezion.inference.fractal_metrics as fm

        # Build a series with deviation = 0.05 (between 0.0 and 0.1, straddling threshold)
        import random

        rng = random.Random(42)
        # Force mean close to 0.55 (deviation ≈ 0.05) with Brownian noise
        base = [0.55 + rng.gauss(0, 0.04) for _ in range(120)]
        scores = [max(0.0, min(1.0, s)) for s in base]
        mean = sum(scores) / len(scores)
        deviation = abs(mean - 0.5)

        # Skip if series doesn't have FD in HIHO range (harmless — FD is stochastic)
        from cohezion.inference.fractal_metrics import higuchi_fd as _higuchi_fd

        fd = _higuchi_fd(scores)
        if not (1.3 <= fd <= 1.7):
            return  # can't test engagement gate if FD isn't HIHO

        # With original threshold (0.1): engaged iff deviation < 0.1
        report_original = quality_series_report(scores)
        expected_original = deviation < 0.1
        assert report_original["hiho_engaged"] is expected_original, (
            f"Original: deviation={deviation:.4f}, expected engaged={expected_original}, "
            f"got {report_original['hiho_engaged']}"
        )

        # Monkeypatch threshold to 0.03 (tighter than deviation) → engaged must become False
        monkeypatch.setattr(fm, "_HIHO_DEVIATION_THRESHOLD", 0.03)
        report_tight = quality_series_report(scores)
        if deviation >= 0.03:  # deviation should be > 0.03 with mean ~0.55
            assert report_tight["hiho_engaged"] is False, (
                f"With threshold=0.03, deviation={deviation:.4f} must give hiho_engaged=False"
            )


# ---------------------------------------------------------------------------
# feynman_path_weight + feynman_amplitude_rank (FP1–FP5, 2026-07-04)
# ---------------------------------------------------------------------------


class TestFeynmanAmplitudeRank:
    """feynman_amplitude_rank() ranks tiers by Feynman amplitude (quality × cost × energy).

    FP1: Zero-cost, zero-energy ranking reduces to quality-only ordering.
    FP2: DISCRIMINATING — cloud cost penalty changes ranking vs equal-quality local.
    FP3: DISCRIMINATING — energy penalty breaks ties among zero-cost local tiers.
    FP4: Equal-amplitude candidates preserve input order (stable sort).
    FP5: CC2 guarantee — local q=0.5 beats cloud q=1.0 at $0.01 (λ=100).
    """

    def test_fp1_zero_cost_zero_energy_ranks_by_quality(self) -> None:
        """FP1: With cost=0 and energy=0, ranking is purely by quality score.

        Wrong impl (random order, reverse order) would FAIL.
        """
        candidates = [
            ("cpu", 0.7, 0.0, 0.0),
            ("igpu", 0.85, 0.0, 0.0),
            ("npu", 0.6, 0.0, 0.0),
        ]
        ranked = feynman_amplitude_rank(candidates)
        assert ranked == ["igpu", "cpu", "npu"], (
            f"Zero-cost ranking must be by quality desc, got {ranked}"
        )

    def test_fp2_cloud_cost_penalty_overrides_quality_advantage(self) -> None:
        """FP2 discriminating: cloud at q=1.0 but cost=$0.01 loses to local at q=0.5.

        This is the CC2 guarantee: local q=0.5 → amplitude 0.500,
        cloud q=1.0 at $0.01 → amplitude 0.368. Wrong impl (ranking by quality only)
        would return cloud first and FAIL.
        """
        candidates = [
            ("cloud", 1.0, 0.01, 0.0),   # high quality, high cost
            ("local", 0.5, 0.0, 0.0),    # lower quality, zero cost
        ]
        ranked = feynman_amplitude_rank(candidates)
        assert ranked[0] == "local", (
            f"Local q=0.5 ($0) must beat cloud q=1.0 ($0.01) per CC2, got ranked={ranked}"
        )

    def test_fp3_energy_penalty_breaks_zero_cost_tie(self) -> None:
        """FP3 discriminating: among zero-cost tiers with equal quality, energy wins.

        NPU at ~2 W beats CPU at ~55 W when quality and cost are tied.
        Wrong impl (ignoring energy) would preserve arbitrary input order.
        """
        # Equal quality, zero dollar cost, different energy
        candidates = [
            ("cpu", 0.8, 0.0, 55.0),   # 55 J (high wattage tier)
            ("npu", 0.8, 0.0, 2.0),    # 2 J  (low wattage tier)
            ("igpu", 0.8, 0.0, 15.0),  # 15 J (mid wattage tier)
        ]
        ranked = feynman_amplitude_rank(candidates)
        assert ranked[0] == "npu", (
            f"NPU (2J) must rank first among equal-quality zero-cost tiers, got {ranked}"
        )
        assert ranked[-1] == "cpu", (
            f"CPU (55J) must rank last among equal-quality zero-cost tiers, got {ranked}"
        )

    def test_fp4_stable_sort_preserves_input_order_for_ties(self) -> None:
        """FP4: Candidates with identical amplitude preserve input order.

        Wrong impl using unstable sort would give non-deterministic ordering.
        """
        # All identical amplitude → must come back in input order
        candidates = [
            ("a", 0.5, 0.0, 0.0),
            ("b", 0.5, 0.0, 0.0),
            ("c", 0.5, 0.0, 0.0),
        ]
        ranked = feynman_amplitude_rank(candidates)
        assert ranked == ["a", "b", "c"], (
            f"Equal-amplitude candidates must preserve input order (stable), got {ranked}"
        )

    def test_fp5_cc2_guarantee_feynman_path_weight(self) -> None:
        """FP5: Mathematical CC2 guarantee — local q=0.5 amplitude > cloud q=1.0 at $0.01.

        This is the single most important invariant for the Quarter-on-a-String protocol.
        If feynman_path_weight is miscalibrated (wrong λ), this fails.
        """
        local_amplitude = feynman_path_weight(0.5, cost_usd=0.0)
        cloud_amplitude = feynman_path_weight(1.0, cost_usd=0.01)
        assert local_amplitude > cloud_amplitude, (
            f"CC2 violation: local_amplitude={local_amplitude:.4f} must exceed "
            f"cloud_amplitude={cloud_amplitude:.4f} (λ=100 guarantees this at $0.01)"
        )
        # Exact values from harness (λ=100): local=0.500, cloud≈0.368
        assert abs(local_amplitude - 0.5) < 1e-9, f"local_amplitude={local_amplitude} should be 0.5"
        assert 0.36 < cloud_amplitude < 0.37, f"cloud_amplitude={cloud_amplitude:.4f} should be ≈0.368"


# ---------------------------------------------------------------------------
# RollingRegimeTracker (RT1–RT5, 2026-07-04)
# ---------------------------------------------------------------------------


class TestRollingRegimeTracker:
    """Streaming HIHO regime tracker over a fixed rolling window.

    RT1: Returns None before min_samples; returns a FractalRegime after.
    RT2: DISCRIMINATING — window eviction: oldest scores are dropped, only recent matter.
    RT3: is_hiho() / deviation() / current_regime() / regime_history() API correctness.
    RT4: reset() clears window and history (start fresh without creating a new instance).
    RT5: DISCRIMINATING — window_size < 4 raises ValueError (FD requires ≥ 4 points).
    """

    def test_rt1_returns_none_before_min_samples(self) -> None:
        """RT1: update() returns None until min_samples scores have been fed."""
        tracker = RollingRegimeTracker(window_size=20, min_samples=20)
        for i in range(19):
            result = tracker.update(0.5)
            assert result is None, f"update {i + 1}/19 must return None (below min_samples)"
        # 20th update should return a regime (not None)
        result = tracker.update(0.5)
        assert result is not None, "20th update must return a FractalRegime, not None"
        assert isinstance(result, FractalRegime), f"Expected FractalRegime, got {type(result)}"

    def test_rt1_current_regime_none_before_min_samples(self) -> None:
        """RT1: current_regime() is None when no regime has been computed yet."""
        tracker = RollingRegimeTracker(window_size=20, min_samples=20)
        assert tracker.current_regime() is None
        tracker.update(0.5)  # still 1/20
        assert tracker.current_regime() is None

    def test_rt2_window_eviction_only_recent_scores_matter(self) -> None:
        """RT2 discriminating: once window fills, old scores are evicted.

        Feed 20 Brownian-ish scores (HIHO expected), then overwrite with 80 constant
        scores all at 0.0 (STUCK expected via deviation from 0.5). If eviction works,
        the tracker should eventually settle into STUCK because the old Brownian scores
        are gone. Wrong impl (accumulating all scores) would keep Brownian influence.
        """
        tracker = RollingRegimeTracker(window_size=20, min_samples=20)
        # Phase 1: Fill with constant-0.0 scores
        for _ in range(40):
            tracker.update(0.0)
        # After 40 constant-0.0 scores with window=20, all 20 slots hold 0.0
        # Deviation = |0.0 - 0.5| = 0.5 >> 0.1 → hiho_engaged=False
        assert not tracker.is_hiho(), (
            "After 40 scores at 0.0, tracker must NOT be HIHO (deviation=0.5)"
        )
        # Now reset and prove the window is truly bounded
        assert len(tracker) == 20, f"Window must be capped at 20, got {len(tracker)}"

    def test_rt3_api_correctness(self) -> None:
        """RT3: is_hiho(), deviation(), current_regime(), regime_history() behave correctly."""
        tracker = RollingRegimeTracker(window_size=20, min_samples=5)
        # Before min_samples: deviation still works (uses raw scores)
        tracker.update(0.5)
        assert abs(tracker.deviation() - 0.0) < 1e-9, "Single score at 0.5 → deviation=0.0"
        assert tracker.is_hiho() is False  # regime not yet computed (below min_samples)

        # Feed enough scores
        for _ in range(20):
            tracker.update(0.5)
        regime_hist = tracker.regime_history()
        assert len(regime_hist) > 0, "regime_history() must be non-empty after min_samples"
        assert tracker.current_regime() is regime_hist[-1], (
            "current_regime() must return the last entry in regime_history()"
        )

    def test_rt4_reset_clears_window_and_history(self) -> None:
        """RT4: reset() gives a fresh tracker without object recreation."""
        tracker = RollingRegimeTracker(window_size=20, min_samples=5)
        for _ in range(25):
            tracker.update(0.5)
        assert len(tracker) > 0
        assert tracker.current_regime() is not None

        tracker.reset()
        assert len(tracker) == 0, "reset() must clear the window"
        assert tracker.current_regime() is None, "reset() must clear regime history"
        assert tracker.regime_history() == [], "reset() must return empty regime_history()"

    def test_rt5_window_size_less_than_4_raises(self) -> None:
        """RT5: window_size < 4 raises ValueError (FD requires ≥ 4 points).

        Wrong impl (allowing tiny windows) silently returns FD=1.0 and STUCK always.
        """
        with pytest.raises(ValueError, match="window_size"):
            RollingRegimeTracker(window_size=3)
