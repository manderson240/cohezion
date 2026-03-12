"""Tests for Constitutional Shielding & Auto-Incinerator (Story 4.3, NFR-10)."""

from __future__ import annotations

from cohezion.security.constitutional_shield import (
    AuditVerdict,
    ConstitutionalShield,
)


class TestConstitutionalShield:
    def test_safe_content_passes(self):
        """Normal code passes the Constitutional audit."""
        shield = ConstitutionalShield()
        record = shield.audit("def hello(): return 'world'")
        assert record.verdict == AuditVerdict.SAFE
        assert record.safety_score >= 0.7

    def test_unsafe_pattern_is_incinerated(self):
        """Code with unsafe patterns is permanently blacklisted."""
        shield = ConstitutionalShield()
        # Two unsafe patterns to guarantee score < 0.3
        record = shield.audit("rm -rf / --no-preserve-root; DROP TABLE users;")
        assert record.verdict == AuditVerdict.INCINERATED
        assert record.safety_score < 0.3

    def test_incinerated_content_is_blacklisted(self):
        """Once incinerated, the content hash is permanently blocked."""
        shield = ConstitutionalShield()
        content = "rm -rf / --no-preserve-root; DROP TABLE x;"
        shield.audit(content)
        assert shield.is_blacklisted(content)

    def test_blacklisted_content_rejected_on_retry(self):
        """Previously blacklisted content is immediately rejected."""
        shield = ConstitutionalShield()
        content = "__import__('os').system('bad'); DROP TABLE x;"
        shield.audit(content)
        # Second audit should return incinerated immediately
        record = shield.audit(content)
        assert record.verdict == AuditVerdict.INCINERATED
        assert "Previously blacklisted" in record.reasons

    def test_ambiguous_content_is_quarantined(self):
        """Borderline content is quarantined for Triune review."""
        shield = ConstitutionalShield(safe_threshold=0.9, unsafe_threshold=0.3)
        # Content with one minor pattern match -> score between 0.3 and 0.9
        record = shield.audit("DROP TABLE users;")
        assert record.verdict == AuditVerdict.QUARANTINED

    def test_quarantine_includes_audit_trace(self):
        """Quarantined records include reasons for human review."""
        shield = ConstitutionalShield(safe_threshold=0.9, unsafe_threshold=0.2)
        record = shield.audit("DROP TABLE users;")
        assert record.verdict == AuditVerdict.QUARANTINED
        assert len(shield.quarantine) == 1
        assert len(record.reasons) > 0

    def test_audit_log_tracks_all_audits(self):
        """Complete audit log maintained for observability."""
        shield = ConstitutionalShield()
        shield.audit("safe code")
        shield.audit("rm -rf / ; DROP TABLE x;")
        log = shield.get_audit_log()
        assert len(log) == 2

    def test_multiple_unsafe_patterns_compound(self):
        """Multiple unsafe patterns further reduce safety score."""
        shield = ConstitutionalShield()
        record = shield.audit("rm -rf /; DROP TABLE x; DELETE FROM y;")
        assert record.verdict == AuditVerdict.INCINERATED
        assert record.safety_score == 0.0  # Clamped at 0

    def test_empty_content_reduces_score(self):
        """Empty content gets a slight score reduction."""
        shield = ConstitutionalShield()
        record = shield.audit("")
        assert record.safety_score < 1.0
