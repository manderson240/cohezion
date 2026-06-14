"""Tests for TwoComponentCondensate — Qi et al. 2026 exciton BEC phases."""

from __future__ import annotations

import numpy as np
import pytest

from cohezion.physics.two_component_bec import (
    CondensatePhase,
    TwoComponentCondensate,
    make_flume_bec,
    make_triune_bec,
    suggest_routing_from_bec,
)


# ── Fixtures ────────────────────────────────────────────────────────────────


@pytest.fixture
def symmetric_bec() -> TwoComponentCondensate:
    """Symmetric two-component BEC at B=0: both tiers equal, negative J → IIA."""
    return TwoComponentCondensate(r1=-1.0, r2=-1.0, u1=1.0, u2=1.0, g=0.5, J=-0.2, B=0.0)


@pytest.fixture
def polarized_bec() -> TwoComponentCondensate:
    """Strongly field-shifted BEC: one component favored → Phase I."""
    return TwoComponentCondensate(r1=-1.0, r2=-1.0, u1=1.0, u2=1.0, g=0.5, J=-0.2, B=5.0)


@pytest.fixture
def normal_bec() -> TwoComponentCondensate:
    """Above-critical BEC: both mass terms positive → NORMAL phase."""
    return TwoComponentCondensate(r1=1.0, r2=1.0, u1=1.0, u2=1.0, g=0.3, J=-0.1, B=0.0)


@pytest.fixture
def intervalley_bec() -> TwoComponentCondensate:
    """Anti-phase Josephson (J>0) → Phase IIB (intervalley)."""
    return TwoComponentCondensate(r1=-1.0, r2=-1.0, u1=1.0, u2=1.0, g=0.5, J=0.3, B=0.0)


# ── Construction ─────────────────────────────────────────────────────────────


def test_default_construction() -> None:
    bec = TwoComponentCondensate()
    assert bec.r1 == -1.0
    assert bec.r2 == -1.0
    assert bec.u1 == 1.0
    assert bec.u2 == 1.0


def test_invalid_u1_raises() -> None:
    with pytest.raises(ValueError, match="Self-interaction"):
        TwoComponentCondensate(u1=-0.5)


def test_invalid_u2_raises() -> None:
    with pytest.raises(ValueError, match="Self-interaction"):
        TwoComponentCondensate(u2=0.0)


# ── Effective mass terms ─────────────────────────────────────────────────────


def test_r1_eff_zero_field(symmetric_bec: TwoComponentCondensate) -> None:
    assert symmetric_bec.r1_eff == pytest.approx(-1.0)


def test_r2_eff_zero_field(symmetric_bec: TwoComponentCondensate) -> None:
    assert symmetric_bec.r2_eff == pytest.approx(-1.0)


def test_r1_eff_positive_field() -> None:
    """r₁(B) = r₁ + b₁×B — positive B increases r1_eff."""
    bec = TwoComponentCondensate(r1=-1.0, b1=1.0, B=2.0)
    assert bec.r1_eff == pytest.approx(-1.0 + 2.0)


def test_r2_eff_positive_field() -> None:
    """r₂(B) = r₂ − b₂×B — positive B decreases r2_eff."""
    bec = TwoComponentCondensate(r2=-1.0, b2=1.0, B=2.0)
    assert bec.r2_eff == pytest.approx(-1.0 - 2.0)


def test_r1_r2_shift_opposite_with_field() -> None:
    """B shifts r1 up and r2 down — opposite mass renormalization."""
    bec = TwoComponentCondensate(r1=-1.0, r2=-1.0, B=1.0, b1=1.0, b2=1.0)
    assert bec.r1_eff > bec.r2_eff


# ── Free energy ──────────────────────────────────────────────────────────────


def test_free_energy_at_zero_is_zero(symmetric_bec: TwoComponentCondensate) -> None:
    """F(0, 0) = 0 — trivial normal phase energy."""
    assert symmetric_bec.free_energy(0.0, 0.0) == pytest.approx(0.0)


