"""Tests for Autonomous Skill Registration (Story 5.7, FR11)."""

from __future__ import annotations

from cohezion.registry.autonomous_registration import AutonomousSkillRegistry


class TestAutonomousSkillRegistry:
    def test_register_new_skill(self):
        """New skill is registered with version 1."""
        registry = AutonomousSkillRegistry()
        skill, conflict = registry.register("COMPOUND_PRIME", "# Compound\n")
        assert skill.version == 1
        assert conflict is None

    def test_duplicate_content_not_re_registered(self):
        """Same content returns existing skill without new version."""
        registry = AutonomousSkillRegistry()
        s1, _ = registry.register("S1", "content A")
        s2, _ = registry.register("S1", "content A")
        assert s1.version == s2.version == 1

    def test_version_conflict_increments(self):
        """Different content creates new version, not overwrite."""
        registry = AutonomousSkillRegistry()
        s1, _ = registry.register("S1", "version 1")
        s2, conflict = registry.register("S1", "version 2")
        assert s2.version == 2
        assert conflict is not None
        assert conflict.existing_version == 1
        assert conflict.new_version == 2

    def test_both_versions_preserved(self):
        """Both old and new versions are preserved."""
        registry = AutonomousSkillRegistry()
        registry.register("S1", "v1")
        registry.register("S1", "v2")
        versions = registry.get_all_versions("S1")
        assert len(versions) == 2

    def test_latest_version(self):
        """Latest version returns the newest."""
        registry = AutonomousSkillRegistry()
        registry.register("S1", "v1")
        registry.register("S1", "v2")
        latest = registry.get_latest("S1")
        assert latest is not None
        assert latest.version == 2

    def test_provenance_hash_unique(self):
        """Each version gets a unique provenance hash."""
        registry = AutonomousSkillRegistry()
        s1, _ = registry.register("S1", "v1")
        s2, _ = registry.register("S1", "v2")
        assert s1.provenance_hash != s2.provenance_hash

    def test_conflicts_tracked(self):
        """All conflicts are tracked for Triune review."""
        registry = AutonomousSkillRegistry()
        registry.register("A", "v1")
        registry.register("A", "v2")
        registry.register("B", "v1")
        registry.register("B", "v2")
        assert len(registry.get_conflicts()) == 2

    def test_list_skills(self):
        """All registered skill names are listable."""
        registry = AutonomousSkillRegistry()
        registry.register("A", "a")
        registry.register("B", "b")
        assert set(registry.list_skills()) == {"A", "B"}

    def test_unknown_skill_returns_none(self):
        """Unknown skill returns None."""
        registry = AutonomousSkillRegistry()
        assert registry.get_latest("NONEXISTENT") is None
