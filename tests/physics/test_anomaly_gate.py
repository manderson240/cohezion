"""Tests for the domain-pluggable AnomalyGate + local-inference Skeptic (the blend)."""

from __future__ import annotations

import pytest

from cohezion.physics.anomaly_gate import (
    AnomalyGate,
    AnomalyVerdict,
    InvariantKind,
    InvariantSpec,
    LocalSkeptic,
    adjudicate,
)
from cohezion.physics.conservation_filter import Verdict


# -- deterministic gate across domains ----------------------------------------


def test_standard_when_all_within_tolerance():
    g = AnomalyGate()
    v = g.evaluate("mhd", {"energy": 0.02, "solenoidal_div_b": 1e-9, "unitarity": 1e-10})
    assert v.verdict is Verdict.STANDARD


@pytest.mark.parametrize("domain", ["mhd", "spinor", "gauge", "lagrangian", "toe"])
def test_every_registered_domain_evaluable(domain):
    g = AnomalyGate()
    v = g.evaluate(domain, {})  # no measurements -> nothing fails -> standard
    assert isinstance(v, AnomalyVerdict) and v.verdict is Verdict.STANDARD


def test_unknown_domain_raises():
    with pytest.raises(KeyError):
        AnomalyGate().evaluate("phlogiston", {"energy": 1.0})


def test_physical_violation_with_integrity_intact_is_anomaly():
    g = AnomalyGate()
    v = g.evaluate("mhd", {"energy": 0.6, "solenoidal_div_b": 1e-9, "unitarity": 1e-10})
    assert (
        v.verdict is Verdict.ANOMALY and v.physical_failed == ["energy"] and not v.integrity_failed
    )


def test_integrity_failure_dominates_physical_spike_is_reject():
    """The cross-domain discriminator: a spike + integrity failure is an artifact, not a discovery."""
    g = AnomalyGate()
    v = g.evaluate("mhd", {"energy": 5.0, "solenoidal_div_b": 1.0})  # ∇·B drift + huge spike
    assert v.verdict is Verdict.REJECT
    assert "solenoidal_div_b" in v.integrity_failed
    assert "energy" in v.physical_failed  # recorded but vetoed


def test_gauge_negative_action_is_reject():
    v = AnomalyGate().evaluate("gauge", {"yang_mills_nonneg": 0.3, "energy": 0.9})
    assert v.verdict is Verdict.REJECT and "yang_mills_nonneg" in v.integrity_failed


def test_toe_symmetry_order_anomaly():
    v = AnomalyGate().evaluate("toe", {"noether_current": 1e-9, "symmetry_order": 0.4})
    assert v.verdict is Verdict.ANOMALY and v.physical_failed == ["symmetry_order"]


def test_register_new_domain():
    g = AnomalyGate()
    g.register(
        "tek",
        [
            InvariantSpec("ledger_balance", InvariantKind.INTEGRITY, 1e-9),
            InvariantSpec("emergent_coherence", InvariantKind.PHYSICAL, 0.1),
        ],
    )
    assert g.evaluate("tek", {"emergent_coherence": 0.5}).verdict is Verdict.ANOMALY
    assert g.evaluate("tek", {"ledger_balance": 1.0}).verdict is Verdict.REJECT


# -- Skeptic (faked call for determinism) -------------------------------------


def _anom():
    return AnomalyVerdict("mhd", Verdict.ANOMALY, [], ["energy"], "test")


def test_skeptic_refutes():
    sk = LocalSkeptic(
        call=lambda p: (
            "Analysis... REFUTED: energy spike is an unconstrained grid-boundary artifact."
        )
    )
    v = sk.falsify(_anom(), {"energy": 0.6})
    assert v.survived is False and "boundary" in v.refutation


def test_skeptic_cannot_dismiss_survives():
    sk = LocalSkeptic(call=lambda p: "I considered boundary and mesh effects. SURVIVED")
    v = sk.falsify(_anom(), {"energy": 0.6})
    assert v.survived is True and v.refutation is None


def test_skeptic_falls_back_to_survive_on_fleet_failure():
    def boom(p):
        raise RuntimeError("connection refused")

    v = LocalSkeptic(call=boom).falsify(_anom(), {"energy": 0.6})
    assert (
        v.survived is True and "unavailable" in v.note
    )  # never auto-reject when validator is down


# -- the blend: adjudicate chains deterministic -> non-deterministic ----------


def test_adjudicate_standard_skips_inference():
    out = adjudicate("mhd", {"energy": 0.01}, skeptic=LocalSkeptic(call=lambda p: "REFUTED: x"))
    assert out["final"] == "standard" and "skeptic" not in out  # cheap path stays cheap


def test_adjudicate_reject_skips_inference():
    out = adjudicate(
        "mhd", {"solenoidal_div_b": 1.0}, skeptic=LocalSkeptic(call=lambda p: "SURVIVED")
    )
    assert out["final"] == "reject" and "skeptic" not in out  # artifacts never reach the LLM


def test_adjudicate_anomaly_invokes_skeptic_refuted():
    out = adjudicate(
        "mhd", {"energy": 0.6}, skeptic=LocalSkeptic(call=lambda p: "REFUTED: boundary error")
    )
    assert out["verdict"]["verdict"] == "anomaly"
    assert out["final"] == "rejected_by_skeptic"


def test_adjudicate_anomaly_survives_to_human():
    out = adjudicate("mhd", {"energy": 0.6}, skeptic=LocalSkeptic(call=lambda p: "SURVIVED"))
    assert out["final"] == "human_review" and out["skeptic"]["survived"] is True
