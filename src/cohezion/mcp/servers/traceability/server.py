#!/usr/bin/env python3
# long lines: SQL/URLs/docstrings — wrapping reduces readability
"""Traceability MCP Server - Autonomous repo health monitoring via MCP protocol.

Usage:
    uv run python -m cohezion.mcp.servers.traceability.server

Ports:
    - 8362: Traceability MCP Server (HTTP/SSE)

Environment:
    - MCP_API_KEY: Authentication key (required)
    - MCP_PORT: Server port (default: 8362)
    - PROJECT_ROOT: Project root path (default: /home/mike-anderson/dev/cohezion)

Tools:
    1. traceability_run_engine - Execute traceability extraction
    2. traceability_run_health - Run health check
    3. traceability_trigger_party - Trigger party review
    4. traceability_get_dashboard - Get health dashboard
    5. traceability_get_findings - Get recent findings
    6. traceability_auto_commit - Commit improvements
"""

from __future__ import annotations

import os
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any

from mcp import Server


# Configuration
MCP_PORT = int(os.environ.get("MCP_PORT", "8362"))
PROJECT_ROOT = Path(os.environ.get("PROJECT_ROOT", "/home/mike-anderson/dev/cohezion"))
TRACEABILITY_DIR = PROJECT_ROOT / "_bmad" / "_config" / "traceability"

# Resolve external executable paths at module load to avoid S607 partial-path warnings.
_UV = shutil.which("uv") or "/usr/local/bin/uv"
_GIT = shutil.which("git") or "/usr/bin/git"

# Create server
app = Server("traceability")


# ============================================================================
# TOOLS (6 MCP tools for AI agent access)
# ============================================================================


@app.tool()
def traceability_run_engine(self_trace: bool = False) -> dict[str, Any]:
    """Execute traceability extraction engine.

    Args:
        self_trace: Whether to trace traceability/ directory itself

    Returns:
        Dict with returncode, stdout, stderr, and matrix counts
    """
    args = [_UV, "run", "python", str(TRACEABILITY_DIR / "traceability_engine.py")]
    if self_trace:
        args.append("--self-trace")

    result = subprocess.run(args, capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=300)

    # Parse matrix counts from output
    matrices = {}
    for line in result.stdout.split("\n"):
        if "Generated matrices:" in line:
            break
        if "agent_workflow:" in line:
            matrices["agent_workflow"] = True
        if "workflow_task:" in line:
            matrices["workflow_task"] = True
        if "workflow_chain:" in line:
            matrices["workflow_chain"] = True
        if "party_module:" in line:
            matrices["party_module"] = True

    return {
        "returncode": result.returncode,
        "stdout": result.stdout,
        "stderr": result.stderr,
        "matrices_generated": len(matrices),
        "self_trace": self_trace,
    }


