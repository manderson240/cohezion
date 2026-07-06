"""AOEP-v0 Scorecard tests — discriminating stressor tests, one per axis.

Each test verifies that the scorer RESPONDS CORRECTLY to presence/absence of
the mechanism — not that the current system scores exactly X.0. This keeps tests
green before AND after the gap is filled.

Pattern: mock the probe kwarg to control the score independently of production
state, then assert the discriminating condition (higher score when mechanism is
present, lower when absent, never the same).
"""

from __future__ import annotations

import dataclasses

import pytest

from cohezion.compound.aoep_scorecard import AOEPScore, AOEPScorecard


@pytest.fixture()
def scorecard():
    return AOEPScorecard()


# ── Authority ─────────────────────────────────────────────────────────────────


class TestAOEPAuthority:
    def test_has_gate_returns_one(self, scorecard):
        """Score = 1.0 when authority gate exists (discriminating: wrong impl ignores probe)."""
        assert scorecard.score_authority(has_authority_gate=True) == 1.0

    def test_no_gate_returns_zero(self, scorecard):
        """Score = 0.0 when no authority gate exists."""
        assert scorecard.score_authority(has_authority_gate=False) == 0.0

    def test_gate_presence_changes_score(self, scorecard):
        """Discriminating: score must differ when gate is present vs absent."""
        with_gate = scorecard.score_authority(has_authority_gate=True)
        without_gate = scorecard.score_authority(has_authority_gate=False)
        assert with_gate > without_gate

    def test_structural_introspection_returns_float(self, scorecard):
        """Structural check: live introspection returns a valid 0.0–1.0 float."""
        score = scorecard.score_authority()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ── Scope ─────────────────────────────────────────────────────────────────────


class TestAOEPScope:
    def test_scope_filter_present_gives_nonzero(self, scorecard):
        """Discriminating: scope_filter hook present → score > 0."""
        assert scorecard.score_scope(has_scope_filter=True) > 0.0

    def test_scope_filter_absent_gives_zero(self, scorecard):
        """Discriminating: no scope_filter → score = 0.0 (confirmed gap)."""
        assert scorecard.score_scope(has_scope_filter=False) == 0.0

    def test_scope_score_discriminates(self, scorecard):
        """Score must differ when scope_filter is present vs absent."""
        assert scorecard.score_scope(has_scope_filter=True) > scorecard.score_scope(
            has_scope_filter=False
        )

    def test_live_scope_score_is_float(self, scorecard):
        """Live introspection: check SemanticCache.get() signature."""
        score = scorecard.score_scope()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ── Mutability ────────────────────────────────────────────────────────────────


class TestAOEPMutability:
    def test_seesaw_present_gives_nonzero(self, scorecard):
        """_seesaw_check present → score = 0.5 (partial)."""
        assert scorecard.score_mutability(has_seesaw=True) > 0.0

    def test_seesaw_absent_gives_zero(self, scorecard):
        """No seesaw → score = 0.0."""
        assert scorecard.score_mutability(has_seesaw=False) == 0.0

    def test_seesaw_discriminates(self, scorecard):
        """Discriminating: presence must strictly raise score."""
        assert scorecard.score_mutability(has_seesaw=True) > scorecard.score_mutability(
            has_seesaw=False
        )

    def test_live_mutability_uses_seesaw(self, scorecard):
        """Live introspection: score is a valid float in [0, 1].

        Note: CB15 (_seesaw_check in SkillRefiner.refine) is documented but not yet
        committed to this branch — score may be 0.0 (gap) or 0.5 (implemented).
        The probe-based discriminating tests (above) verify scoring logic independently.
        """
        score = scorecard.score_mutability()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ── Provenance ────────────────────────────────────────────────────────────────