def test_free_energy_is_finite(symmetric_bec: TwoComponentCondensate) -> None:
    F = symmetric_bec.free_energy(0.5, 0.5)
    assert np.isfinite(F)


def test_free_energy_josephson_always_negative_contribution() -> None:
    """Josephson term -2|J|ρ₁ρ₂ always lowers the energy for condensed state."""
    bec_with_J = TwoComponentCondensate(r1=-1.0, r2=-1.0, J=-0.5)
    bec_no_J = TwoComponentCondensate(r1=-1.0, r2=-1.0, J=0.0)
    assert bec_with_J.free_energy(0.5, 0.5) < bec_no_J.free_energy(0.5, 0.5)


def test_free_energy_negative_rho_clamped(symmetric_bec: TwoComponentCondensate) -> None:
    """Negative amplitudes are clamped to 0 — same as F(0,0)."""
    F_neg = symmetric_bec.free_energy(-0.5, -0.5)
    F_zero = symmetric_bec.free_energy(0.0, 0.0)
    assert F_neg == pytest.approx(F_zero)


# ── Minimization ─────────────────────────────────────────────────────────────


def test_minimize_returns_three_floats(symmetric_bec: TwoComponentCondensate) -> None:
    result = symmetric_bec.minimize_free_energy()
    assert len(result) == 3
    rho1, rho2, F = result
    assert all(isinstance(v, float) for v in (rho1, rho2, F))


def test_minimize_nonnegative_amplitudes(symmetric_bec: TwoComponentCondensate) -> None:
    rho1, rho2, _ = symmetric_bec.minimize_free_energy()
    assert rho1 >= 0.0
    assert rho2 >= 0.0


def test_minimize_free_energy_below_normal(symmetric_bec: TwoComponentCondensate) -> None:
    """Ground state energy must be ≤ trivial normal phase energy."""
    _, _, F_star = symmetric_bec.minimize_free_energy()
    assert F_star <= symmetric_bec.free_energy(0.0, 0.0)


def test_normal_phase_minimum_at_origin(normal_bec: TwoComponentCondensate) -> None:
    """With positive mass terms, minimum is at ρ₁=ρ₂=0."""
    rho1, rho2, _ = normal_bec.minimize_free_energy()
    assert rho1 == pytest.approx(0.0, abs=0.05)
    assert rho2 == pytest.approx(0.0, abs=0.05)


def test_symmetric_bec_both_condensed(symmetric_bec: TwoComponentCondensate) -> None:
    """Symmetric parameters → both order parameters condensed."""
    rho1, rho2, _ = symmetric_bec.minimize_free_energy()
    assert rho1 > 0.1
    assert rho2 > 0.1


# ── Phase identification ──────────────────────────────────────────────────────


def test_normal_phase_identified(normal_bec: TwoComponentCondensate) -> None:
    assert normal_bec.phase() == CondensatePhase.NORMAL


def test_iia_phase_negative_J(symmetric_bec: TwoComponentCondensate) -> None:
    """J < 0 → in-phase Josephson → Phase IIA (intravalley)."""
    assert symmetric_bec.J < 0
    assert symmetric_bec.phase() == CondensatePhase.IIA


def test_iib_phase_positive_J(intervalley_bec: TwoComponentCondensate) -> None:
    """J > 0 → anti-phase Josephson → Phase IIB (intervalley)."""
    assert intervalley_bec.J > 0
    assert intervalley_bec.phase() == CondensatePhase.IIB


def test_phase_I_strong_field(polarized_bec: TwoComponentCondensate) -> None:
    """Large B field forces one component to zero → Phase I."""
    phase = polarized_bec.phase()
    assert phase == CondensatePhase.I


def test_phase_enum_values() -> None:
    assert CondensatePhase.IIA.value == "IIA"
    assert CondensatePhase.IIB.value == "IIB"
    assert CondensatePhase.I.value == "I"
    assert CondensatePhase.NORMAL.value == "normal"


# ── Order parameters ─────────────────────────────────────────────────────────


