"""Tests for Dependency Security Scanner (Story 7.2)."""

from __future__ import annotations

from cohezion.registry.dependency_scanner import DependencySecurityScanner, Severity


class TestDependencySecurityScanner:
    def _scanner_with_vuln(self) -> DependencySecurityScanner:
        scanner = DependencySecurityScanner()
        scanner.seed_vulnerability(
            package="requests",
            cve_id="CVE-2026-001",
            cvss_score=8.5,
            vulnerable_range="<2.32.0",
            fixed_version="2.32.0",
        )
        return scanner

    def test_detects_vulnerable_package(self):
        scanner = self._scanner_with_vuln()
        report = scanner.scan({"requests": "2.28.0"})
        assert len(report.alerts) == 1
        assert report.alerts[0].package == "requests"
        assert report.alerts[0].cve_id == "CVE-2026-001"

    def test_high_cvss_creates_pr(self):
        scanner = self._scanner_with_vuln()
        report = scanner.scan({"requests": "2.28.0"})
        assert report.prs_created == 1
        assert report.alerts[0].pr_created is True

    def test_severity_classified_correctly(self):
        scanner = DependencySecurityScanner()
        scanner.seed_vulnerability("pkg", "CVE-X", 9.5, "<1.0", "1.0")
        report = scanner.scan({"pkg": "0.9"})
        assert report.alerts[0].severity == Severity.CRITICAL

    def test_fixed_version_not_flagged(self):
        scanner = self._scanner_with_vuln()
        report = scanner.scan({"requests": "2.32.0"})
        assert len(report.alerts) == 0

    def test_remediation_included_in_alert(self):
        scanner = self._scanner_with_vuln()
        report = scanner.scan({"requests": "2.28.0"})
        assert "2.32.0" in report.alerts[0].remediation

    def test_scan_report_serializable(self):
        scanner = self._scanner_with_vuln()
        report = scanner.scan({"requests": "2.28.0"})
        d = report.to_dict()
        assert "alerts" in d
        assert "prs_created" in d

    def test_multiple_packages_scanned(self):
        scanner = DependencySecurityScanner()
        report = scanner.scan({"numpy": "1.24.0", "pandas": "2.0.0"})
        assert report.scanned_packages == 2