class TestAOEPProvenance:
    def test_source_field_gives_full_score(self, scorecard):
        """Explicit source field → 1.0."""
        assert scorecard.score_provenance(has_source_field=True) == 1.0

    def test_no_source_field_gives_zero(self, scorecard):
        """No source field → 0.0."""
        assert scorecard.score_provenance(has_source_field=False) == 0.0

    def test_provenance_discriminates(self, scorecard):
        assert scorecard.score_provenance(has_source_field=True) > scorecard.score_provenance(
            has_source_field=False
        )

    def test_live_provenance_partial(self, scorecard):
        """TrajectoryPoint.action field → partial provenance (≥0.5 after JI1)."""
        score = scorecard.score_provenance()
        assert 0.0 <= score <= 1.0


# ── Recoverability ────────────────────────────────────────────────────────────


class TestAOEPRecoverability:
    def test_state_file_present_gives_one(self, scorecard):
        """State file exists → 1.0."""
        assert scorecard.score_recoverability(state_file_exists=True) == 1.0

    def test_no_state_file_gives_partial(self, scorecard):
        """restore_state callable but no file → 0.5 (partial)."""
        score = scorecard.score_recoverability(state_file_exists=False)
        # 0.5 = restore_state callable, just not yet persisted
        assert score == 0.5

    def test_recoverability_discriminates(self, scorecard):
        """State file present must score higher than absent."""
        assert scorecard.score_recoverability(
            state_file_exists=True
        ) > scorecard.score_recoverability(state_file_exists=False)

    def test_live_recoverability_structural(self, scorecard):
        """SkillRefiner.restore_state exists → score ≥ 0.5."""
        score = scorecard.score_recoverability()
        assert score >= 0.5, "SRS3: restore_state is in SkillRefiner"


# ── Actionability ─────────────────────────────────────────────────────────────


class TestAOEPActionability:
    def test_action_populated_gives_nonzero(self, scorecard):
        """action populated → score > 0."""
        assert scorecard.score_actionability(action_populated=True) > 0.0

    def test_action_absent_gives_zero(self, scorecard):
        """action absent → 0.0."""
        assert scorecard.score_actionability(action_populated=False) == 0.0

    def test_actionability_discriminates(self, scorecard):
        """Discriminating: populated vs absent must differ."""
        assert scorecard.score_actionability(action_populated=True) > scorecard.score_actionability(
            action_populated=False
        )

    def test_live_actionability_structural(self, scorecard):
        """Live introspection: score is a valid float in [0, 1].

        Note: JI1 (TrajectoryPoint.action) is documented in the harness but absent from
        this branch — score may be 0.0 (gap) or 0.5 (implemented). The probe-based
        discriminating tests (above) verify scoring logic independently.
        """
        score = scorecard.score_actionability()
        assert isinstance(score, float)
        assert 0.0 <= score <= 1.0


# ── Composite runner ──────────────────────────────────────────────────────────


class TestAOEPRun:
    def test_run_returns_aoep_score(self, scorecard):
        result = scorecard.run()
        assert isinstance(result, AOEPScore)

    def test_overall_is_mean_of_six(self, scorecard):
        """overall = mean(authority, scope, mutability, provenance, recoverability, actionability)."""
        result = scorecard.run()
        axes = [
            result.authority,
            result.scope,
            result.mutability,
            result.provenance,
            result.recoverability,
            result.actionability,
        ]
        expected = sum(axes) / 6
        assert abs(result.overall - expected) < 1e-9

    def test_gaps_contains_low_scoring_axes(self, scorecard):
        """Any axis < 0.5 must appear in gaps."""
        result = scorecard.run()
        fields = dataclasses.fields(AOEPScore)
        axis_names = {f.name for f in fields} - {"overall", "gaps"}
        for axis in axis_names:
            score = getattr(result, axis)
            if score < 0.5:
                assert axis in result.gaps, f"gap axis '{axis}' (score={score}) missing from gaps"

    def test_aoep_score_all_in_range(self, scorecard):
        result = scorecard.run()
        for axis in (
            "authority",
            "scope",
            "mutability",
            "provenance",
            "recoverability",
            "actionability",
        ):
            score = getattr(result, axis)
            assert 0.0 <= score <= 1.0, f"{axis} out of [0,1]: {score}"
