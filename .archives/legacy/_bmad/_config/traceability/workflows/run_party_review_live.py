#!/usr/bin/env python3
"""
Live Multi-Agent Adversarial Review Executor

Executes actual BMAD agents via MCP protocol:
1. Connects to BMAD MCP server (port 8361)
2. Invokes real agents (bmm-dev, bmm-qa, bmm-architect, tea)
3. Runs agents in parallel (asyncio.gather)
4. Consolidates findings with deduplication
5. Generates actionable report
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from pathlib import Path
from typing import Any


# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))

from cohezion.mcp.shared.client import MCPClient


# Agent configuration mapping - Use actual BMAD MCP tool names
AGENT_MAPPING = {
    "Amelia": {
        "mcp_tool": "bmad_bmm_code_review",
        "agent_id": "bmm-dev",
        "perspective": "Code quality, DRY violations, type safety, error handling",
        "icon": "💻",
        "role": "Developer",
    },
    "Quinn": {
        "mcp_tool": "bmad_help",
        "agent_id": "bmm-qa",
        "perspective": "Test quality, assertion strength, edge cases, coverage",
        "icon": "🧪",
        "role": "QA Engineer",
    },
    "Winston": {
        "mcp_tool": "bmad_help",
        "agent_id": "bmm-architect",
        "perspective": "System design, DI, modularity, extensibility",
        "icon": "🏗️",
        "role": "Architect",
    },
    "Murat": {
        "mcp_tool": "bmad_help",
        "agent_id": "tea",
        "perspective": "Test strategy, E2E, CI/CD, risk-based testing",
        "icon": "🧪",
        "role": "Test Architect",
    },
    "BMad Master": {
        "mcp_tool": "bmad_help",
        "agent_id": "bmad-master",
        "perspective": "Workflow compliance, step architecture, party-mode",
        "icon": "🧙",
        "role": "Workflow Orchestrator",
    },
}


async def invoke_agent(
    client: MCPClient,
    agent_name: str,
    agent_config: dict,
    target_files: list[str],
    timeout: int = 60,
) -> dict[str, Any]:
    """
    Invoke a single BMAD agent via MCP.

    Args:
        client: MCP client instance
        agent_name: Human-readable agent name
        agent_config: Agent configuration from AGENT_MAPPING
        target_files: List of files to review
        timeout: Request timeout in seconds

    Returns:
        Dict with agent findings or error
    """
    print(f"  {agent_config['icon']} {agent_name} analyzing...")

    try:
        # Prepare agent-specific parameters
        params = {
            "query": f"Review {target_files} for {agent_config['perspective']}",
            "context": f"Multi-agent adversarial code review",
            "session_id": f"party-review-{datetime.now().isoformat()}",
        }

        # Call MCP tool
        result = await client.call_tool(
            agent_config["mcp_tool"],
            params,
        )

        if "error" in result:
            print(f"    ⚠️  {agent_name} error: {result['error']}")
            return {
                "agent": agent_name,
                "status": "error",
                "error": result["error"],
                "findings": [],
            }

        print(f"    ✅ {agent_name} completed")
        return {
            "agent": agent_name,
            "status": "success",
            "findings": result.get("findings", []),
            "metrics": result.get("metrics", {}),
        }

    except asyncio.TimeoutError:
        print(f"    ⏱️  {agent_name} timed out")
        return {
            "agent": agent_name,
            "status": "timeout",
            "findings": [],
        }
    except Exception as e:
        print(f"    ❌ {agent_name} failed: {e}")
        return {
            "agent": agent_name,
            "status": "exception",
            "error": str(e),
            "findings": [],
        }


async def run_multi_agent_review(
    target_files: list[str],
    mcp_url: str = "http://localhost:8361",
) -> list[dict]:
    """
    Run multi-agent adversarial review in parallel.

    Args:
        target_files: List of files to review
        mcp_url: BMAD MCP server URL

    Returns:
        Consolidated findings from all agents
    """
    print(f"\n🎉 Starting multi-agent review ({len(target_files)} files)")
    print(f"🔗 Connecting to BMAD MCP server: {mcp_url}")

    # Initialize MCP client
    client = MCPClient(base_url=mcp_url)

    # Run all agents in parallel
    print(f"\n👥 Invoking {len(AGENT_MAPPING)} agents...")
    results = await asyncio.gather(
        *[
            invoke_agent(client, name, config, target_files)
            for name, config in AGENT_MAPPING.items()
        ],
        return_exceptions=True,
    )

    # Close client
    await client.close()

    # Consolidate findings
    all_findings = []
    for result in results:
        if isinstance(result, Exception):
            print(f"  ❌ Agent exception: {result}")
            continue

        if result.get("status") == "success":
            all_findings.extend(result.get("findings", []))
        elif result.get("status") == "error":
            print(f"  ⚠️  {result['agent']}: {result.get('error', 'Unknown error')}")

    print(f"\n✅ Collected {len(all_findings)} findings from {len(results)} agents")

    # Deduplicate and prioritize
    consolidated = consolidate_findings(all_findings)

    return consolidated


def consolidate_findings(findings: list[dict]) -> list[dict]:
    """
    Consolidate findings with deduplication and prioritization.

    Args:
        findings: Raw findings from all agents

    Returns:
        Deduplicated, prioritized findings
    """
    # Group by file + line + issue type
    finding_map = {}
    for finding in findings:
        key = (
            finding.get("file", ""),
            finding.get("line", ""),
            finding.get("category", ""),
        )
        if key not in finding_map:
            finding_map[key] = {
                **finding,
                "agents": [],
                "consensus_count": 0,
            }
        finding_map[key]["agents"].append(finding.get("agent", "unknown"))
        finding_map[key]["consensus_count"] += 1

    # Convert back to list
    consolidated = list(finding_map.values())

    # Prioritize by severity + consensus
    severity_order = {"HIGH": 0, "MEDIUM": 1, "LOW": 2}
    consolidated.sort(
        key=lambda f: (
            severity_order.get(f.get("severity", "LOW"), 2),
            -f.get("consensus_count", 0),  # Higher consensus first
        )
    )

    return consolidated


def generate_report(findings: list[dict]) -> str:
    """
    Generate consolidated findings report.

    Args:
        findings: Consolidated findings list

    Returns:
        Markdown report
    """
    report = []
    report.append("# Multi-Agent Adversarial Review Findings")
    report.append("")
    report.append(f"**Date**: {datetime.now().isoformat()}")
    report.append(f"**Agents**: {len(AGENT_MAPPING)} (BMAD MCP)")
    report.append(f"**Findings**: {len(findings)}")
    report.append("")

    # Summary by severity
    high_count = len([f for f in findings if f.get("severity") == "HIGH"])
    med_count = len([f for f in findings if f.get("severity") == "MEDIUM"])
    low_count = len([f for f in findings if f.get("severity") == "LOW"])

    report.append("## Summary")
    report.append("")
    report.append(f"- **HIGH**: {high_count} findings")
    report.append(f"- **MEDIUM**: {med_count} findings")
    report.append(f"- **LOW**: {low_count} findings")
    report.append("")

    # Group by agent consensus
    for i, finding in enumerate(findings[:20], 1):  # Limit to top 20
        agents = finding.get("agents", [])
        consensus = finding.get("consensus_count", 0)

        report.append(f"## {i}. {finding.get('finding', 'Unknown')}")
        report.append(f"- **Severity**: {finding.get('severity', 'UNKNOWN')}")
        report.append(f"- **File**: {finding.get('file', 'Unknown')}")
        report.append(f"- **Line**: {finding.get('line', 'N/A')}")
        report.append(f"- **Category**: {finding.get('category', 'Unknown')}")
        report.append(f"- **Fix**: {finding.get('fix', 'TBD')}")
        report.append(f"- **Agents**: {', '.join(agents)} ({consensus} found this)")
        report.append("")

    return "\n".join(report)


async def main():
    """Main entry point."""
    print("🎉 Multi-Agent Adversarial Review")
    print("=" * 60)

    # Target files (traceability engines)
    target_dir = Path(__file__).parent.parent
    target_files = [
        str(f.relative_to(Path("/home/mike-anderson/dev/cohezion")))
        for f in target_dir.glob("*.py")
    ]

    print(f"📁 Analyzing {len(target_files)} Python files:")
    for f in target_files[:5]:
        print(f"  - {f}")
    if len(target_files) > 5:
        print(f"  ... and {len(target_files) - 5} more")

    # Run multi-agent review
    findings = await run_multi_agent_review(target_files)

    # Generate report
    report = generate_report(findings)
    report_path = target_dir / "workflows" / "MULTI_AGENT_REVIEW_LIVE.md"
    report_path.write_text(report, encoding="utf-8")

    print(f"\n📄 Report written to: {report_path}")

    # Summary
    high_count = len([f for f in findings if f.get("severity") == "HIGH"])
    print(f"\n📊 Summary:")
    print(f"  HIGH findings: {high_count}")
    print(f"  Total findings: {len(findings)}")

    if high_count > 0:
        print(f"\n⚠️  {high_count} HIGH priority findings require attention")
    else:
        print("\n✅ No HIGH priority findings")

    print("\n🎯 Multi-agent review complete!")


if __name__ == "__main__":
    asyncio.run(main())
