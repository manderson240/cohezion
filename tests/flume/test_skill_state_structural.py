"""Structural invariants for SkillStateEncoder — V-Model harness layer.

Per CLAUDE.md Learning 366: every behavioral invariant whose failure surface
is a keyword/signature drift gets a paired structural check here that fires
BEFORE behavioral tests with a named invariant (not a buried TypeError).

Three structural checks:
  SC1: _encode signature — all 8 parameters present by exact name
  SC2: Layout constants — _MGPO_WEIGHT_DIM, _SUCCESS_RATE_DIM, _RUBRIC_PASSED_DIM,
       _FINGERPRINT_START, _TOTAL_DIM, _FINGERPRINT_DIM match the values that
       every behavioral and manifold test hard-codes
  SC3: _FINGERPRINT_START consistency — module constant equals the slice index
       used by test_skill_state_encoder.py (MD8) and test_skill_state_manifold.py (SR3/SR4)
"""

from __future__ import annotations

import inspect

import cohezion.flume.skill_state_encoder as _mod
from cohezion.flume.skill_state_encoder import SkillStateEncoder


# ── SC1: _encode parameter names ─────────────────────────────────────────────

_ENCODE_EXPECTED_PARAMS = {
    "self",
    "skill_name",
    "mgpo_weight",
    "success_rate",
    "rubric_passed",
    "invocation_count",
    "trajectory",
    "operation_type",
    "context",
}


def test_encode_signature_has_all_expected_parameters():
    """SC1: _encode must accept all 8 expected keyword parameters.

    If any parameter is renamed or removed, behavioral tests crash with
    a buried TypeError deep in the call stack. This structural check fires
    first with a named invariant.
    """
    sig = inspect.signature(SkillStateEncoder._encode)
    actual_params = set(sig.parameters.keys())
    missing = _ENCODE_EXPECTED_PARAMS - actual_params
    assert not missing, (
        f"SC1: SkillStateEncoder._encode is missing parameters: {missing}. "
        f"Actual: {sorted(actual_params)}"
    )


# ── SC2: Layout constants match behavioral test assumptions ──────────────────

_LAYOUT_EXPECTED: dict[str, int] = {
    "_MGPO_WEIGHT_DIM": 12,
    "_SUCCESS_RATE_DIM": 13,
    "_RUBRIC_PASSED_DIM": 14,
    "_INVOCATION_COUNT_DIM": 15,
    "_OP_TYPE_START": 24,
    "_FINGERPRINT_START": 29,
    "_TOTAL_DIM": 256,
    "_FINGERPRINT_DIM": 227,
}


def test_layout_constants_match_behavioral_test_assumptions():
    """SC2: All 256D layout constants must match the values hard-coded in
    test_skill_state_encoder.py and test_skill_state_manifold.py.

    If any constant shifts (e.g. _FINGERPRINT_START from 29 to 30), every
    SR-level and MD-level assertion fails with a misleading numeric mismatch
    instead of a named constant-mismatch failure.
    """
    mismatches = []
    for name, expected in _LAYOUT_EXPECTED.items():
        actual = getattr(_mod, name, None)
        if actual != expected:
            mismatches.append(f"{name}: expected {expected}, got {actual}")
    assert not mismatches, (
        "SC2: Layout constant mismatch(es) — behavioral tests will produce "
        "misleading numeric failures:\n" + "\n".join(mismatches)
    )


# ── SC3: _FINGERPRINT_START equals the slice index used in tests ─────────────


def test_fingerprint_start_equals_slice_index_used_in_tests():
    """SC3: _FINGERPRINT_START must equal 29 — the literal slice index used in:
    - test_skill_state_encoder.py::MD8 (v[29:])
    - test_skill_state_manifold.py::SR3 and SR4 (v[29:])
    - routine_skill_geometry.py::_FINGERPRINT_START

    Drift in this constant silently makes those tests assert on the wrong
    dimension range.
    """
    assert _mod._FINGERPRINT_START == 29, (
        f"SC3: _FINGERPRINT_START must be 29 (slice used by manifold tests); "
        f"got {_mod._FINGERPRINT_START}"
    )


# ── SC4: encode_skill and encode_rubric_verdict return signatures ─────────────


def test_encode_skill_returns_type_annotation():
    """SC4: encode_skill must have a return annotation of np.ndarray (or compatible).
    Guards against accidentally dropping the return type."""
    sig = inspect.signature(SkillStateEncoder.encode_skill)
    assert sig.return_annotation is not inspect.Parameter.empty, (
        "SC4: encode_skill must have a return type annotation"
    )


def test_encode_rubric_verdict_accepts_verdict_positional():
    """SC4b: encode_rubric_verdict must accept 'verdict' as 2nd positional param
    (after self and skill_name). Callers pass it positionally; a rename breaks them."""
    sig = inspect.signature(SkillStateEncoder.encode_rubric_verdict)
    params = list(sig.parameters.keys())
    assert "verdict" in params, (
        f"SC4b: encode_rubric_verdict must have 'verdict' parameter; got {params}"
    )
    assert params.index("verdict") == 2, (  # self=0, skill_name=1, verdict=2
        f"SC4b: 'verdict' must be the 3rd parameter (index 2); got index {params.index('verdict')}"
    )
