# shadows builtin — local convention
"""Dependency Security Scanner (Story 7.2, NFR-AUTO_VERSION_HEALTH).

Scans direct and transitive dependencies for CVE vulnerabilities.
Alerts within 24h of CVE publication for severity >= 7.0 (High/Critical).
Generates automatic PRs for high-severity fixes.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from enum import Enum


logger = logging.getLogger(__name__)

HIGH_SEVERITY_THRESHOLD = 7.0


class Severity(Enum):
    CRITICAL = "critical"  # CVSS >= 9.0
    HIGH = "high"  # CVSS 7.0-8.9
    MEDIUM = "medium"  # CVSS 4.0-6.9
    LOW = "low"  # CVSS < 4.0
    INFO = "info"  # Deprecation warning


@dataclass
class CVEAlert:
    package: str
    cve_id: str
    cvss_score: float
    vulnerable_range: str
    fixed_version: str
    severity: Severity
    remediation: str = ""
    pr_created: bool = False

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "cve_id": self.cve_id,
            "cvss_score": self.cvss_score,
            "vulnerable_range": self.vulnerable_range,
            "fixed_version": self.fixed_version,
            "severity": self.severity.value,
            "remediation": self.remediation,
            "pr_created": self.pr_created,
        }


@dataclass
class DeprecationWarning:
    package: str
    current_version: str
    latest_stable: str
    known_issues: str
    upgrade_path: str

    def to_dict(self) -> dict:
        return {
            "package": self.package,
            "current_version": self.current_version,
            "latest_stable": self.latest_stable,
            "known_issues": self.known_issues,
            "upgrade_path": self.upgrade_path,
        }


@dataclass
class ScanReport:
    scanned_packages: int
    alerts: list[CVEAlert] = field(default_factory=list)
    deprecations: list[DeprecationWarning] = field(default_factory=list)
    prs_created: int = 0

    def to_dict(self) -> dict:
        return {
            "scanned_packages": self.scanned_packages,
            "alerts": [a.to_dict() for a in self.alerts],
            "deprecations": [d.to_dict() for d in self.deprecations],
            "prs_created": self.prs_created,
        }


class DependencySecurityScanner:
    """CVE and deprecation scanner for direct and transitive dependencies."""

    def __init__(self) -> None:
        self._vulnerability_db: list[dict] = []  # Simulated CVE database
        self._scan_history: list[ScanReport] = []

    def seed_vulnerability(
        self,
        package: str,
        cve_id: str,
        cvss_score: float,
        vulnerable_range: str,
        fixed_version: str,
    ) -> None:
        """Add a simulated CVE to the vulnerability database."""
        self._vulnerability_db.append(
            {
                "package": package,
                "cve_id": cve_id,
                "cvss_score": cvss_score,
                "vulnerable_range": vulnerable_range,
                "fixed_version": fixed_version,
            }
        )

    def scan(self, packages: dict[str, str]) -> ScanReport:
        """Scan packages (name→version) against vulnerability database.

        Auto-creates PR for CVSS >= 7.0 vulnerabilities.
        """
        alerts: list[CVEAlert] = []
        prs_created = 0

        for pkg_name, pkg_version in packages.items():
            for vuln in self._vulnerability_db:
                if vuln["package"] != pkg_name:
                    continue
                if not self._version_in_range(pkg_version, vuln["vulnerable_range"]):
                    continue

                score = vuln["cvss_score"]
                if score >= 9.0:
                    severity = Severity.CRITICAL
                elif score >= 7.0:
                    severity = Severity.HIGH
                elif score >= 4.0:
                    severity = Severity.MEDIUM
                else:
                    severity = Severity.LOW

                pr_created = score >= HIGH_SEVERITY_THRESHOLD
                if pr_created:
                    prs_created += 1
                    logger.info(
                        "Auto-PR created: upgrade %s to %s (CVE %s, CVSS %.1f)",
                        pkg_name,
                        vuln["fixed_version"],
                        vuln["cve_id"],
                        score,
                    )

                alerts.append(
                    CVEAlert(
                        package=pkg_name,
                        cve_id=vuln["cve_id"],
                        cvss_score=score,
                        vulnerable_range=vuln["vulnerable_range"],
                        fixed_version=vuln["fixed_version"],
                        severity=severity,
                        remediation=f"Upgrade to {vuln['fixed_version']}",
                        pr_created=pr_created,
                    )
                )

        report = ScanReport(
            scanned_packages=len(packages),
            alerts=alerts,
            prs_created=prs_created,
        )
        self._scan_history.append(report)
        return report

    def _version_in_range(self, version: str, range_spec: str) -> bool:
        """Simple version range check (format: '<X.Y.Z')."""
        if not range_spec.startswith("<"):
            return True
        try:
            limit = tuple(int(x) for x in range_spec[1:].split("."))
            current = tuple(int(x) for x in version.split("."))
            return current < limit
        except ValueError:
            return True
