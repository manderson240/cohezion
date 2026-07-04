"""TDD tests for SkillStateEncoder (Task #24) — V-model MD level.

SkillStateEncoder encodes MGPO skill state and RubricVerdict into 256D float32
vectors using the same layout as ExperienceEncoder, adding MGPO-specific
dimensions.

256D layout (must match ExperienceEncoder for manifold compatibility):
  [0:12]   12D trajectory (zeros unless JourneyTracker provides one)
  [12]     mgpo_weight (MGPO bell curve weight)
  [13]     success_rate (0–1)
  [14]     rubric_passed (0.0 or 1.0)
  [15]     invocation_count_norm (log-scaled, clipped to [0,1])
  [16:24]  reserved scalar metrics (zeros)
  [24:29]  5D operation type one-hot
  [29:256] 227D semantic fingerprint (SHA-256 of skill_name + context)

V-Model contracts:
  MD1: SkillStateEncoder has encode_skill() → np.ndarray(256,) float32
  MD2: SkillStateEncoder has encode_rubric_verdict() → np.ndarray(256,)
  MD3: mgpo_weight placed at dim 12
  MD4: success_rate placed at dim 13
  MD5: rubric_passed placed at dim 14 (1.0=passed, 0.0=failed)
  MD6: output always exactly shape (256,) dtype float32
  MD7: encoding is deterministic (same inputs → same vector, always)
  MD8: skill name fingerprint occupies [29:256] (non-zero)
  MD9: different skill names produce different vectors
  MD10: different rubric_passed values produce different vectors at dim 14
"""

from __future__ import annotations


import numpy as np


def _import_encoder():
    from cohezion.flume.skill_state_encoder import SkillStateEncoder
    return SkillStateEncoder


# ── MD1/MD2: interface ───────────────────────────────────────────────────────


def test_skill_state_encoder_importable():
    enc = _import_encoder()
    assert enc is not None


def test_encode_skill_exists():
    enc = _import_encoder()
    e = enc()
    assert hasattr(e, "encode_skill") and callable(e.encode_skill)


def test_encode_rubric_verdict_exists():
    enc = _import_encoder()
    e = enc()
    assert hasattr(e, "encode_rubric_verdict") and callable(e.encode_rubric_verdict)


# ── MD6: shape and dtype ─────────────────────────────────────────────────────


def test_encode_skill_returns_256d_float32():
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("my_skill", mgpo_weight=0.9, success_rate=0.5)
    assert isinstance(v, np.ndarray), "Must return np.ndarray"
    assert v.shape == (256,), f"Must be 256D, got {v.shape}"
    assert v.dtype == np.float32, f"Must be float32, got {v.dtype}"


def test_encode_rubric_verdict_returns_256d_float32():
    from cohezion.compound.rubric_middleware import RubricVerdict
    enc = _import_encoder()
    e = enc()
    verdict = RubricVerdict(passed=True, reason="Output is coherent.")
    v = e.encode_rubric_verdict("my_skill", verdict=verdict, mgpo_weight=0.9, success_rate=0.5)
    assert v.shape == (256,)
    assert v.dtype == np.float32


# ── MD3: mgpo_weight at dim 12 ────────────────────────────────────────────────


def test_mgpo_weight_at_dim_12():
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("skill", mgpo_weight=0.75, success_rate=0.5)
    assert abs(v[12] - 0.75) < 1e-6, (
        f"mgpo_weight must be at dim 12; got {v[12]:.4f}"
    )


def test_mgpo_weight_boundary_is_1():
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("skill", mgpo_weight=1.0, success_rate=0.5)
    assert abs(v[12] - 1.0) < 1e-6


# ── MD4: success_rate at dim 13 ───────────────────────────────────────────────


def test_success_rate_at_dim_13():
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("skill", mgpo_weight=0.5, success_rate=0.8)
    assert abs(v[13] - 0.8) < 1e-6, (
        f"success_rate must be at dim 13; got {v[13]:.4f}"
    )


