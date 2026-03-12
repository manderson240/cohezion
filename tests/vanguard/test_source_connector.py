"""Tests for Vanguard Source Connector Framework (Story 4.1)."""

from __future__ import annotations

from cohezion.vanguard.source_connector import (
    ARXIV_CATEGORIES,
    ArXivConnector,
    DiscoveryRecord,
    FailingConnector,
    SourceHealth,
)


class TestArXivConnector:
    def test_discover_returns_records_for_all_categories(self):
        conn = ArXivConnector()
        records, health = conn.discover()
        assert len(records) == len(ARXIV_CATEGORIES)
        assert health.status == SourceHealth.HEALTHY

    def test_records_have_required_fields(self):
        conn = ArXivConnector()
        records, _ = conn.discover()
        for r in records:
            assert r.title
            assert r.abstract
            assert r.source_url
            assert r.category
            assert r.source_name == "arxiv"

    def test_records_have_content_hash(self):
        conn = ArXivConnector()
        records, _ = conn.discover()
        for r in records:
            assert len(r.content_hash) == 16

    def test_source_name(self):
        assert ArXivConnector().source_name == "arxiv"


class TestFailingConnector:
    def test_returns_empty_records_on_failure(self):
        conn = FailingConnector(http_status=503)
        records, health = conn.discover()
        assert records == []
        assert health.status == SourceHealth.UNREACHABLE

    def test_health_report_includes_http_status(self):
        conn = FailingConnector(http_status=403)
        _, health = conn.discover()
        assert health.http_status == 403
        assert "403" in health.error_message

    def test_discovery_record_content_hash_deterministic(self):
        r1 = DiscoveryRecord("Title", "Abstract", "https://example.com", "cs.LG", "test")
        r2 = DiscoveryRecord("Title", "Abstract", "https://example.com", "cs.LG", "test")
        assert r1.content_hash == r2.content_hash