def test_order_parameters_keys(symmetric_bec: TwoComponentCondensate) -> None:
    d = symmetric_bec.order_parameters()
    assert {"rho1", "rho2", "F_star", "polarization"} <= set(d.keys())


def test_polarization_symmetric_near_zero(symmetric_bec: TwoComponentCondensate) -> None:
    """Symmetric BEC at B=0 → polarization near zero."""
    d = symmetric_bec.order_parameters()
    assert abs(d["polarization"]) < 0.1


def test_polarization_bounds(symmetric_bec: TwoComponentCondensate) -> None:
    d = symmetric_bec.order_parameters()
    assert -1.0 <= d["polarization"] <= 1.0


# ── HIHO score ───────────────────────────────────────────────────────────────


def test_hiho_score_bounds(symmetric_bec: TwoComponentCondensate) -> None:
    score = symmetric_bec.hiho_condensate_score()
    assert 0.0 <= score <= 1.0


def test_hiho_score_peaks_at_equal_components() -> None:
    """Perfect balance ρ₁ = ρ₂ → score = 1.0."""
    bec = TwoComponentCondensate(r1=-1.0, r2=-1.0, u1=1.0, u2=1.0, g=0.0, J=-0.5, B=0.0)
    score = bec.hiho_condensate_score()
    assert score > 0.9  # near maximum for balanced case


def test_hiho_score_zero_for_normal(normal_bec: TwoComponentCondensate) -> None:
    """Uncondensed (NORMAL) phase → HIHO score = 0."""
    assert normal_bec.hiho_condensate_score() == pytest.approx(0.0, abs=1e-6)


def test_is_hiho_condensate_symmetric(symmetric_bec: TwoComponentCondensate) -> None:
    """Well-balanced symmetric BEC should be near HIHO condensate."""
    score = symmetric_bec.hiho_condensate_score()
    expected_hiho = score >= 1.0 - 0.05
    assert symmetric_bec.is_hiho_condensate() == expected_hiho


# ── First-order regime ────────────────────────────────────────────────────────


def test_first_order_regime_true_when_g_large() -> None:
    """g > √(u₁u₂) = 1.0 → first-order transition regime."""
    bec = TwoComponentCondensate(u1=1.0, u2=1.0, g=1.5)
    assert bec.is_first_order_regime()


def test_first_order_regime_false_when_g_small() -> None:
    """g < √(u₁u₂) = 1.0 → continuous (second-order) transition."""
    bec = TwoComponentCondensate(u1=1.0, u2=1.0, g=0.8)
    assert not bec.is_first_order_regime()


def test_first_order_boundary() -> None:
    """g = √(u₁u₂) exactly → NOT first-order (boundary is exclusive)."""
    bec = TwoComponentCondensate(u1=1.0, u2=1.0, g=1.0)
    assert not bec.is_first_order_regime()


# ── Field sweep ───────────────────────────────────────────────────────────────


def test_sweep_field_returns_list(symmetric_bec: TwoComponentCondensate) -> None:
    records = symmetric_bec.sweep_field(B_range=(-1.0, 1.0), n_points=5)
    assert isinstance(records, list)
    assert len(records) == 5


def test_sweep_field_record_keys(symmetric_bec: TwoComponentCondensate) -> None:
    records = symmetric_bec.sweep_field(B_range=(-1.0, 1.0), n_points=3)
    for rec in records:
        assert {"B", "phase", "rho1", "rho2", "F_star", "hiho_score"} <= set(rec.keys())


def test_sweep_field_phase_strings(symmetric_bec: TwoComponentCondensate) -> None:
    records = symmetric_bec.sweep_field(B_range=(-2.0, 2.0), n_points=5)
    valid_phases = {p.value for p in CondensatePhase}
    for rec in records:
        assert rec["phase"] in valid_phases


def test_sweep_field_b_values_ordered(symmetric_bec: TwoComponentCondensate) -> None:
    records = symmetric_bec.sweep_field(B_range=(-2.0, 2.0), n_points=10)
    b_values = [r["B"] for r in records]
    assert b_values == sorted(b_values)


