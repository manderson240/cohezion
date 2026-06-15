"""Tests for Mycelium Registry — Skill Synthesis (Story 4.6, FR11)."""

from __future__ import annotations

from cohezion.learning.mycelium_registry import (
    HyperedgePattern,
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


class TestHyperedgePattern:
    """Discriminating tests for Hyper-Extract-inspired hyperedge tracking."""

    def test_ingest_new_hyperedge(self):
        """First ingest creates a new HyperedgePattern."""
        registry = MyceliumRegistry()
        result = registry.ingest_execution_trace(["Act", "Checker"], ["code"])
        assert isinstance(result, HyperedgePattern)
        assert set(result.nodes) == {"Act", "Checker"}
        assert result.relation == "co_produced"
        assert result.weight == 1.0
        assert len(registry.hyperedges) == 1

    def test_dedup_increments_weight(self):
        """Repeated identical trace increments weight instead of adding duplicate."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["Act", "Checker"], ["code"])
        registry.ingest_execution_trace(["Checker", "Act"], ["analysis"])  # order-invariant
        assert len(registry.hyperedges) == 1
        assert registry.hyperedges[0].weight == 2.0

    def test_different_relation_is_separate_hyperedge(self):
        """Same nodes with different relation = distinct hyperedge."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["Act", "Refiner"], relation="co_produced")
        registry.ingest_execution_trace(["Act", "Refiner"], relation="co_refined")
        assert len(registry.hyperedges) == 2

    def test_domain_accumulation_on_dedup(self):
        """Repeated trace from different domain appends domain to source_domains."""
        registry = MyceliumRegistry()
        registry.ingest_execution_trace(["Act", "Checker"], ["code"])
        registry.ingest_execution_trace(["Act", "Checker"], ["analysis"])
        pattern = registry.hyperedges[0]
        assert "code" in pattern.source_domains
        assert "analysis" in pattern.source_domains

    def test_audit_report_includes_hyperedge_count(self):
        """AuditReport.hyperedges_captured reflects current hyperedge count."""
        registry = MyceliumRegistry(min_entries_for_pattern=2)
        registry.ingest_execution_trace(["Step3", "Step3.5", "Step7"])
        registry.ingest_entry(JournalEntry("e1", "A", "pattern"))
        registry.ingest_entry(JournalEntry("e2", "B", "pattern"))
        report = registry.run_audit()
        assert report.hyperedges_captured == 1

    def test_n_ary_hyperedge_three_nodes(self):
        """Hyperedge correctly captures three-way co-participation."""
        registry = MyceliumRegistry()
        result = registry.ingest_execution_trace(
            ["execute_fn", "maker_checker", "skill_refiner"],
            ["reasoning"],
            relation="co_produced",
        )
        assert len(result.nodes) == 3
        assert "execute_fn" in result.nodes
