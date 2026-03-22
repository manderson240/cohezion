"""Tests for Skill Evolution Diffs (Story 5.5, FR18)."""

from __future__ import annotations

from cohezion.compound.skill_evolution_diff import SkillEvolutionTracker


class TestSkillEvolutionTracker:
    def test_first_version_no_diff(self):
        """First version has no diff (nothing to compare)."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("COMPOUND_PRIME", "# Compound Engineering\n")
        assert len(tracker.get_diffs()) == 0

    def test_second_version_generates_diff(self):
        """Second version generates a diff against the first."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("COMPOUND_PRIME", "# Compound\nLine 1\n")
        tracker.record_version("COMPOUND_PRIME", "# Compound\nLine 1\nLine 2\n")
        diffs = tracker.get_diffs()
        assert len(diffs) == 1
        assert diffs[0].additions == 1
        assert diffs[0].removals == 0

    def test_removal_tracked(self):
        """Removed lines are counted as Plasma removals."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("SKILL_X", "Line A\nLine B\nLine C\n")
        tracker.record_version("SKILL_X", "Line A\nLine C\n")
        diffs = tracker.get_diffs()
        assert diffs[0].removals == 1

    def test_diff_text_contains_unified_format(self):
        """Diff text is in unified diff format."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("SKILL_Y", "old\n")
        tracker.record_version("SKILL_Y", "new\n")
        diff = tracker.get_diffs()[0]
        assert "---" in diff.diff_text
        assert "+++" in diff.diff_text

    def test_filter_by_skill_name(self):
        """Diffs can be filtered by skill name."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("A", "v1\n")
        tracker.record_version("A", "v2\n")
        tracker.record_version("B", "v1\n")
        tracker.record_version("B", "v2\n")
        assert len(tracker.get_diffs("A")) == 1
        assert len(tracker.get_diffs("B")) == 1

    def test_multiple_versions_chain(self):
        """Multiple versions generate sequential diffs."""
        tracker = SkillEvolutionTracker()
        for i in range(4):
            tracker.record_version("EVOLVING", f"version {i}\n")
        assert len(tracker.get_diffs()) == 3

    def test_latest_version(self):
        """Latest version is retrievable."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("S1", "first\n")
        tracker.record_version("S1", "second\n")
        latest = tracker.get_latest_version("S1")
        assert latest is not None
        assert latest.version == 2
        assert latest.content == "second\n"

    def test_unknown_skill_returns_none(self):
        """Unknown skill returns None for latest version."""
        tracker = SkillEvolutionTracker()
        assert tracker.get_latest_version("NONEXISTENT") is None

    def test_evolution_report(self):
        """Evolution report exports all diffs."""
        tracker = SkillEvolutionTracker()
        tracker.record_version("R1", "a\n")
        tracker.record_version("R1", "b\n")
        report = tracker.get_evolution_report()
        assert len(report) == 1
        assert "additions" in report[0]

    def test_content_hash_differs_per_version(self):
        """Each version gets a unique content hash."""
        tracker = SkillEvolutionTracker()
        v1 = tracker.record_version("H1", "content A\n")
        v2 = tracker.record_version("H1", "content B\n")
        assert v1.content_hash != v2.content_hash
