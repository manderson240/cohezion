"""Tests for Vanguard Multi-Source Integration (Story 4.1b)."""

from __future__ import annotations

from cohezion.vanguard.connectors import (
    GitHubTrendingConnector,
    HuggingFaceConnector,
    OllamaConnector,
    RedditConnector,
    VanguardScout,
)
from cohezion.vanguard.source_connector import FailingConnector, SourceHealth


class TestMultiSourceConnectors:
    def test_all_connectors_return_records(self):
        for connector_cls in [
            HuggingFaceConnector,
            GitHubTrendingConnector,
            RedditConnector,
            OllamaConnector,
        ]:
            conn = connector_cls()
            records, health = conn.discover()
            assert len(records) >= 1
            assert health.status == SourceHealth.HEALTHY

    def test_vanguard_scout_aggregates_all_sources(self):
        scout = VanguardScout()
        records, report = scout.run_cycle()
        assert len(records) > 0
        assert report.total_discoveries > 0

    def test_failing_connector_does_not_block_cycle(self):
        """Single source failure should not block other connectors."""
        scout = VanguardScout(
            connectors=[
                HuggingFaceConnector(),
                FailingConnector(http_status=503),
                RedditConnector(),
            ]
        )
        records, report = scout.run_cycle()
        # Should still get records from HF and Reddit
        assert len(records) >= 2
        assert "failing_source" in report.per_source_counts

    def test_report_includes_per_source_counts(self):
        scout = VanguardScout()
        _, report = scout.run_cycle()
        assert len(report.per_source_counts) > 0

    def test_scout_report_serializable(self):
        scout = VanguardScout()
        _, report = scout.run_cycle()
        d = report.to_dict()
        assert "total_discoveries" in d
        assert "per_source_counts" in d
