"""Tests for Attribution & License Compliance Engine (Story 4.1c)."""

from __future__ import annotations

from cohezion.vanguard.attribution import AttributionEngine, LicenseStatus
from cohezion.vanguard.source_connector import DiscoveryRecord


def _record(title: str = "Test Paper") -> DiscoveryRecord:
    return DiscoveryRecord(
        title=title,
        abstract="Abstract",
        source_url=f"https://arxiv.org/{title}",
        category="cs.LG",
        source_name="arxiv",
    )


class TestAttributionEngine:
    def test_mit_license_compatible(self):
        engine = AttributionEngine()
        attributed = engine.process(_record(), authors=["Alice"], license_type="MIT")
        assert attributed.attribution.status == LicenseStatus.COMPATIBLE
        assert not attributed.quarantined

    def test_gpl_license_quarantined(self):
        engine = AttributionEngine()
        attributed = engine.process(_record(), authors=["Bob"], license_type="GPL-3.0")
        assert attributed.attribution.status == LicenseStatus.INCOMPATIBLE
        assert attributed.quarantined
        assert "GPL" in attributed.quarantine_reason

    def test_unknown_license_flagged_for_review(self):
        engine = AttributionEngine()
        attributed = engine.process(
            _record(), authors=["Carol"], license_type="custom-weird-license"
        )
        assert attributed.attribution.status == LicenseStatus.UNKNOWN
        assert attributed.attribution.flagged_for_review is True

    def test_quarantine_count_tracked(self):
        engine = AttributionEngine()
        engine.process(_record("p1"), authors=["Alice"], license_type="GPL-3.0")
        engine.process(_record("p2"), authors=["Bob"], license_type="proprietary")
        assert engine.quarantine_count() == 2

    def test_content_hash_immutable(self):
        engine = AttributionEngine()
        record = _record("same-paper")
        a1 = engine.process(record, ["Alice"], "MIT")
        a2 = engine.process(record, ["Alice"], "MIT")
        assert a1.attribution.content_hash == a2.attribution.content_hash

    def test_quarantined_records_visible(self):
        engine = AttributionEngine()
        engine.process(_record("gpl-paper"), ["X"], "GPL-2.0")
        quarantined = engine.quarantined_records()
        assert len(quarantined) == 1
        assert "gpl-paper" in quarantined[0]["title"]
