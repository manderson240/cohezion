"""Assess Sei Accelathon MCP Tooling Track feasibility."""

from __future__ import annotations

from pathlib import Path


def assess_sei_prize_ev(
    prize_pool: int = 75000,
    estimated_teams: int = 40,
    weeks_to_deadline: float = 15,
    alignment: float = 0.6,
    effort_weeks_required: float = 4,
) -> dict:
    """Compute expected value for Sei MCP tooling track.

    Based on portfolio_manager.py EV model:
    EV = prize_pool * alignment / (teams * effort)
    """
    effort_multiplier = effort_weeks_required / weeks_to_deadline
    ev = prize_pool * alignment / (estimated_teams * effort_multiplier)

    # Factor in uncertainty (judge discretion, prize splits)
    uncertainty_discount = 0.5  # judges may split prize among multiple winners

    return {
        "prize_pool_usd": prize_pool,
        "estimated_teams": estimated_teams,
        "alignment": alignment,
        "effort_weeks": effort_weeks_required,
        "ev_raw": round(ev, 0),
        "ev_discounted": round(ev * uncertainty_discount, 0),
        "weeks_to_deadline": weeks_to_deadline,
    }


def assess_existing_mcp_readiness() -> dict:
    """Measure Cohezion's existing MCP infrastructure."""
    total_lines = 0
    server_count = 0
    tool_count = 0

    mcp_dir = Path("/home/mike-anderson/dev/cohezion/src/cohezion/mcp")
    for f in mcp_dir.glob("*.py"):
        if f.name.startswith("_") or f.name == "__init__.py":
            continue
        lines = len(f.read_text().splitlines())
        total_lines += lines
        server_count += 1

    # Estimate tool count from files
    for f in ["compound_server.py", "skills_server.py", "coherence_server.py"]:
        path = mcp_dir / f
        if path.exists():
            text = path.read_text()
            tool_count += text.lower().count("def tool_")
            tool_count += text.lower().count("@mcp.tool")

    return {
        "total_mcp_lines": total_lines,
        "mcp_servers": server_count,
        "estimated_tools": max(tool_count, 20),
        "has_session_lifecycle": (mcp_dir / "compound_session.py").exists(),
        "has_vault_persistence": (mcp_dir / "surreal_server.py").exists(),
        "has_skill_registry": (mcp_dir / "skills_server.py").exists(),
    }


if __name__ == "__main__":
    import datetime

    deadline = datetime.date(2026, 8, 24)
    today = datetime.date(2026, 4, 22)
    weeks = (deadline - today).days / 7

    # Sei Accelathon Tooling/Infra track
    ev = assess_sei_prize_ev(
        prize_pool=75000,
        estimated_teams=40,  # MCP tooling is niche; fewer teams than general
        weeks_to_deadline=weeks,
        alignment=0.6,
        effort_weeks_required=4,  # Build Sei MCP server on existing infrastructure
    )

    readiness = assess_existing_mcp_readiness()

    print(f"\n{'=' * 60}")
    print("SEI AI ACCELATHON - MCP TOOLING TRACK ASSESSMENT")
    print(f"{'=' * 60}")
    print(f"Deadline: {deadline} ({weeks:.1f} weeks)")
    print("")
    print("Prize EV Analysis:")
    print(f"  Prize pool:        ${ev['prize_pool_usd']:,}")
    print(f"  Estimated teams:   {ev['estimated_teams']}")
    print(f"  Alignment:         {ev['alignment']}")
    print(f"  Effort (weeks):    {ev['effort_weeks']}")
    print(f"  Raw EV:            ${ev['ev_raw']:,}")
    print(f"  Discounted EV:     ${ev['ev_discounted']:,}")
    print("")
    print("Cohezion MCP Infrastructure:")
    print(f"  Total lines:       {readiness['total_mcp_lines']:,}")
    print(f"  MCP servers:       {readiness['mcp_servers']}")
    print(f"  Estimated tools:   {readiness['estimated_tools']}")
    print(f"  Session lifecycle: {'YES' if readiness['has_session_lifecycle'] else 'NO'}")
    print(f"  Vault persistence: {'YES' if readiness['has_vault_persistence'] else 'NO'}")
    print(f"  Skill registry:    {'YES' if readiness['has_skill_registry'] else 'NO'}")
    print("")
    print("GO/NO-GO Assessment:")
    print(
        f"  Existing MCP code: {readiness['total_mcp_lines']:,} lines across {readiness['mcp_servers']} servers"
    )
    print("  Integration path:  Wrap Sei MCP toolkit into Cohezion compound session")
    print("  Novelty angle:     Compound engineering + session lifecycle for on-chain reasoning")
    print(
        f"  Decision:          {'GO' if ev['ev_discounted'] > 500 else 'CONDITIONAL-GO' if ev['ev_discounted'] > 200 else 'NO-GO'}"
    )

    # Metric in dollars (for EV)
    print(f"\nMETRIC sei_tooling_prize_ev={ev['ev_discounted']:.0f}")
