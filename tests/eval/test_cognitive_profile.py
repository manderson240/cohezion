"""Falsification-first tests for the cognitive-profile harness.

These tests are written BEFORE the implementation and must FAIL until
`src/cohezion/eval/cognitive_profile.py` exists. They encode the discriminating
properties that make this a real measurement (verification-depth.md), not a
vanity dashboard:

  1. SEPARABILITY — neutralizing ONE axis's capability collapses ONLY that axis.
  2. PER-AXIS DISCRIMINATION — a no-op/wrong system on an axis scores LOW
     (an always-empty reasoner → G6 ≈ 0), proving the axis measures capability,
     not mere presence.
  3. BEYOND_REACH HONESTY — substrate-limited axes are reported BEYOND_REACH and
     are NEVER silently flipped to MET, even when the substrate scores well.
  4. COVERAGE — the profile reports all 10 DeepMind faculties (G1–G10).
"""

from __future__ import annotations

import dataclasses

from cohezion.eval.cognitive_profile import (
    Capabilities,
    oracle_capabilities,
    run_profile,
)


def _axis_score(profile: dict, axis_id: str) -> float:
    return profile["axes"][axis_id]["score"]


def _axis_status(profile: dict, axis_id: str) -> str:
    return profile["axes"][axis_id]["status"]


def test_profile_has_all_ten_faculties() -> None:
    """The profile JSON must contain an axis for every DeepMind faculty G1..G10."""
    profile = run_profile(capabilities=oracle_capabilities())
    axis_ids = set(profile["axes"].keys())
    for i in range(1, 11):
        assert any(aid.startswith(f"G{i}_") for aid in axis_ids), (
            f"no axis for faculty G{i}; axes present: {sorted(axis_ids)}"
        )


def test_axis_separability_reasoning_disabled_collapses_only_g6() -> None:
    """The DISCRIMINATING property: disabling the reasoning capability must
    collapse ONLY the G6 axis — memory (G5) and speed (B1) are untouched.

    A harness whose axes all move together (a global confound) FAILS this.
    """
    baseline = run_profile(capabilities=oracle_capabilities())

    crippled_caps = dataclasses.replace(oracle_capabilities(), reasoning_fn=lambda _prompt: "")
    crippled = run_profile(capabilities=crippled_caps)

    # G6 collapses
    assert _axis_score(baseline, "G6_reasoning") >= 0.7
    assert _axis_score(crippled, "G6_reasoning") < 0.34

    # Other axes are unchanged — the cripple was surgical, not global.
    assert _axis_score(crippled, "G5_memory") == _axis_score(baseline, "G5_memory")
    assert _axis_score(crippled, "B1_speed") == _axis_score(baseline, "B1_speed")


def test_noop_reasoner_scores_low_g6_real_reasoner_scores_high() -> None:
    """Per-axis discrimination: the G6 axis measures reasoning CAPABILITY, not
    the mere presence of a reasoner. An always-empty reasoner → G6 ≈ 0."""
    empty_caps = dataclasses.replace(oracle_capabilities(), reasoning_fn=lambda _prompt: "")
    wrong_caps = dataclasses.replace(oracle_capabilities(), reasoning_fn=lambda _prompt: "banana")
    assert _axis_score(run_profile(capabilities=empty_caps), "G6_reasoning") < 0.34
    assert _axis_score(run_profile(capabilities=wrong_caps), "G6_reasoning") < 0.34
    assert _axis_score(run_profile(capabilities=oracle_capabilities()), "G6_reasoning") >= 0.7


def test_beyond_reach_axis_never_silently_met() -> None:
    """Substrate-BEYOND-REACH honesty: a substrate axis (broad knowledge / Gc)
    must report BEYOND_REACH even when the substrate answers PERFECTLY. A high
    score must NOT be laundered into MET."""
    profile = run_profile(capabilities=oracle_capabilities())
    # Find at least one substrate-beyond-reach axis.
    beyond = {aid: ax for aid, ax in profile["axes"].items() if ax["substrate_beyond_reach"]}
    assert beyond, "no BEYOND_REACH axis declared — the harness hides substrate limits"
    for aid, ax in beyond.items():
        assert ax["status"] == "BEYOND_REACH", (
            f"{aid} scored {ax['score']} but status={ax['status']} — "
            "a substrate-limited axis was silently promoted (dishonest)"
        )


def test_oracle_capabilities_returns_capabilities() -> None:
    assert isinstance(oracle_capabilities(), Capabilities)


def test_every_axis_reports_required_fields() -> None:
    profile = run_profile(capabilities=oracle_capabilities())
    for aid, ax in profile["axes"].items():
        for key in ("faculty", "score", "n", "uncertainty", "status", "substrate_beyond_reach"):
            assert key in ax, f"axis {aid} missing field {key}"
        assert ax["status"] in {"MET", "PARTIAL", "GAP", "BEYOND_REACH"}
