"""Wiring tests for security, mcp, core, and research orphan modules — round 5.

Each test verifies that a name imported from the package __init__ is the same
object as the name imported directly from its source module (identity check).
One behavioral test exercises a pure, dep-free callable to confirm the module
is actually executable, not just importable.
"""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Identity tests — security/
# ---------------------------------------------------------------------------


def test_security_SecurityPipeline_identity() -> None:
    from cohezion.security import SecurityPipeline
    from cohezion.security.pipeline import SecurityPipeline as _Direct

    assert SecurityPipeline is _Direct


def test_security_PromptGuard_identity() -> None:
    from cohezion.security import PromptGuard
    from cohezion.security.prompt_guard import PromptGuard as _Direct

    assert PromptGuard is _Direct


def test_security_ConstitutionalShield_identity() -> None:
    from cohezion.security import ConstitutionalShield
    from cohezion.security.constitutional_shield import ConstitutionalShield as _Direct

    assert ConstitutionalShield is _Direct


def test_security_AttackCategory_identity() -> None:
    from cohezion.security import AttackCategory
    from cohezion.security.attack_patterns import AttackCategory as _Direct

    assert AttackCategory is _Direct


def test_security_RateLimiter_identity() -> None:
    from cohezion.security import RateLimiter
    from cohezion.security.rate_limiter import RateLimiter as _Direct

    assert RateLimiter is _Direct


def test_security_ConstitutionalEnforcer_identity() -> None:
    from cohezion.security import ConstitutionalEnforcer
    from cohezion.security.constitutional_enforcer import ConstitutionalEnforcer as _Direct

    assert ConstitutionalEnforcer is _Direct


def test_security_EvalAwarenessDefense_identity() -> None:
    from cohezion.security import EvalAwarenessDefense
    from cohezion.security.eval_awareness_defense import EvalAwarenessDefense as _Direct

    assert EvalAwarenessDefense is _Direct


def test_security_AgentAuthManager_identity() -> None:
    from cohezion.security import AgentAuthManager
    from cohezion.security.agent_auth import AgentAuthManager as _Direct

    assert AgentAuthManager is _Direct


# ---------------------------------------------------------------------------
# Identity tests — mcp/
# ---------------------------------------------------------------------------


def test_mcp_McpClientResolver_identity() -> None:
    from cohezion.mcp import McpClientResolver
    from cohezion.mcp.compound_utils import McpClientResolver as _Direct

    assert McpClientResolver is _Direct


def test_mcp_HookifyMCPBridge_identity() -> None:
    from cohezion.mcp import HookifyMCPBridge
    from cohezion.mcp.hookify_server import HookifyMCPBridge as _Direct

    assert HookifyMCPBridge is _Direct


def test_mcp_MCPRegistry_identity() -> None:
    from cohezion.mcp import MCPRegistry
    from cohezion.mcp.registry import MCPRegistry as _Direct

    assert MCPRegistry is _Direct


def test_mcp_MCPAuditor_identity() -> None:
    from cohezion.mcp import MCPAuditor
    from cohezion.mcp.audit import MCPAuditor as _Direct

    assert MCPAuditor is _Direct


def test_mcp_SwarmMCP_identity() -> None:
    from cohezion.mcp import SwarmMCP
    from cohezion.mcp.swarm_server import SwarmMCP as _Direct

    assert SwarmMCP is _Direct


def test_mcp_SkillsMCP_identity() -> None:
    from cohezion.mcp import SkillsMCP
    from cohezion.mcp.skills_server import SkillsMCP as _Direct

    assert SkillsMCP is _Direct


# ---------------------------------------------------------------------------
# Identity tests — core/
# ---------------------------------------------------------------------------


def test_core_TelemetryBus_identity() -> None:
    from cohezion.core import TelemetryBus
    from cohezion.core.telemetry_bus import TelemetryBus as _Direct

    assert TelemetryBus is _Direct


def test_core_SiliconGuard_identity() -> None:
    from cohezion.core import SiliconGuard
    from cohezion.core.silicon_guard import SiliconGuard as _Direct

    assert SiliconGuard is _Direct


def test_core_CacheManager_identity() -> None:
    from cohezion.core import CacheManager
    from cohezion.core.cache_manager import CacheManager as _Direct

    assert CacheManager is _Direct


def test_core_TemplateEngine_identity() -> None:
    from cohezion.core import TemplateEngine
    from cohezion.core.template_engine import TemplateEngine as _Direct

    assert TemplateEngine is _Direct


def test_core_JourneyWorker_identity() -> None:
    from cohezion.core import JourneyWorker
    from cohezion.core.journey_worker import JourneyWorker as _Direct

    assert JourneyWorker is _Direct


def test_core_ZVOLSwapPipeline_identity() -> None:
    from cohezion.core import ZVOLSwapPipeline
    from cohezion.core.zvol_swap import ZVOLSwapPipeline as _Direct

    assert ZVOLSwapPipeline is _Direct


def test_core_LocalExpertRouter_identity() -> None:
    from cohezion.core import LocalExpertRouter
    from cohezion.core.routing.router import LocalExpertRouter as _Direct

    assert LocalExpertRouter is _Direct


def test_core_SymmetryHardwareBridge_identity() -> None:
    from cohezion.core import SymmetryHardwareBridge
    from cohezion.core.symmetry_hardware_bridge import SymmetryHardwareBridge as _Direct

    assert SymmetryHardwareBridge is _Direct


# ---------------------------------------------------------------------------
# Identity tests — research/
# ---------------------------------------------------------------------------


def test_research_AdaptiveSkillRefiner_identity() -> None:
    from cohezion.research import AdaptiveSkillRefiner
    from cohezion.research.adaptive_refinement import AdaptiveSkillRefiner as _Direct

    assert AdaptiveSkillRefiner is _Direct


def test_research_ResearchCheckpoint_identity() -> None:
    from cohezion.research import ResearchCheckpoint
    from cohezion.research.checkpoint import ResearchCheckpoint as _Direct

    assert ResearchCheckpoint is _Direct


def test_research_CostTracker_identity() -> None:
    from cohezion.research import CostTracker
    from cohezion.research.cost_optimization import CostTracker as _Direct

    assert CostTracker is _Direct


def test_research_AutoresearchDriver_identity() -> None:
    from cohezion.research import AutoresearchDriver
    from cohezion.research.autoresearch_driver import AutoresearchDriver as _Direct

    assert AutoresearchDriver is _Direct


def test_research_Orborous_identity() -> None:
    from cohezion.research import Orborous
    from cohezion.research.orborous import Orborous as _Direct

    assert Orborous is _Direct


def test_research_PartyModeConsensus_identity() -> None:
    from cohezion.research import PartyModeConsensus
    from cohezion.research.consensus import PartyModeConsensus as _Direct

    assert PartyModeConsensus is _Direct


# ---------------------------------------------------------------------------
# Behavioral test — pure, dep-free
# ---------------------------------------------------------------------------


def test_attack_patterns_get_pattern_count_nonzero() -> None:
    """security.attack_patterns is importable and has real content."""
    from cohezion.security.attack_patterns import get_pattern_count

    assert get_pattern_count() > 0


def test_mcp_compound_utils_ok_and_err_shapes() -> None:
    """mcp.compound_utils helper returns expected dict shapes."""
    from cohezion.mcp.compound_utils import err, ok

    success = ok(result="done", count=3)
    assert success["result"] == "done"
    assert success["count"] == 3
    assert success["status"] == "success"

    failure = err("something broke", code=42)
    assert failure["status"] == "error"
    assert failure["error"] == "something broke"
    assert failure["code"] == 42
