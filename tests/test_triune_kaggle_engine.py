"""Unit tests for Percival's Triune Self Kaggle Ascension Engine."""

import pytest
from cohezion.compound.triune_kaggle_engine import (
    TriuneKaggleAscensionEngine,
    TriuneDoer,
    TriuneThinker,
    TriuneKnower,
)


def test_triune_doer_native_primitives():
    """Verify Doer executes native Rust primitives on hardware."""
    doer = TriuneDoer()
    assert doer.rust_available is True

    # 1. ARC-3 Zobrist hashing on hardware
    grid = [[1, 2], [3, 4]]
    h = doer.compute_zobrist_hash(grid, 42)
    assert isinstance(h, int) and h != 0

    # 2. ARC connected components
    comps = doer.extract_arc_components([[1, 0], [0, 2]])
    assert len(comps) == 2
    assert comps[0] == [[1, 0], [0, 0]] or comps[0] == [[0, 0], [0, 2]]

    # 3. Kaggriculture parallel rollouts
    mean, min_s, max_s, win_rate = doer.simulate_kaggriculture(num_sims=50, seed=42)
    assert max_s >= min_s
    assert 0.0 <= win_rate <= 1.0


def test_triune_thinker_hiho_and_invariants():
    """Verify Thinker evaluates HIHO coherence and AutoHarness invariants."""
    thinker = TriuneThinker(target_coherence=0.50, stiffness=0.20)

    # Identical vectors -> cos_sim = 1.0 -> coherence = 1.0 (sycophancy / over-alignment)
    c_high = thinker.compute_hiho_coherence([1.0] * 10, [1.0] * 10)
    assert pytest.approx(c_high, abs=1e-5) == 1.0
    f_high = thinker.compute_restoring_force(c_high)
    assert f_high < 0  # Force pushes back toward 0.50

    # Orthogonal vectors -> cos_sim = 0.0 -> coherence = 0.50 (perfect HIHO equilibrium)
    c_ortho = thinker.compute_hiho_coherence([1.0, 0.0], [0.0, 1.0])
    assert pytest.approx(c_ortho, abs=1e-5) == 0.50
    f_ortho = thinker.compute_restoring_force(c_ortho)
    assert pytest.approx(f_ortho, abs=1e-5) == 0.0

    # Kolmogorov Monotonicity invariant verification
    valid_knee = {"Abnormal": 0.85, "ACL": 0.70, "Meniscus": 0.60}
    ok, _ = thinker.verify_autoharness_invariants(valid_knee, {})
    assert ok is True

    invalid_knee = {"Abnormal": 0.50, "ACL": 0.80, "Meniscus": 0.30}
    ok_inv, msg = thinker.verify_autoharness_invariants(invalid_knee, {})
    assert ok_inv is False
    assert "Kolmogorov Monotonicity violated" in msg


def test_triune_knower_poincare_autocontext():
    """Verify Knower maintains 2048D Poincaré AutoContext metric space."""
    knower = TriuneKnower(dimension=2048)

    # Initial state near origin
    assert knower.get_conformal_factor() >= 2.0

    # Advance state with delta
    delta = [0.005] * 2048
    d_before = knower.get_poincare_distance([0.0] * 2048)
    knower.advance_autocontext(delta)
    d_after = knower.get_poincare_distance([0.0] * 2048)

    assert d_after > d_before
    assert knower.get_conformal_factor() >= 2.0


def test_triune_engine_complete_ascent_cycle():
    """Verify complete Percival cycle (Doer -> Thinker -> Knower)."""
    engine = TriuneKaggleAscensionEngine()

    def dummy_action():
        return {"Abnormal": 0.90, "ACL": 0.60}, {"loss": 0.12}

    report = engine.execute_ascent_cycle(
        competition_id="rsna-knee-abnormality-detection",
        task_intent="Evaluate Kolmogorov-monotonic 16-slice ensemble",
        doer_action_fn=dummy_action,
        intent_embedding=[0.5] * 512,
        state_embedding=[0.5] * 512,
    )

    assert report.doer_executed is True
    assert report.doer_duration_ms > 0
    assert report.thinker_verdict in ("ACCEPT", "RESTORE")
    assert report.poincare_norm >= 0.0
    assert len(engine.cycle_history) == 1
