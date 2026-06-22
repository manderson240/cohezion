"""Skills package — MCP tool modules and skill registry."""

import contextlib

# Wiring-sweep 2026-06-22: all 7 MCP tool modules were import-graph orphans.
with contextlib.suppress(Exception):
    from cohezion.skills.cohezion_mcp import CohezionMCP as CohezionMCP

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_paths import cohezion_root as cohezion_root
    from cohezion.skills.mcp_paths import skill_registry_path as skill_registry_path

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_tool_definitions import (
        build_tool_list as build_tool_list,
    )

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_inference_tools import (
        compound_engineering_orchestrator as compound_engineering_orchestrator,
    )

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_model_tools import (
        elite_model_selection as elite_model_selection,
    )

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_reliability_tools import (
        resolve_claims as resolve_claims,
    )

with contextlib.suppress(Exception):
    from cohezion.skills.mcp_skill_tools import execute_skill as execute_skill
