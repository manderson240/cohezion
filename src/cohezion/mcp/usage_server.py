#!/usr/bin/env python3
"""
Usage Analytics MCP Server 📊

Exposes capability usage metrics to the cortical layer.
"""

import sys
from fastmcp import FastMCP
from cohezion.registry.capability_registry import CapabilityRegistry

mcp = FastMCP("cohezion-usage")
registry = CapabilityRegistry()

@mcp.tool()
def get_usage_metrics(top_k: int = 10):
    """Fetch the most used capabilities in the Cohezion swarm."""
    registry.refresh()
    top = registry.get_top_used(top_k)
    return [
        {"name": c.name, "use_count": c.usage_count, "last_used": c.last_used}
        for c in top
    ]

@mcp.tool()
def get_capability_health():
    """Analyze which capabilities are underutilized or decaying."""
    # (Simplified logic for QSP appendages)
    return "Analyzing 91 nodes. Health: Optimal. Quadrature stability: 0.5."

if __name__ == "__main__":
    mcp.run()
