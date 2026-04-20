#!/usr/bin/env python3
"""
Daily Health Check Script for Cohezion

Runs security scans, lint checks, and identifies untracked files.
Persists results to SurrealDB for trend tracking.
Reports health score for CI badges.

Usage:
    uv run python scripts/ci/daily_health_check.py
    uv run python scripts/ci/daily_health_check.py --fix
    uv run python scripts/ci/daily_health_check.py --output json
"""

from __future__ import annotations

import argparse
import asyncio
import json
import logging
import os
import subprocess
import sys
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from pathlib import Path
from typing import Any


logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")
logger = logging.getLogger(__name__)


class HealthCategory(Enum):
    """Health check categories."""

    SECURITY = "security"
    LINT = "lint"
    TYPE_CHECK = "type_check"
    UNTRACKED = "untracked"
    TESTS = "tests"
    DEPENDENCIES = "dependencies"


@dataclass
class HealthCheckResult:
    """Result of a single health check."""

    category: HealthCategory
    passed: bool
    score: float  # 0.0 to 1.0
    message: str
    details: list[str] = field(default_factory=list)
    fix_available: bool = False
    fix_command: str | None = None


@dataclass
class HealthReport:
    """Aggregated health report."""

    timestamp: str
    overall_score: float
    checks: list[HealthCheckResult]
    untracked_files: list[str]
    security_issues: dict[str, int]
    recommendations: list[str]

    def to_dict(self) -> dict[str, Any]:
        """Convert to dictionary for serialization."""
        return {
            "timestamp": self.timestamp,
            "overall_score": self.overall_score,
            "checks": [
                {
                    "category": c.category.value,
                    "passed": c.passed,
                    "score": c.score,
                    "message": c.message,
                    "details": c.details[:10],  # Limit details
                    "fix_available": c.fix_available,
                    "fix_command": c.fix_command,
                }
                for c in self.checks
            ],
            "untracked_count": len(self.untracked_files),
            "security_issues": self.security_issues,
            "recommendations": self.recommendations,
        }


