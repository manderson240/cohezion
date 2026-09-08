"""Unit tests for Poincaré-to-Twistor Bundle Bridge (Phase 1 Transcendence)."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cohezion.flume.twistor_bundle_bridge import SOUL_DIM, TwistorBundleBridge


@pytest.fixture
def bridge() -> TwistorBundleBridge:
    return TwistorBundleBridge()


def test_embed_text_to_poincare_2048d(bridge: TwistorBundleBridge) -> None:
    point = bridge.embed_text_to_poincare_2048d("cohezion.flume.geometric_correspondence")
    assert point.dim == SOUL_DIM
    assert len(point.coords) == SOUL_DIM

    norm_sq = sum(c * c for c in point.coords)
    assert norm_sq < 1.0  # Must be strictly within Poincaré unit ball
    assert norm_sq > 0.0


def test_poincare_to_4d_spacetime_lightcone(bridge: TwistorBundleBridge) -> None:
    point = bridge.embed_text_to_poincare_2048d("cohezion.physics.cosmogony")
    t, x, y, z = bridge.poincare_to_4d_spacetime(point)

    # Lightcone condition: t^2 = x^2 + y^2 + z^2
    spatial_sq = x * x + y * y + z * z
    temporal_sq = t * t
    assert math.isclose(temporal_sq, spatial_sq, rel_tol=1e-5)


def test_dissolve_module_twistor_properties(bridge: TwistorBundleBridge) -> None:
    state = bridge.dissolve_module(
        module_name="cohezion.physics.twistor_orch_or",
        module_summary="Penrose Twistor projective coordinates and Orch-OR quantum collapse",
    )
    assert state.module_name == "cohezion.physics.twistor_orch_or"
    assert state.twistor_state.is_null_ray is True
    assert math.isclose(state.twistor_state.helicity, 0.0, abs_tol=1e-5)
    assert state.orch_or_event.reduction_time_tau_s > 0.0


def test_batch_dissolve_and_precipitate(bridge: TwistorBundleBridge) -> None:
    modules = [
        ("cohezion.physics.cosmogony", "10-step cooling chain to 0.50 HIHO attractor"),
        ("cohezion.flume.poincare_manifold", "2048D Poincaré hyperbolic manifold"),
        ("cohezion.compound.triune_self", "Harold Percival Triune Self recursive loop"),
    ]
    res = bridge.batch_dissolve_and_precipitate(modules)
    assert res["status"] == "PHASE_1_DISSOLUTION_COMPLETE"
    assert res["modules_count"] == 3
    assert res["lightcone_conformity_pct"] == 100.0
    assert res["mean_hyperbolic_distance"] > 0.0

    # Verify MOC file exists on disk
    moc_path = Path(res["vault_moc"])
    assert moc_path.exists()
    content = moc_path.read_text(encoding="utf-8")
    assert "Phase 1 Dissolution: Poincaré-Twistor Semantic Fabric" in content