@app.tool()
def traceability_run_health() -> dict[str, Any]:
    """Run repository health check.

    Returns:
        Dict with health score, category breakdown, and findings
    """
    result = subprocess.run(
        [_UV, "run", "python", str(TRACEABILITY_DIR / "repo_health" / "repo_health_engine.py")],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=300,
    )

    # Parse health score from output
    score = 0.0
    for line in result.stdout.split("\n"):
        if "Overall Health Score:" in line:
            score = float(line.split(":")[1].strip().split("/")[0])

    return {
        "returncode": result.returncode,
        "health_score": score,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@app.tool()
def traceability_trigger_party() -> dict[str, Any]:
    """Trigger party-mode adversarial review.

    Returns:
        Dict with findings count and severity breakdown
    """
    result = subprocess.run(
        [_UV, "run", "python", str(TRACEABILITY_DIR / "workflows" / "run_party_review.py")],
        capture_output=True,
        text=True,
        cwd=PROJECT_ROOT,
        timeout=600,
    )

    # Parse findings from output
    findings_count = 0
    high_count = 0
    for line in result.stdout.split("\n"):
        if "Collected" in line and "findings" in line:
            findings_count = int(line.split("Collected")[1].strip().split()[0])
        if "HIGH findings:" in line:
            high_count = int(line.split(":")[1].strip())

    return {
        "returncode": result.returncode,
        "findings_count": findings_count,
        "high_findings": high_count,
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


@app.tool()
def traceability_get_dashboard() -> str:
    """Get health dashboard as HTML.

    Returns:
        HTML dashboard string
    """
    dashboard_path = TRACEABILITY_DIR / "dashboard.html"

    if dashboard_path.exists():
        return dashboard_path.read_text(encoding="utf-8")
    else:
        # Generate minimal dashboard
        health_result = traceability_run_health()
        score = health_result.get("health_score", 0.0)

        html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Autonomous Traceability Dashboard</title>
    <meta http-equiv="refresh" content="300">
</head>
<body>
    <h1>Repo Health: {score}/100</h1>
    <p>Dashboard auto-refreshes every 5 minutes</p>
    <p>Last check: {datetime.now().isoformat()}</p>
</body>
</html>"""
        return html


@app.tool()
def traceability_get_findings() -> dict[str, Any]:
    """Get recent adversarial review findings.

    Returns:
        Dict with findings categorized by severity
    """
    findings_path = TRACEABILITY_DIR / "workflows" / "PARTY_REVIEW_FINDINGS.md"

    if findings_path.exists():
        content = findings_path.read_text(encoding="utf-8")

        # Parse findings
        high = []
        medium = []
        low = []

        for line in content.split("\n"):
            if "**Severity**: HIGH" in line:
                high.append(line)
            elif "**Severity**: MEDIUM" in line:
                medium.append(line)
            elif "**Severity**: LOW" in line:
                low.append(line)

        return {
            "high_count": len(high),
            "medium_count": len(medium),
            "low_count": len(low),
            "findings_file": str(findings_path),
        }
    else:
        return {
            "high_count": 0,
            "medium_count": 0,
            "low_count": 0,
            "findings_file": None,
        }


@app.tool()
def traceability_auto_commit(
    message: str = "Auto-commit traceability improvements",
) -> dict[str, Any]:
    """Auto-commit traceability improvements.

    Args:
        message: Commit message

    Returns:
        Dict with commit hash and status
    """
    # Stage changes
    subprocess.run(
        [_GIT, "add", "_bmad/_config/traceability/"], cwd=PROJECT_ROOT, capture_output=True
    )

    # Commit
    result = subprocess.run(
        [_GIT, "commit", "-m", message], capture_output=True, text=True, cwd=PROJECT_ROOT
    )

    # Get commit hash
    hash_result = subprocess.run(
        [_GIT, "rev-parse", "HEAD"], capture_output=True, text=True, cwd=PROJECT_ROOT
    )

    return {
        "success": result.returncode == 0,
        "commit_hash": hash_result.stdout.strip(),
        "stdout": result.stdout,
        "stderr": result.stderr,
    }


# ============================================================================
# RESOURCES
# ============================================================================


@app.resource("traceability://health")
async def get_health_resource() -> str:
    """Get current health score as resource."""
    result = traceability_run_health()
    return f"Health Score: {result['health_score']}/100"


@app.resource("traceability://findings")
async def get_findings_resource() -> str:
    """Get findings summary as resource."""
    result = traceability_get_findings()
    return f"Findings: HIGH={result['high_count']}, MEDIUM={result['medium_count']}, LOW={result['low_count']}"


# ============================================================================
# MAIN
# ============================================================================


def main():
    """Main entry point."""
    import asyncio
    import sys

    from mcp.server import stdio

    print(f"🔍 Traceability MCP Server starting on port {MCP_PORT}", file=sys.stderr)
    print(f"📁 Project root: {PROJECT_ROOT}", file=sys.stderr)
    print("📊 Tools: 6 (engine, health, party, dashboard, findings, commit)", file=sys.stderr)

    # Run server
    asyncio.run(stdio.run(app))


if __name__ == "__main__":
    main()
