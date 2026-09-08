"""Unit tests for Phase 2 Alignment: Twistor Worldview Functor."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

from cohezion.flume.twistor_bundle_bridge import SOUL_DIM
from cohezion.worldviews.tradition_data import TOE_STEPS
from cohezion.worldviews.twistor_worldview_functor import (
    TwistorWorldviewFunctor,
)


@pytest.fixture
def functor() -> TwistorWorldviewFunctor:
    return TwistorWorldviewFunctor()


def test_tradition_count(functor: TwistorWorldviewFunctor) -> None:
    assert len(functor.traditions) == 17


def test_single_step_functor(functor: TwistorWorldviewFunctor) -> None:
    # Test Step 7: HIHO (Dynamic Equilibrium)
    step = functor.map_step_functor(7)
    assert step.step_index == 7
    assert step.canonical_name == TOE_STEPS[7]
    assert len(step.poincare_centroid_2048d) == SOUL_DIM
    assert step.hyperbolic_spread_radius > 0.0
    assert len(step.tradition_terms) == 17
    # Twistor null ray
    assert step.is_null_ray is True
    assert math.isclose(step.twistor_helicity, 0.0, abs_tol=1e-5)


def test_complete_alignment_execution(functor: TwistorWorldviewFunctor) -> None:
    res = functor.execute_complete_alignment()
    assert res["status"] == "PHASE_2_ALIGNMENT_COMPLETE"
    assert res["traditions_count"] == 17
    assert res["steps_count"] == 10
    assert res["hiho_step_conformal"] is True
    assert len(res["step_geodesics"]) == 9

    # Verify MOC note written to disk
    moc_path = Path(res["vault_moc"])
    assert moc_path.exists()
    content = moc_path.read_text(encoding="utf-8")
    assert "Phase 2 Alignment: Functorial Worldview Integration in CP³" in content