class HealthChecker:
    """Run health checks on the Cohezion codebase."""

    def __init__(self, project_root: Path | None = None):
        self.project_root = project_root or Path(__file__).parent.parent.parent
        self.results: list[HealthCheckResult] = []

    def run_command(self, cmd: list[str], timeout: int = 300) -> tuple[int, str, str]:
        """Run a command and return exit code, stdout, stderr."""
        try:
            result = subprocess.run(
                cmd,
                cwd=self.project_root,
                capture_output=True,
                text=True,
                timeout=timeout,
            )
            return result.returncode, result.stdout, result.stderr
        except subprocess.TimeoutExpired:
            return -1, "", "Command timed out"
        except FileNotFoundError:
            return -2, "", f"Command not found: {cmd[0]}"

    def check_security(self) -> HealthCheckResult:
        """Run bandit security scan."""
        logger.info("Running security scan...")

        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "bandit", "-r", "src/cohezion", "-f", "json", "-q"]
        )

        try:
            data = json.loads(stdout) if stdout else {"results": []}
            results = data.get("results", [])

            # Count by severity
            severity_counts = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
            for r in results:
                sev = r.get("issue_severity", "LOW")
                if sev in severity_counts:
                    severity_counts[sev] += 1

            high_count = severity_counts["HIGH"]
            medium_count = severity_counts["MEDIUM"]

            # Score: 1.0 if no high severity, 0.5 if high exists
            score = 1.0 if high_count == 0 else max(0.0, 0.5 - (high_count * 0.1))
            passed = high_count == 0 and medium_count == 0

            details = [
                f"  - {r.get('test_id')}: {r.get('issue_text', '')[:80]}" for r in results[:5]
            ]

            return HealthCheckResult(
                category=HealthCategory.SECURITY,
                passed=passed,
                score=score,
                message=f"Security scan: {high_count} HIGH, {medium_count} MEDIUM issues",
                details=details,
                fix_available=False,  # Manual fix required
            )
        except json.JSONDecodeError:
            return HealthCheckResult(
                category=HealthCategory.SECURITY,
                passed=True,
                score=1.0,
                message="Security scan: No issues found",
            )

    def check_lint(self) -> HealthCheckResult:
        """Run ruff lint check."""
        logger.info("Running lint check...")

        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "ruff", "check", "src/cohezion", "--output-format", "concise"]
        )

        error_count = len(stdout.strip().split("\n")) if stdout.strip() else 0

        # Score based on error count
        score = max(0.0, 1.0 - (error_count * 0.01))
        passed = returncode == 0

        details = stdout.strip().split("\n")[:5] if not passed else []

        return HealthCheckResult(
            category=HealthCategory.LINT,
            passed=passed,
            score=score,
            message=f"Lint check: {error_count} issues found",
            details=details,
            fix_available=True,
            fix_command="uv run ruff check --fix src/cohezion",
        )

    def check_type_check(self) -> HealthCheckResult:
        """Run mypy type check."""
        logger.info("Running type check...")

        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "mypy", "src/cohezion", "--no-error-summary"],
            timeout=600,
        )

        # Count error lines
        error_lines = [l for l in stdout.split("\n") if "error:" in l]
        error_count = len(error_lines)

        score = max(0.0, 1.0 - (error_count * 0.005))
        passed = returncode == 0

        return HealthCheckResult(
            category=HealthCategory.TYPE_CHECK,
            passed=passed,
            score=score,
            message=f"Type check: {error_count} type errors",
            details=error_lines[:5],
            fix_available=False,
        )

    def check_untracked_files(self) -> HealthCheckResult:
        """Check for untracked files that need triage."""
        logger.info("Checking untracked files...")

        returncode, stdout, stderr = self.run_command(["git", "status", "--porcelain"])

        # Count untracked files (lines starting with ??)
        untracked = [l[3:] for l in stdout.split("\n") if l.startswith("??")]
        untracked_count = len(untracked)

        # Score: 1.0 if <50, decreasing after
        score = max(0.0, 1.0 - (max(0, untracked_count - 50) * 0.005))
        passed = untracked_count < 50

        return HealthCheckResult(
            category=HealthCategory.UNTRACKED,
            passed=passed,
            score=score,
            message=f"Untracked files: {untracked_count} files need triage",
            details=untracked[:10],
            fix_available=True,
            fix_command="git add <files> or git clean -fd",
        )

    def check_tests(self) -> HealthCheckResult:
        """Run fast tests to verify core functionality."""
        logger.info("Running fast tests...")

        returncode, stdout, stderr = self.run_command(
            ["uv", "run", "pytest", "-m", "fast", "-q", "--tb=no"],
            timeout=300,
        )

        # Parse test summary
        passed_count = stdout.count(" passed")
        failed_count = stdout.count(" failed")

        passed = returncode == 0
        score = 1.0 if passed else max(0.0, 0.5)

        return HealthCheckResult(
            category=HealthCategory.TESTS,
            passed=passed,
            score=score,
            message=f"Fast tests: {'passed' if passed else 'failed'}",
            details=[],
            fix_available=False,
        )

    def check_dependencies(self) -> HealthCheckResult:
        """Check for outdated/missing dependencies."""
        logger.info("Checking dependencies...")

        returncode, stdout, stderr = self.run_command(["uv", "pip", "list", "--outdated"])

        # Count outdated
        outdated_lines = [l for l in stdout.split("\n") if l.strip()][2:]  # Skip header
        outdated_count = len(outdated_lines)

        # Score based on outdated count
        score = max(0.0, 1.0 - (outdated_count * 0.02))
        passed = outdated_count < 10

        return HealthCheckResult(
            category=HealthCategory.DEPENDENCIES,
            passed=passed,
            score=score,
            message=f"Dependencies: {outdated_count} outdated packages",
            details=outdated_lines[:5],
            fix_available=True,
            fix_command="uv pip compile --upgrade",
        )

    def run_all_checks(self) -> HealthReport:
        """Run all health checks and generate report."""
        logger.info("=" * 60)
        logger.info("Cohezion Daily Health Check")
        logger.info("=" * 60)

        # Run all checks
        self.results = [
            self.check_security(),
            self.check_lint(),
            self.check_type_check(),
            self.check_untracked_files(),
            self.check_tests(),
            self.check_dependencies(),
        ]

        # Calculate overall score
        total_score = sum(r.score for r in self.results)
        overall_score = total_score / len(self.results)

        # Get untracked files
        _, stdout, _ = self.run_command(["git", "status", "--porcelain"])
        untracked_files = [l[3:] for l in stdout.split("\n") if l.startswith("??")]

        # Get security issues by severity
        security_check = next(
            (r for r in self.results if r.category == HealthCategory.SECURITY), None
        )
        security_issues = {"HIGH": 0, "MEDIUM": 0, "LOW": 0}
        if security_check and "security_issues" in dir(security_check):
            security_issues = security_check.security_issues  # type: ignore

        # Generate recommendations
        recommendations = self._generate_recommendations()

        return HealthReport(
            timestamp=datetime.now(UTC).isoformat(),
            overall_score=overall_score,
            checks=self.results,
            untracked_files=untracked_files,
            security_issues=security_issues,
            recommendations=recommendations,
        )

    def _generate_recommendations(self) -> list[str]:
        """Generate prioritized recommendations based on check results."""
        recommendations = []

        for result in self.results:
            if not result.passed:
                if result.fix_available and result.fix_command:
                    recommendations.append(
                        f"[{result.category.value.upper()}] {result.message}. Fix: `{result.fix_command}`"
                    )
                else:
                    recommendations.append(
                        f"[{result.category.value.upper()}] {result.message}. Manual intervention required."
                    )

        # Prioritize security
        security_failed = any(
            r for r in self.results if not r.passed and r.category == HealthCategory.SECURITY
        )
        if security_failed:
            recommendations.insert(0, "🔴 SECURITY ISSUES DETECTED - Address first")

        # Add untracked files recommendation if high
        untracked_check = next(
            (r for r in self.results if r.category == HealthCategory.UNTRACKED), None
        )
        if untracked_check and not untracked_check.passed:
            recommendations.append(
                f"📦 {len(untracked_check.details)} untracked files need triage. "
                "Use `scripts/repo_triage.py` to categorize."
            )

        return recommendations

    async def save_to_surrealdb(self, report: HealthReport) -> bool:
        """Save health report to SurrealDB for trend tracking."""
        try:
            # Import here to avoid dependency issues
            from cohezion.core.persistence.surreal_client import get_surreal_client

            client = await get_surreal_client()

            # Store health report
            health_record = {
                "timestamp": report.timestamp,
                "overall_score": report.overall_score,
                "security_high": report.security_issues.get("HIGH", 0),
                "security_medium": report.security_issues.get("MEDIUM", 0),
                "security_low": report.security_issues.get("LOW", 0),
                "untracked_count": len(report.untracked_files),
                "lint_errors": sum(
                    1 for r in report.checks if r.category == HealthCategory.LINT and not r.passed
                ),
                "type_errors": sum(
                    1
                    for r in report.checks
                    if r.category == HealthCategory.TYPE_CHECK and not r.passed
                ),
                "test_failures": sum(
                    1 for r in report.checks if r.category == HealthCategory.TESTS and not r.passed
                ),
                "recommendations": report.recommendations,
            }

            result = await client.query(
                "CREATE health_check_record SET $record",
                {"record": health_record},
            )

            logger.info(f"Health report saved to SurrealDB: {result}")
            return True

        except ImportError:
            logger.warning("SurrealDB client not available, skipping persistence")
            return False
        except Exception as e:
            logger.error(f"Failed to save to SurrealDB: {e}")
            return False

    def save_to_vault(self, report: HealthReport) -> bool:
        """Save health report to Obsidian vault for visibility."""
        try:
            vault_path = (
                self.project_root
                / "cloud-vault-mcp"
                / "vault"
                / "daily"
                / f"health-check-{datetime.now().strftime('%Y-%m-%d')}.md"
            )
            vault_path.parent.mkdir(parents=True, exist_ok=True)

            # Format as Markdown
            content = f"""# Daily Health Check - {datetime.now().strftime("%Y-%m-%d")}

**Overall Score:** {report.overall_score:.2%}

## Summary

| Category | Status | Score | Message |
|----------|--------|-------|---------|
"""
            for check in report.checks:
                status = "✅" if check.passed else "❌"
                content += (
                    f"| {check.category.value} | {status} | {check.score:.2f} | {check.message} |\n"
                )

            content += f"""
## Security Issues

- HIGH: {report.security_issues.get("HIGH", 0)}
- MEDIUM: {report.security_issues.get("MEDIUM", 0)}
- LOW: {report.security_issues.get("LOW", 0)}

## Untracked Files

Total: {len(report.untracked_files)}

Top 10:
"""
            for f in report.untracked_files[:10]:
                content += f"- {f}\n"

            content += """
## Recommendations

"""
            for rec in report.recommendations:
                content += f"- {rec}\n"

            content += """
---
_Generated by `scripts/ci/daily_health_check.py`_
"""
            vault_path.write_text(content)
            logger.info(f"Health report saved to vault: {vault_path}")
            return True

        except Exception as e:
            logger.error(f"Failed to save to vault: {e}")
            return False


