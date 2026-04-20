"""Tests for Compound Version Registry (Story 7.3)."""

from __future__ import annotations

from cohezion.registry.compound_version_registry import CompoundVersionRegistry


class TestCompoundVersionRegistry:
    def _registry_with_entry(self) -> CompoundVersionRegistry:
        reg = CompoundVersionRegistry()
        reg.record_release(
            version="1.1.0",
            previous_version="1.0.0",
            changelog_diff="+ feat: add HIHO governor",
            epic_ids=["epic-1"],
            story_ids=["1-3"],
            pr_number=35,
        )
        return reg

    def test_record_release_appends_entry(self):
        reg = CompoundVersionRegistry()
        entry = reg.record_release(
            version="1.0.1",
            previous_version="1.0.0",
            changelog_diff="+ fix: null check",
            epic_ids=["epic-7"],
            story_ids=["7-1"],
        )
        assert entry.version == "1.0.1"
        assert len(reg.all_entries()) == 1

    def test_query_by_epic_returns_matching(self):
        reg = self._registry_with_entry()
        reg.record_release("1.2.0", "1.1.0", "+ feat: x", ["epic-2"], ["2-1"])
        entries = reg.query_by_epic("epic-1")
        assert len(entries) == 1
        assert entries[0].version == "1.1.0"

    def test_rollback_context_retrieved_instantly(self):
        reg = self._registry_with_entry()
        entry = reg.get_rollback_context("1.1.0")
        assert entry is not None
        assert entry.version == "1.1.0"
        assert entry.pr_number == 35

    def test_rollback_context_missing_returns_none(self):
        reg = CompoundVersionRegistry()
        assert reg.get_rollback_context("99.0.0") is None

    def test_latest_version_returns_most_recent(self):
        reg = CompoundVersionRegistry()
        reg.record_release("1.0.0", "0.9.0", "init", [], [])
        reg.record_release("1.1.0", "1.0.0", "feat", [], [])
        assert reg.latest_version() == "1.1.0"

    def test_entries_serializable(self):
        reg = self._registry_with_entry()
        entries = reg.all_entries()
        assert "version" in entries[0]
        assert "epic_ids" in entries[0]