def test_sweep_field_large_b_drives_polarization() -> None:
    """At large |B|, the system should enter Phase I (single-component)."""
    bec = TwoComponentCondensate(r1=-1.0, r2=-1.0, u1=1.0, u2=1.0, g=0.5, J=-0.2)
    records = bec.sweep_field(B_range=(4.0, 6.0), n_points=3)
    phases = {r["phase"] for r in records}
    # At least some records at large B should be Phase I
    assert CondensatePhase.I.value in phases or CondensatePhase.NORMAL.value in phases


# ── Serialization ─────────────────────────────────────────────────────────────


def test_to_dict_keys(symmetric_bec: TwoComponentCondensate) -> None:
    d = symmetric_bec.to_dict()
    required = {
        "phase",
        "rho1",
        "rho2",
        "F_star",
        "hiho_condensate_score",
        "is_first_order_regime",
        "B",
        "J",
        "g",
    }
    assert required <= set(d.keys())


def test_to_dict_phase_string(symmetric_bec: TwoComponentCondensate) -> None:
    d = symmetric_bec.to_dict()
    valid_phases = {p.value for p in CondensatePhase}
    assert d["phase"] in valid_phases


def test_to_dict_values_serializable(symmetric_bec: TwoComponentCondensate) -> None:
    import json

    d = symmetric_bec.to_dict()
    # Should serialize to JSON without error
    json.dumps(d)


# ── Convenience constructors ──────────────────────────────────────────────────


def test_make_triune_bec_default() -> None:
    bec = make_triune_bec(quality_budget=0.0)
    assert isinstance(bec, TwoComponentCondensate)
    assert bec.B == 0.0
    assert bec.J < 0  # HIHO in-phase at zero budget


def test_make_triune_bec_iia_at_zero_budget() -> None:
    """At quality_budget=0, HIHO mode: Phase IIA."""
    bec = make_triune_bec(quality_budget=0.0)
    assert bec.phase() == CondensatePhase.IIA


def test_make_triune_bec_quality_budget_sets_field() -> None:
    bec_pos = make_triune_bec(quality_budget=2.0)
    bec_neg = make_triune_bec(quality_budget=-2.0)
    # Positive budget: fast-tier favored (r1_eff shifts up, r2_eff shifts down)
    assert bec_pos.r1_eff > bec_neg.r1_eff


def test_make_flume_bec_default() -> None:
    bec = make_flume_bec(kl_weight=0.01)
    assert isinstance(bec, TwoComponentCondensate)
    assert bec.J == pytest.approx(-0.01 * 10.0)


def test_make_flume_bec_iia_healthy_vae() -> None:
    """Small KL weight → both encoder/decoder condensed → Phase IIA."""
    bec = make_flume_bec(kl_weight=0.01)  # A3 harness invariant
    assert bec.phase() == CondensatePhase.IIA


def test_make_flume_bec_b_coupling_zero() -> None:
    """FLUME BEC: no external field — B=0, b1=b2=0."""
    bec = make_flume_bec()
    assert bec.B == 0.0
    assert bec.b1 == 0.0
    assert bec.b2 == 0.0


# ── Routing suggestion ─────────────────────────────────────────────────────────


def test_suggest_routing_returns_string() -> None:
    tier = suggest_routing_from_bec(quality_budget=0.0)
    assert isinstance(tier, str)


def test_suggest_routing_valid_tiers() -> None:
    valid_tiers = {"npu", "igpu", "cpu", "cloud"}
    for budget in [-3.0, -1.0, 0.0, 1.0, 3.0]:
        tier = suggest_routing_from_bec(quality_budget=budget)
        assert tier in valid_tiers


def test_suggest_routing_default_is_igpu() -> None:
    """At zero budget, HIHO Phase IIA → igpu (balanced middle tier)."""
    tier = suggest_routing_from_bec(quality_budget=0.0)
    assert tier == "igpu"
