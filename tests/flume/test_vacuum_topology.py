"""Tests for VacuumTopologyClassifier — harness invariants VT1–VT6."""

import numpy as np
import pytest

from cohezion.flume.vacuum_topology import (
    _INSTANTON_CENTER,
    _SOLITON_CENTER,
    _TRIVIAL_CENTER,
    VACUUM_LABELS,
    VacuumTopologyClassifier,
    classify_point,
)


@pytest.fixture
def clf():
    return VacuumTopologyClassifier()


# VT1 ─ prototype centres are unit-norm -----------------------------------


def test_prototype_centers_unit_norm():
    for name, ctr in [
        ("trivial", _TRIVIAL_CENTER),
        ("soliton", _SOLITON_CENTER),
        ("instanton", _INSTANTON_CENTER),
    ]:
        norm = float(np.linalg.norm(ctr))
        assert abs(norm - 1.0) < 1e-9, f"{name} centre not unit-norm: {norm}"


# VT2 ─ label is always a member of VACUUM_LABELS -------------------------


def test_label_always_valid(clf):
    rng = np.random.RandomState(42)
    for _ in range(50):
        v = rng.randn(12)
        result = clf.classify(v)
        assert result.label in VACUUM_LABELS
        assert 0.0 <= result.confidence <= 1.0


# VT3 ─ each prototype maps to its own class (identity property) ----------


def test_trivial_center_classifies_trivial(clf):
    assert clf.classify(_TRIVIAL_CENTER).label == "trivial"


def test_soliton_center_classifies_soliton(clf):
    assert clf.classify(_SOLITON_CENTER).label == "soliton"


def test_instanton_center_classifies_instanton(clf):
    assert clf.classify(_INSTANTON_CENTER).label == "instanton"


# VT4 ─ near-zero vectors are definitively trivial -----------------------


def test_near_zero_is_trivial(clf):
    v = np.full(12, 0.001)
    result = clf.classify(v)
    assert result.label == "trivial"
    assert result.confidence == 1.0


# VT5 ─ noise robustness: perturbed prototype stays in its class ---------


def test_noisy_soliton_stays_soliton(clf):
    rng = np.random.RandomState(7)
    noise = rng.randn(12) * 0.05
    result = clf.classify(_SOLITON_CENTER + noise)
    assert result.label == "soliton"


def test_noisy_instanton_stays_instanton(clf):
    rng = np.random.RandomState(13)
    noise = rng.randn(12) * 0.05
    result = clf.classify(_INSTANTON_CENTER + noise)
    assert result.label == "instanton"


# VT6 ─ batch and diversity APIs ------------------------------------------


def test_classify_many_returns_correct_count(clf):
    pts = [_TRIVIAL_CENTER, _SOLITON_CENTER, _INSTANTON_CENTER]
    results = clf.classify_many(pts)
    assert len(results) == 3
    assert [r.label for r in results] == ["trivial", "soliton", "instanton"]


def test_topological_diversity_uniform_is_one(clf):
    pts = [_TRIVIAL_CENTER, _SOLITON_CENTER, _INSTANTON_CENTER]
    div = clf.topological_diversity(pts)
    assert abs(div["diversity"] - 1.0) < 1e-6


def test_topological_diversity_all_same_is_zero(clf):
    pts = [_TRIVIAL_CENTER, _TRIVIAL_CENTER, _TRIVIAL_CENTER]
    div = clf.topological_diversity(pts)
    assert div["diversity"] == 0.0


def test_topological_diversity_empty_returns_zero(clf):
    div = clf.topological_diversity([])
    assert div["diversity"] == 0.0


# VT7 ─ module singleton --------------------------------------------------


def test_classify_point_singleton():
    r1 = classify_point(_SOLITON_CENTER)
    r2 = classify_point(_SOLITON_CENTER)
    assert r1.label == r2.label == "soliton"
    assert r1.confidence == r2.confidence


# VT8 ─ to_dict keys and types -------------------------------------------


def test_to_dict_structure(clf):
    d = clf.classify(_INSTANTON_CENTER).to_dict()
    assert set(d.keys()) == {"label", "confidence", "l2_norm", "runner_up", "runner_up_confidence"}
    assert isinstance(d["label"], str)
    assert isinstance(d["confidence"], float)
    assert isinstance(d["l2_norm"], float)


# VT9 ─ wrong shape raises -------------------------------------------------


def test_wrong_shape_raises(clf):
    with pytest.raises(ValueError, match="Expected 12D"):
        clf.classify(np.zeros(8))
