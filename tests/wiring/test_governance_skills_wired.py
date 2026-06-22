"""Wiring identity tests: governance/ and skills/ orphan modules.

Discriminating: each test verifies the re-exported name IS the original class/function
(not a shadow), and that a basic behavioral call succeeds.
"""

import cohezion.governance as pkg_gov
import cohezion.skills as pkg_skills


# ── governance: autonomy_engine ──────────────────────────────────────────────


def test_autonomy_tier_wired():
    from cohezion.governance.autonomy_engine import AutonomyTier as src

    assert pkg_gov.AutonomyTier is src


def test_agent_autonomy_state_wired():
    from cohezion.governance.autonomy_engine import AgentAutonomyState as src

    assert pkg_gov.AgentAutonomyState is src


# ── governance: fleet_monitor ────────────────────────────────────────────────


def test_fleet_monitor_wired():
    from cohezion.governance.fleet_monitor import FleetMonitor as src

    assert pkg_gov.FleetMonitor is src


def test_fleet_monitor_instantiable():
    fm = pkg_gov.FleetMonitor()
    assert fm is not None


# ── governance: guardian ─────────────────────────────────────────────────────


def test_guardian_registry_wired():
    from cohezion.governance.guardian import GuardianRegistry as src

    assert pkg_gov.GuardianRegistry is src


# ── governance: knowledge_bridge ─────────────────────────────────────────────


def test_learning_wired():
    from cohezion.governance.knowledge_bridge import Learning as src

    assert pkg_gov.Learning is src


def test_persist_to_vault_wired():
    from cohezion.governance.knowledge_bridge import persist_to_vault as src

    assert pkg_gov.persist_to_vault is src


# ── governance: quadrature_nexus ─────────────────────────────────────────────


def test_quadrature_nexus_wired():
    from cohezion.governance.quadrature_nexus import QuadratureNexus as src

    assert pkg_gov.QuadratureNexus is src


# ── governance: flume_bridge ─────────────────────────────────────────────────


def test_encode_prompt_wired():
    from cohezion.governance.flume_bridge import encode_prompt as src

    assert pkg_gov.encode_prompt is src


def test_data_product_similarity_wired():
    from cohezion.governance.flume_bridge import data_product_similarity as src

    assert pkg_gov.data_product_similarity is src


# ── skills: cohezion_mcp ─────────────────────────────────────────────────────


def test_cohezion_mcp_wired():
    from cohezion.skills.cohezion_mcp import CohezionMCP as src

    assert pkg_skills.CohezionMCP is src


# ── skills: mcp_paths ────────────────────────────────────────────────────────


def test_cohezion_root_wired():
    from cohezion.skills.mcp_paths import cohezion_root as src

    assert pkg_skills.cohezion_root is src


def test_cohezion_root_returns_string():
    result = pkg_skills.cohezion_root()
    assert isinstance(result, str) and len(result) > 0


# ── skills: mcp_tool_definitions ─────────────────────────────────────────────


def test_build_tool_list_wired():
    from cohezion.skills.mcp_tool_definitions import build_tool_list as src

    assert pkg_skills.build_tool_list is src


def test_build_tool_list_returns_list():
    result = pkg_skills.build_tool_list({})
    assert isinstance(result, list)


# ── skills: mcp_skill_tools ──────────────────────────────────────────────────


def test_execute_skill_wired():
    from cohezion.skills.mcp_skill_tools import execute_skill as src

    assert pkg_skills.execute_skill is src
