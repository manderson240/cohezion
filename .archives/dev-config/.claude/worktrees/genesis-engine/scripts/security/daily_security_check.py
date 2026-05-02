#!/usr/bin/env python3
"""
Daily Security Check Script

Autonomous security monitoring for Cohezion.
Run daily via cron or manually to check security posture.

Usage:
    python scripts/security/daily_security_check.py

Environment:
    GITHUB_TOKEN - Required for GitHub API access
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


# Configuration
REPO_OWNER = "manderson240"
REPO_NAME = "cohezion"
ALERT_THRESHOLD_DAYS = 7


def load_config() -> dict[str, str]:
    """Load configuration from environment."""
    env_path = Path(__file__).parent.parent.parent / ".env"
    load_dotenv(env_path)

    token = os.getenv("GITHUB_TOKEN")
    if not token:
        print("❌ GITHUB_TOKEN not found in .env")
        sys.exit(1)

    return {"token": token}


def run_gh_command(args: list[str]) -> dict[str, Any] | list[Any]:
    """Run GitHub CLI command and parse JSON output."""
    result = subprocess.run(["gh", *args], capture_output=True, text=True)

    if result.returncode != 0:
        print(f"❌ GitHub CLI error: {result.stderr}")
        return {}

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError:
        return {}


def check_code_scanning_alerts() -> dict[str, Any]:
    """Check for open CodeQL alerts."""
    print("🔍 Checking CodeQL alerts...")

    alerts = run_gh_command(
        [
            "api",
            f"/repos/{REPO_OWNER}/{REPO_NAME}/code-scanning/alerts",
            "-X",
            "GET",
            "-f",
            "state=open",
        ]
    )

    if not isinstance(alerts, list):
        print("   ⚠️  Could not fetch CodeQL alerts")
        return {}

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    recent_alerts = []

    for alert in alerts:
        severity = alert.get("rule", {}).get("security_severity_level", "low")
        by_severity[severity] = by_severity.get(severity, 0) + 1

        # Check if alert is recent
        created = alert.get("created_at", "")
        if created:
            created_date = datetime.fromisoformat(created.replace("Z", "+00:00"))
            if datetime.now().astimezone() - created_date < timedelta(days=ALERT_THRESHOLD_DAYS):
                recent_alerts.append(alert)

    print(f"   ✅ Found {len(alerts)} open alerts")
    print(
        f"      Critical: {by_severity['critical']}, High: {by_severity['high']}, "
        f"Medium: {by_severity['medium']}, Low: {by_severity['low']}"
    )
    print(f"      🔔 {len(recent_alerts)} new alerts in last {ALERT_THRESHOLD_DAYS} days")

    return {"total": len(alerts), "by_severity": by_severity, "recent": recent_alerts}


def check_dependabot_alerts() -> dict[str, Any]:
    """Check for Dependabot alerts."""
    print("🔍 Checking Dependabot alerts...")

    alerts = run_gh_command(
        [
            "api",
            f"/repos/{REPO_OWNER}/{REPO_NAME}/dependabot/alerts",
            "-X",
            "GET",
            "-f",
            "state=open",
        ]
    )

    if not isinstance(alerts, list):
        print("   ⚠️  Could not fetch Dependabot alerts")
        return {}

    by_severity = {"critical": 0, "high": 0, "medium": 0, "low": 0}

    for alert in alerts:
        severity = alert.get("security_advisory", {}).get("severity", "low")
        by_severity[severity] = by_severity.get(severity, 0) + 1

    print(f"   ✅ Found {len(alerts)} open dependency alerts")
    print(
        f"      Critical: {by_severity['critical']}, High: {by_severity['high']}, "
        f"Medium: {by_severity['medium']}, Low: {by_severity['low']}"
    )

    return {"total": len(alerts), "by_severity": by_severity}


def check_workflow_status() -> dict[str, Any]:
    """Check recent workflow runs."""
    print("🔍 Checking recent workflow runs...")

    workflows = ["codeql.yml", "dependency-review.yml", "ci.yml"]
    status = {}

    for workflow in workflows:
        runs = run_gh_command(
            [
                "api",
                f"/repos/{REPO_OWNER}/{REPO_NAME}/actions/workflows/{workflow}/runs",
                "-X",
                "GET",
                "-f",
                "per_page=1",
            ]
        )

        if isinstance(runs, dict) and "workflow_runs" in runs:
            latest = runs["workflow_runs"][0]
            status[workflow] = {
                "conclusion": latest.get("conclusion"),
                "status": latest.get("status"),
                "created_at": latest.get("created_at"),
            }

            icon = "✅" if latest.get("conclusion") == "success" else "❌"
            print(f"   {icon} {workflow}: {latest.get('conclusion', 'unknown')}")

    return status


def check_dependabot_prs() -> dict[str, Any]:
    """Check for open Dependabot PRs."""
    print("🔍 Checking Dependabot PRs...")

    prs = run_gh_command(
        [
            "api",
            f"/repos/{REPO_OWNER}/{REPO_NAME}/pulls",
            "-X",
            "GET",
            "-f",
            "state=open",
            "-f",
            "per_page=100",
        ]
    )

    if not isinstance(prs, list):
        print("   ⚠️  Could not fetch PRs")
        return {}

    dependabot_prs = [pr for pr in prs if pr.get("user", {}).get("login") == "dependabot[bot]"]

    security_prs = [pr for pr in dependabot_prs if "security" in pr.get("title", "").lower()]

    print(f"   ✅ Found {len(dependabot_prs)} open Dependabot PRs")
    print(f"      🔒 {len(security_prs)} security-related")

    return {"total": len(dependabot_prs), "security": len(security_prs), "prs": dependabot_prs}


def generate_report(results: dict[str, Any]) -> str:
    """Generate markdown security report."""
    report = f"""# Daily Security Report

