"""Unit tests for Phase 2 Alignment: Twistor Worldview Functor."""

from __future__ import annotations

import math
from pathlib import Path

import pytest

import cohezion.data_mesh.durable_precipitation_bridge as dpb
from cohezion.flume.twistor_bundle_bridge import SOUL_DIM
from cohezion.worldviews.tradition_data import TOE_STEPS, get_traditions
from cohezion.worldviews.twistor_worldview_functor import (
    TwistorWorldviewFunctor,
)


@pytest.fixture
def functor(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> TwistorWorldviewFunctor:
    # Keep the MOC note and spool out of the real vault and repo, and SurrealDB offline.
    monkeypatch.setattr(dpb, "SPOOL_FILE", tmp_path / "witness_spool.jsonl")
    bridge = dpb.DurablePrecipitationBridge(
        vault_dir=tmp_path / "moc", surreal_url="http://127.0.0.1:9/sql"
    )
    return TwistorWorldviewFunctor(persistence=bridge)


# 18 since stealthskater was restored (harness.md S2, 2026-08-01); the registry is the source of truth.
N_TRADITIONS = len(get_traditions())


def test_tradition_count(functor: TwistorWorldviewFunctor) -> None:
    assert len(functor.traditions) == N_TRADITIONS


def test_single_step_functor(functor: TwistorWorldviewFunctor) -> None:
    # Test Step 7: HIHO (Dynamic Equilibrium)
    step = functor.map_step_functor(7)
    assert step.step_index == 7
    assert step.canonical_name == TOE_STEPS[7]
    assert len(step.poincare_centroid_2048d) == SOUL_DIM
    assert step.hyperbolic_spread_radius > 0.0
    assert len(step.tradition_terms) == N_TRADITIONS
    # Twistor null ray
    assert step.is_null_ray is True
    assert math.isclose(step.twistor_helicity, 0.0, abs_tol=1e-5)


def test_complete_alignment_execution(functor: TwistorWorldviewFunctor) -> None:
    res = functor.execute_complete_alignment()
    assert res["status"] == "PHASE_2_ALIGNMENT_COMPLETE"
    assert res["traditions_count"] == N_TRADITIONS
    assert res["steps_count"] == 10
    assert res["hiho_step_conformal"] is True
    assert len(res["step_geodesics"]) == 9

    # Verify MOC note written to disk
    moc_path = Path(res["vault_moc"])
    assert moc_path.exists()
    assert moc_path.parent == functor.persistence.vault_dir
    content = moc_path.read_text(encoding="utf-8")
    assert "Phase 2 Alignment: Functorial Worldview Integration in CP³" in content
