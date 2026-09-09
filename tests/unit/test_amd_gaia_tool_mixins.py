"""Unit tests for AMD GAIA SDK Tool Mixins architecture."""

from __future__ import annotations

import pytest

from cohezion.integrations.amd_gaia_tool_mixins import GaiaSovereignPhysicsAgent


@pytest.mark.asyncio
async def test_gaia_tool_registry_and_schema_generation() -> None:
    agent = GaiaSovereignPhysicsAgent()
    schemas = agent.get_tool_definitions()

    assert len(schemas) >= 2
    tool_names = [s["function"]["name"] for s in schemas]
    assert "quantize_metron_area" in tool_names
    assert "evaluate_enc_cluster" in tool_names


@pytest.mark.asyncio
async def test_gaia_tool_execution() -> None:
    agent = GaiaSovereignPhysicsAgent()

    # Execute quantize_metron_area
    res_metron = await agent.execute_tool("quantize_metron_area", {"area_m2": 1.845e-69})
    assert res_metron["discrete_metrons"] == 3

    # Execute evaluate_enc_cluster
    res_enc = await agent.execute_tool(
        "evaluate_enc_cluster",
        {"num_protons": 4, "num_electrons": 8, "current_density": 1e12},
    )
    assert res_enc["is_enc_triggered"] is True