**Date**: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
**Repository**: {REPO_OWNER}/{REPO_NAME}

## Summary

| Category | Count | Status |
|----------|-------|--------|
| CodeQL Alerts | {results.get("codeql", {}).get("total", 0)} | {"🔴" if results.get("codeql", {}).get("by_severity", {}).get("critical", 0) > 0 else "🟢"} |
| Dependabot Alerts | {results.get("dependabot", {}).get("total", 0)} | {"🔴" if results.get("dependabot", {}).get("by_severity", {}).get("critical", 0) > 0 else "🟢"} |
| Dependabot PRs | {results.get("prs", {}).get("total", 0)} | {"🟡" if results.get("prs", {}).get("security", 0) > 0 else "🟢"} |

## CodeQL Alerts

"""

    codeql = results.get("codeql", {})
    if codeql.get("by_severity"):
        report += f"""
| Severity | Count |
|----------|-------|
| 🔴 Critical | {codeql["by_severity"].get("critical", 0)} |
| 🟠 High | {codeql["by_severity"].get("high", 0)} |
| 🟡 Medium | {codeql["by_severity"].get("medium", 0)} |
| 🔵 Low | {codeql["by_severity"].get("low", 0)} |

"""

    if codeql.get("recent"):
        report += "### New Alerts (Last 7 Days)\n\n"
        for alert in codeql["recent"][:5]:
            report += f"- **{alert.get('rule', {}).get('id', 'Unknown')}**: {alert.get('rule', {}).get('description', 'No description')}\n"

    report += f"""
## Dependabot Alerts

| Severity | Count |
|----------|-------|
| 🔴 Critical | {results.get("dependabot", {}).get("by_severity", {}).get("critical", 0)} |
| 🟠 High | {results.get("dependabot", {}).get("by_severity", {}).get("high", 0)} |
| 🟡 Medium | {results.get("dependabot", {}).get("by_severity", {}).get("medium", 0)} |
| 🔵 Low | {results.get("dependabot", {}).get("by_severity", {}).get("low", 0)} |

## Workflow Status

"""

    for workflow, status in results.get("workflows", {}).items():
        icon = "✅" if status.get("conclusion") == "success" else "❌"
        report += f"- {icon} **{workflow}**: {status.get('conclusion', 'unknown')}\n"

    report += """
## Recommendations

"""

    # Generate recommendations
    if codeql.get("by_severity", {}).get("critical", 0) > 0:
        report += "🔴 **CRITICAL**: Address CodeQL critical alerts immediately\n"
    if codeql.get("by_severity", {}).get("high", 0) > 0:
        report += "🟠 **HIGH**: Review and fix high severity CodeQL alerts\n"
    if results.get("dependabot", {}).get("by_severity", {}).get("critical", 0) > 0:
        report += "🔴 **CRITICAL**: Merge Dependabot security patches\n"
    if results.get("prs", {}).get("security", 0) > 0:
        report += "🔒 Review security-related Dependabot PRs\n"

    report += "\n---\n\n*Report generated by Cohezion Security Monitor*\n"

    return report


def main():
    """Run daily security check."""
    print("=" * 60)
    print("🔒 Cohezion Daily Security Check")
    print("=" * 60)
    print()

    load_config()

    results = {
        "codeql": check_code_scanning_alerts(),
        "dependabot": check_dependabot_alerts(),
        "workflows": check_workflow_status(),
        "prs": check_dependabot_prs(),
    }

    print()
    print("=" * 60)
    print("📊 Generating Report...")
    print("=" * 60)
    print()

    report = generate_report(results)
    print(report)

    # Save report
    report_dir = Path(__file__).parent.parent.parent / "reports" / "security"
    report_dir.mkdir(parents=True, exist_ok=True)

    report_file = report_dir / f"daily-security-{datetime.now().strftime('%Y-%m-%d')}.md"
    report_file.write_text(report)
    print(f"📄 Report saved to: {report_file}")

    # Critical alert check
    critical_count = results.get("codeql", {}).get("by_severity", {}).get("critical", 0) + results.get(
        "dependabot", {}
    ).get("by_severity", {}).get("critical", 0)

    if critical_count > 0:
        print()
        print("⚠️  CRITICAL ALERTS DETECTED - Immediate action required!")
        sys.exit(1)

    print()
    print("✅ Security check complete - No critical issues found")
    sys.exit(0)


if __name__ == "__main__":
    main()
