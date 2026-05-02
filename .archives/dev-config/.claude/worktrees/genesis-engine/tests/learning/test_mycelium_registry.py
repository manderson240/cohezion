"""Tests for Mycelium Registry — Skill Synthesis (Story 4.6, FR11)."""

from __future__ import annotations

from cohezion.learning.mycelium_registry import (
    JournalEntry,
    MyceliumRegistry,
)


class TestMyceliumRegistry:
    def test_ingest_entry(self):
        """Journal entries can be ingested."""
        registry = MyceliumRegistry()
        registry.ingest_entry(JournalEntry("e1", "Some learning", "pattern"))
        # No crash, internal state updated

    def test_audit_synthesizes_from_patterns(self):
        """Audit synthesizes skills when domain has enough entries."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "Pattern A", "pattern"))
        registry.ingest_entry(JournalEntry("e2", "Pattern B", "pattern"))
        report = registry.run_audit()
        assert report.skills_synthesized == 1
        assert "PATTERN_SYNTHESIZED" in registry.skills

    def test_insufficient_entries_no_synthesis(self):
        """Single entry doesn't trigger synthesis."""
        registry = MyceliumRegistry(min_entries_for_pattern=3)
        registry.ingest_entry(JournalEntry("e1", "Solo entry", "decision"))
        report = registry.run_audit()
        assert report.skills_synthesized == 0

    def test_synthesized_skill_has_content(self):
        """Synthesized skill contains content from entries."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "Learn X", "experiment"))
        registry.ingest_entry(JournalEntry("e2", "Learn Y", "experiment"))
        registry.run_audit()
        skill = registry.skills["EXPERIMENT_SYNTHESIZED"]
        assert "Learn X" in skill.skill_content
        assert "Learn Y" in skill.skill_content

    def test_update_existing_skill(self):
        """Updated entries update the synthesized skill."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "V1", "pattern"))
        registry.ingest_entry(JournalEntry("e2", "V2", "pattern"))
        registry.run_audit()
        # Add new entry and re-audit
        registry.ingest_entry(JournalEntry("e3", "V3", "pattern"))
        report = registry.run_audit()
        assert report.skills_updated == 1

    def test_audit_history(self):
        """Audit reports are accumulated."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "A", "pattern"))
        registry.ingest_entry(JournalEntry("e2", "B", "pattern"))
        registry.run_audit()
        registry.run_audit()
        assert len(registry.get_audit_history()) == 2

    def test_multiple_domains(self):
        """Different domains produce different skills."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "D1", "decision"))
        registry.ingest_entry(JournalEntry("e2", "D2", "decision"))
        registry.ingest_entry(JournalEntry("e3", "P1", "pattern"))
        registry.ingest_entry(JournalEntry("e4", "P2", "pattern"))
        report = registry.run_audit()
        assert report.skills_synthesized == 2

    def test_source_entries_tracked(self):
        """Synthesized skill tracks which entries contributed."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_entry(JournalEntry("e1", "A", "pattern"))
        registry.ingest_entry(JournalEntry("e2", "B", "pattern"))
        registry.run_audit()
        skill = registry.skills["PATTERN_SYNTHESIZED"]
        assert "e1" in skill.source_entries
        assert "e2" in skill.source_entries
