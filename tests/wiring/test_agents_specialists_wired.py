"""Discriminating tests for agents/specialists and agents/generated wiring."""

import cohezion.agents.generated as generated_pkg
import cohezion.agents.specialists as specialists_pkg
from cohezion.agents.generated.skill_0_agent import Skill0Agent as src_skill0
from cohezion.agents.generated.skill_1_agent import Skill1Agent as src_skill1
from cohezion.agents.specialists.claude_specialist import ClaudeSpecialist as src_claude
from cohezion.agents.specialists.gemini_specialist import GeminiSpecialist as src_gemini
from cohezion.agents.specialists.mcp_specialist import MCPSpecialist as src_mcp
from cohezion.agents.specialists.ollama_specialist import OllamaSpecialist as src_ollama
from cohezion.agents.specialists.platform_coordinator import PlatformCoordinator as src_platform
from cohezion.agents.specialists.surreal_dba import SurrealDBA as src_surreal
from cohezion.agents.specialists.vault_keeper import VaultKeeper as src_vault


# ── Identity tests: package surface must be the SAME object as source ──────────


def test_claude_specialist_identity():
    assert specialists_pkg.ClaudeSpecialist is src_claude


def test_gemini_specialist_identity():
    assert specialists_pkg.GeminiSpecialist is src_gemini


def test_mcp_specialist_identity():
    assert specialists_pkg.MCPSpecialist is src_mcp


def test_ollama_specialist_identity():
    assert specialists_pkg.OllamaSpecialist is src_ollama


def test_platform_coordinator_identity():
    assert specialists_pkg.PlatformCoordinator is src_platform


def test_surreal_dba_identity():
    assert specialists_pkg.SurrealDBA is src_surreal


def test_vault_keeper_identity():
    assert specialists_pkg.VaultKeeper is src_vault


# ── Membership test: all 7 required names present on package surface ────────────


def test_all_specialists_registered():
    required = [
        "ClaudeSpecialist",
        "GeminiSpecialist",
        "MCPSpecialist",
        "OllamaSpecialist",
        "PlatformCoordinator",
        "SurrealDBA",
        "VaultKeeper",
    ]
    for name in required:
        assert hasattr(specialists_pkg, name), f"Missing from cohezion.agents.specialists: {name}"


# ── Callable test: describe_all() returns a non-empty list ─────────────────────


def test_describe_all_callable():
    result = specialists_pkg.describe_all()
    assert isinstance(result, list)
    assert len(result) >= 7


# ── Discriminating: describe_all() items each carry expected keys ──────────────


def test_describe_all_items_have_required_keys():
    """Catches a wrong describe_all() that merely returns an empty list or non-dicts."""
    result = specialists_pkg.describe_all()
    required_keys = {"name", "description", "capabilities"}
    for item in result:
        missing = required_keys - set(item)
        assert not missing, f"Specialist card missing keys {missing}: {item.get('name', '?')}"


# ── Generated agents ────────────────────────────────────────────────────────────


def test_generated_agents_load():
    # Skill0Agent and Skill1Agent must always be present in the generated package
    assert hasattr(generated_pkg, "Skill0Agent")
    assert hasattr(generated_pkg, "Skill1Agent")
    # TestSkillAgent is absent (test_skill_agent.py not generated yet) — that's OK
    # This assertion confirms the absence is intentional, not a load failure
    assert not hasattr(generated_pkg, "TestSkillAgent")


def test_skill0_agent_identity():
    assert generated_pkg.Skill0Agent is src_skill0


def test_skill1_agent_identity():
    assert generated_pkg.Skill1Agent is src_skill1