# ── MD5: rubric_passed at dim 14 ──────────────────────────────────────────────


def test_rubric_passed_true_at_dim_14():
    from cohezion.compound.rubric_middleware import RubricVerdict
    enc = _import_encoder()
    e = enc()
    verdict = RubricVerdict(passed=True, reason="ok")
    v = e.encode_rubric_verdict("skill", verdict=verdict, mgpo_weight=0.5, success_rate=0.5)
    assert abs(v[14] - 1.0) < 1e-6, f"rubric_passed=True must give 1.0 at dim 14; got {v[14]}"


def test_rubric_passed_false_at_dim_14():
    from cohezion.compound.rubric_middleware import RubricVerdict
    enc = _import_encoder()
    e = enc()
    verdict = RubricVerdict(passed=False, reason="hallucinated")
    v = e.encode_rubric_verdict("skill", verdict=verdict, mgpo_weight=0.5, success_rate=0.5)
    assert abs(v[14] - 0.0) < 1e-6, f"rubric_passed=False must give 0.0 at dim 14; got {v[14]}"


def test_encode_skill_defaults_rubric_passed_to_1():
    """encode_skill (no verdict) must default rubric_passed=1.0 at dim 14."""
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("skill", mgpo_weight=0.5, success_rate=0.5)
    assert abs(v[14] - 1.0) < 1e-6


# ── MD10: rubric changes vector at dim 14 only ────────────────────────────────


def test_rubric_passed_changes_vector_at_dim_14():
    """Changing rubric_passed must change exactly dim 14 (discriminating test)."""
    from cohezion.compound.rubric_middleware import RubricVerdict
    enc = _import_encoder()
    e = enc()
    v_pass = e.encode_rubric_verdict(
        "skill", RubricVerdict(passed=True, reason="ok"), mgpo_weight=0.5, success_rate=0.5
    )
    v_fail = e.encode_rubric_verdict(
        "skill", RubricVerdict(passed=False, reason="ok"), mgpo_weight=0.5, success_rate=0.5
    )
    assert abs(v_pass[14] - v_fail[14]) > 0.9, "dim 14 must differ by ~1.0"
    # All other dims must be identical (same inputs except rubric_passed)
    other_dims = np.concatenate([v_pass[:14], v_pass[15:]])
    other_dims_fail = np.concatenate([v_fail[:14], v_fail[15:]])
    np.testing.assert_allclose(other_dims, other_dims_fail, atol=1e-6)


# ── MD7: determinism ─────────────────────────────────────────────────────────


def test_encode_skill_is_deterministic():
    enc = _import_encoder()
    e = enc()
    v1 = e.encode_skill("deterministic_skill", mgpo_weight=0.42, success_rate=0.67)
    v2 = e.encode_skill("deterministic_skill", mgpo_weight=0.42, success_rate=0.67)
    np.testing.assert_array_equal(v1, v2, err_msg="Same inputs must produce identical vectors")


# ── MD8: fingerprint occupies [29:256] ───────────────────────────────────────


def test_fingerprint_region_is_nonzero():
    enc = _import_encoder()
    e = enc()
    v = e.encode_skill("any_skill", mgpo_weight=0.5, success_rate=0.5)
    fingerprint = v[29:]
    assert fingerprint.shape == (227,)
    assert np.any(fingerprint != 0.0), "Fingerprint region [29:256] must be non-zero"


# ── MD9: different skill names produce different vectors ──────────────────────


def test_different_skill_names_produce_different_vectors():
    enc = _import_encoder()
    e = enc()
    v1 = e.encode_skill("routing_skill", mgpo_weight=0.5, success_rate=0.5)
    v2 = e.encode_skill("analysis_skill", mgpo_weight=0.5, success_rate=0.5)
    assert not np.allclose(v1, v2), (
        "Different skill names must produce different fingerprints"
    )