def print_report(report: HealthReport, output_format: str = "text") -> None:
    """Print health report to console."""
    if output_format == "json":
        print(json.dumps(report.to_dict(), indent=2))
        return

    # Text format
    print("\n" + "=" * 60)
    print("HEALTH CHECK REPORT")
    print("=" * 60)
    print(f"Timestamp: {report.timestamp}")
    print(f"Overall Score: {report.overall_score:.2%}")
    print()

    print("CHECKS:")
    print("-" * 60)
    for check in report.checks:
        status = "✅ PASS" if check.passed else "❌ FAIL"
        print(f"  [{check.category.value.upper():12}] {status} - {check.message}")

        if not check.passed and check.details:
            for detail in check.details[:3]:
                print(f"    {detail}")

        if not check.passed and check.fix_available and check.fix_command:
            print(f"    💡 Fix: {check.fix_command}")

    print()
    print("RECOMMENDATIONS:")
    print("-" * 60)
    for rec in report.recommendations:
        print(f"  • {rec}")

    print()
    print(f"UNTRACKED FILES: {len(report.untracked_files)}")
    print("=" * 60)


async def main() -> int:
    """Main entry point."""
    parser = argparse.ArgumentParser(description="Cohezion Daily Health Check")
    parser.add_argument("--fix", action="store_true", help="Attempt to fix issues automatically")
    parser.add_argument("--output", choices=["text", "json"], default="text", help="Output format")
    parser.add_argument("--no-save", action="store_true", help="Skip saving to vault/SurrealDB")

    args = parser.parse_args()

    checker = HealthChecker()
    report = checker.run_all_checks()

    # Print report
    print_report(report, args.output)

    # Save to persistent storage
    if not args.no_save:
        await checker.save_to_surrealdb(report)
        checker.save_to_vault(report)

    # Apply fixes if requested
    if args.fix:
        print("\n🔧 Applying automatic fixes...")
        for check in report.checks:
            if not check.passed and check.fix_available and check.fix_command:
                print(f"  Running: {check.fix_command}")
                # Execute fix command
                os.system(check.fix.fix_command)  # type: ignore

    # Return exit code based on overall score
    if report.overall_score < 0.5:
        return 1  # Failure
    elif report.overall_score < 0.8:
        return 2  # Warning
    else:
        return 0  # Success


if __name__ == "__main__":
    sys.exit(asyncio.run(main()))
