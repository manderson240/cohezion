"""Tests for memory_gap_prioritizer — routing-frequency-weighted gap ranking (backlog item 129).

Covers: gap_score formula, sort order, alert threshold, coverage capping, and report formatting.
"""

from __future__ import annotations

import pytest

from cohezion.governance.memory_gap_prioritizer import (
    gap_report,
    prioritize_memory_gaps,
    _DEFAULT_TARGET_ENTRIES,
)


class TestPrioritizeMemoryGaps:
    def test_empty_returns_empty(self):
        assert prioritize_memory_gaps({}, {}) == []

    def test_gap_score_formula(self):
        # domain with frequency=0.5 and 0 entries → coverage=0 → score=0.5
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 50, "other": 50},
            vault_entry_counts={"code": 0},
            target_entries_per_domain=5,
        )
        code_gap = next(g for g in gaps if g.domain == "code")
        assert code_gap.routing_frequency == pytest.approx(0.5)
        assert code_gap.memory_coverage == pytest.approx(0.0)
        assert code_gap.gap_score == pytest.approx(0.5)

    def test_full_coverage_zero_gap(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 100},
            vault_entry_counts={"code": 5},  # == target_entries_per_domain default
        )
        code_gap = next(g for g in gaps if g.domain == "code")
        assert code_gap.memory_coverage == pytest.approx(1.0)
        assert code_gap.gap_score == pytest.approx(0.0)

    def test_coverage_capped_at_one(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 100},
            vault_entry_counts={"code": 100},  # far exceeds target
        )
        code_gap = next(g for g in gaps if g.domain == "code")
        assert code_gap.memory_coverage == pytest.approx(1.0)

    def test_sorted_by_gap_score_descending(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"high_freq": 80, "low_freq": 20},
            vault_entry_counts={"high_freq": 0, "low_freq": 0},
        )
        scores = [g.gap_score for g in gaps]
        assert scores == sorted(scores, reverse=True)

    def test_alert_triggers_at_threshold(self):
        # gap_score = routing_freq * (1 - coverage); need > 0.1
        # With 1 domain and 0 vault entries: gap_score = 1.0 * 1.0 = 1.0
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 100},
            vault_entry_counts={},
        )
        assert gaps[0].alert is True

    def test_no_alert_when_below_threshold(self):
        # routing_freq = 0.01, coverage = 0 → gap_score = 0.01 < 0.1
        routing = {f"domain{i}": 99 for i in range(100)}
        routing["sparse"] = 1
        gaps = prioritize_memory_gaps(routing_counts=routing, vault_entry_counts={})
        sparse_gap = next(g for g in gaps if g.domain == "sparse")
        assert sparse_gap.alert is False

    def test_domain_only_in_vault_counts_included(self):
        # Domains in vault_entry_counts but not routing_counts still appear
        gaps = prioritize_memory_gaps(
            routing_counts={},
            vault_entry_counts={"orphan_domain": 3},
        )
        domains = {g.domain for g in gaps}
        assert "orphan_domain" in domains

    def test_tie_broken_by_domain_name(self):
        # Two domains with identical gap_score → sorted by domain name
        gaps = prioritize_memory_gaps(
            routing_counts={"b_domain": 50, "a_domain": 50},
            vault_entry_counts={},
        )
        tied = [g for g in gaps if g.gap_score == gaps[0].gap_score]
        if len(tied) > 1:
            names = [g.domain for g in tied]
            assert names == sorted(names)


class TestGapReport:
    def test_report_contains_all_domains(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 60, "reason": 40},
            vault_entry_counts={"code": 2},
        )
        report = gap_report(gaps)
        assert "code" in report
        assert "reason" in report

    def test_report_contains_alert_section(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 100},
            vault_entry_counts={},
        )
        report = gap_report(gaps)
        assert "Recommended vault seeding" in report

    def test_report_no_alert_section_when_clean(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"code": 100},
            vault_entry_counts={"code": _DEFAULT_TARGET_ENTRIES},
        )
        report = gap_report(gaps)
        assert "Recommended vault seeding" not in report

    def test_report_header_includes_domain_count(self):
        gaps = prioritize_memory_gaps(
            routing_counts={"a": 50, "b": 50},
            vault_entry_counts={},
        )
        report = gap_report(gaps)
        assert "2 domains" in report
