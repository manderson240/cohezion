"""Item 82: skill-firing concentration scalar (report-only, TDD red→green).

`firing_concentration(usage_events, registry_skills)` → `FiringConcentration`
with `{top_skill_share, unused_share, total_firings}`.

Each test fails a plausible wrong impl:
  - divides unused_share by fired-skill count (not registry size)  -> test_unused_share_over_registry
  - counts unregistered firings in total_firings                    -> test_unregistered_excluded
  - ZeroDivision on empty event stream                              -> test_zero_events_no_crash
  - top_skill_share uses event count not registered-firing count    -> test_top_skill_share_excludes_unregistered
"""

from __future__ import annotations

import pytest

from cohezion.compound.skill_adoption import FiringConcentration, firing_concentration


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _evt(skill: str) -> dict:
    return {"skill_name": skill}


# ---------------------------------------------------------------------------
# Core discrimination tests
# ---------------------------------------------------------------------------


class TestTopSkillShare:
    """top_skill_share = most_fired / total_registered_firings."""

    def test_one_skill_dominates(self) -> None:
        """1 of 4 skills gets 9 of 10 firings → top_skill_share == 0.9."""
        events = [_evt("alpha")] * 9 + [_evt("beta")]
        result = firing_concentration(events, registry_skills=["alpha", "beta", "gamma", "delta"])
        assert result.top_skill_share == pytest.approx(0.9)

    def test_uniform_distribution(self) -> None:
        """When all registered skills fire equally, top_share = 1/N."""
        events = [_evt("A"), _evt("B"), _evt("C"), _evt("D")]
        result = firing_concentration(events, registry_skills=["A", "B", "C", "D"])
        assert result.top_skill_share == pytest.approx(0.25)

    def test_single_skill_all_firings(self) -> None:
        """One registered skill with all firings → top_skill_share == 1.0."""
        events = [_evt("X")] * 5
        result = firing_concentration(events, registry_skills=["X", "Y"])
        assert result.top_skill_share == pytest.approx(1.0)

    def test_top_skill_share_excludes_unregistered(self) -> None:
        """Unregistered firings are excluded from both numerator and denominator."""
        # 3 registered firings (all to "A"), 7 unregistered firings → share = 3/3 = 1.0
        events = [_evt("A")] * 3 + [_evt("unregistered")] * 7
        result = firing_concentration(events, registry_skills=["A", "B"])
        assert result.total_firings == 3
        assert result.top_skill_share == pytest.approx(1.0)


class TestUnusedShare:
    """unused_share = never_fired / total_registered (NOT / fired-skill count)."""

    def test_unused_share_over_registry(self) -> None:
        """MAIN DISCRIMINATOR: unused_share divides by registry size, not fired-skill count.

        3 registered skills; only 1 fires; unused = 2.
        unused_share = 2/3, NOT 2/1 (the wrong impl divides by 1 fired skill).
        """
        events = [_evt("A")]
        result = firing_concentration(events, registry_skills=["A", "B", "C"])
        assert result.unused_share == pytest.approx(2 / 3)

    def test_all_skills_fire(self) -> None:
        """When every registered skill fires at least once, unused_share == 0.0."""
        events = [_evt("A"), _evt("B"), _evt("C")]
        result = firing_concentration(events, registry_skills=["A", "B", "C"])
        assert result.unused_share == pytest.approx(0.0)

    def test_no_skills_fire(self) -> None:
        """When nothing fires (empty events), all registered skills are unused → share == 1.0."""
        result = firing_concentration([], registry_skills=["A", "B", "C"])
        assert result.unused_share == pytest.approx(1.0)


class TestTotalFirings:
    """total_firings counts only registered firings."""

    def test_unregistered_excluded(self) -> None:
        """Unregistered skill firings are NOT counted in total_firings."""
        events = [_evt("registered")] * 4 + [_evt("ghost")] * 10
        result = firing_concentration(events, registry_skills=["registered", "other"])
        assert result.total_firings == 4

    def test_zero_events(self) -> None:
        """Empty event stream → total_firings == 0."""
        result = firing_concentration([], registry_skills=["A", "B"])
        assert result.total_firings == 0


class TestEdgeCases:
    """Zero-division guards and trivial inputs."""

    def test_zero_events_no_crash(self) -> None:
        """Empty event stream must not raise ZeroDivisionError."""
        result = firing_concentration([], registry_skills=["A", "B", "C"])
        assert isinstance(result, FiringConcentration)
        assert result.top_skill_share == pytest.approx(0.0)
        assert result.unused_share == pytest.approx(1.0)
        assert result.total_firings == 0

    def test_empty_registry_no_crash(self) -> None:
        """Empty registry (no registered skills) must not crash."""
        result = firing_concentration([_evt("X")], registry_skills=[])
        assert isinstance(result, FiringConcentration)
        assert result.top_skill_share == pytest.approx(0.0)
        assert result.unused_share == pytest.approx(0.0)
        assert result.total_firings == 0

    def test_result_type(self) -> None:
        result = firing_concentration([_evt("A")], registry_skills=["A"])
        assert isinstance(result, FiringConcentration)
        assert 0.0 <= result.top_skill_share <= 1.0
        assert 0.0 <= result.unused_share <= 1.0
        assert result.total_firings >= 0
