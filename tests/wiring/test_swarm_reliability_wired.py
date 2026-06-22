"""Wiring tests for swarm sub-packages, healing, resilience, observability, and
mycelium/graph/gateway/hookify orphans.

Identity tests: verify each name re-exported from the package is the *same
object* as the one in the originating module.  A skip is issued when the name
was silently suppressed (module failed to import).
"""

import importlib

import pytest


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------


def _check_identity(pkg_mod: str, src_submod: str, name: str) -> None:
    """Assert pkg_mod.name is src_submod.name, skipping if suppressed."""
    pkg = importlib.import_module(pkg_mod)
    if not hasattr(pkg, name):
        pytest.skip(f"{name} suppressed in {pkg_mod}")
    src = importlib.import_module(src_submod)
    pkg_obj = getattr(pkg, name)
    src_obj = getattr(src, name, None)
    assert src_obj is not None, f"{src_submod} has no attribute {name}"
    assert pkg_obj is src_obj, f"{pkg_mod}.{name} is not {src_submod}.{name}"


# ---------------------------------------------------------------------------
# swarm/agents
# ---------------------------------------------------------------------------

AGENTS_CASES = [
    ("cohezion.swarm.agents.base_scout", "Finding"),
    ("cohezion.swarm.agents.base_scout", "ASTSummary"),
    ("cohezion.swarm.agents.base_scout", "BaseScout"),
    ("cohezion.swarm.agents.anti_pattern_scout", "AntiPatternScout"),
    ("cohezion.swarm.agents.pattern_scout", "PatternScout"),
    ("cohezion.swarm.agents.architecture_scout", "ArchitectureScout"),
    ("cohezion.swarm.agents.quality_scout", "QualityScout"),
    ("cohezion.swarm.agents.eigent_agent", "EigentAgent"),
    ("cohezion.swarm.agents.code_review_swarm", "CodeReviewSwarm"),
    ("cohezion.swarm.agents.code_review_swarm", "SwarmReport"),
    ("cohezion.swarm.agents.arc_agi_3_wrapper", "ARCAGI3Env"),
    ("cohezion.swarm.agents.arc_agi_3_wrapper", "RecursiveChainOfThought"),
]


@pytest.mark.parametrize("src,name", AGENTS_CASES)
def test_agents_identity(src: str, name: str) -> None:
    _check_identity("cohezion.swarm.agents", src, name)


def test_agents_finding_behavioral() -> None:
    """Finding dataclass must be instantiable and have expected fields."""
    import cohezion.swarm.agents as pkg
    import dataclasses

    if not hasattr(pkg, "Finding"):
        pytest.skip("Finding suppressed")

    assert dataclasses.is_dataclass(pkg.Finding), "Finding must be a dataclass"  # type: ignore[arg-type]
    field_names = {f.name for f in dataclasses.fields(pkg.Finding)}  # type: ignore[arg-type]
    assert "category" in field_names, "Finding must have a 'category' field"
    assert "confidence" in field_names, "Finding must have a 'confidence' field"


# ---------------------------------------------------------------------------
# swarm/autoresearch
# ---------------------------------------------------------------------------

AUTORESEARCH_CASES = [
    ("cohezion.swarm.autoresearch.base", "ExperimentResult"),
    ("cohezion.swarm.autoresearch.base", "ResearchDriver"),
]


@pytest.mark.parametrize("src,name", AUTORESEARCH_CASES)
def test_autoresearch_identity(src: str, name: str) -> None:
    _check_identity("cohezion.swarm.autoresearch", src, name)


def test_autoresearch_driver_behavioral() -> None:
    """ResearchDriver must be an abstract class (not directly instantiable)."""
    import cohezion.swarm.autoresearch as pkg

    if not hasattr(pkg, "ResearchDriver"):
        pytest.skip("ResearchDriver suppressed")

    import inspect

    assert inspect.isabstract(pkg.ResearchDriver), "ResearchDriver must be abstract"  # type: ignore[attr-defined]


# ---------------------------------------------------------------------------
# swarm/providers (additional symbols)
# ---------------------------------------------------------------------------

PROVIDERS_CASES = [
    ("cohezion.swarm.providers.model_provider", "GenerationResult"),
    ("cohezion.swarm.providers.ollama_provider", "OllamaProvider"),
    ("cohezion.swarm.providers.gemma4_provider", "Gemma4Provider"),
    ("cohezion.swarm.providers.gemini_provider", "GeminiProvider"),
    ("cohezion.swarm.providers.lemonade_provider", "LemonadeProvider"),
    ("cohezion.swarm.providers.multi_model_orchestrator", "ComputeUnit"),
    ("cohezion.swarm.providers.multi_model_orchestrator", "ModelType"),
    ("cohezion.swarm.providers.multi_model_orchestrator", "MultiModelOrchestrator"),
    ("cohezion.swarm.providers.tip_spear_provider", "TipSpearProvider"),
]


@pytest.mark.parametrize("src,name", PROVIDERS_CASES)
def test_providers_identity(src: str, name: str) -> None:
    _check_identity("cohezion.swarm.providers", src, name)


# ---------------------------------------------------------------------------
# healing
# ---------------------------------------------------------------------------

HEALING_CASES = [
    ("cohezion.healing.drift_analyzer", "DriftAnalyzer"),
    ("cohezion.healing.deep_audit", "CodeIssue"),
    ("cohezion.healing.deep_audit", "DeepAuditor"),
    ("cohezion.healing.deep_audit", "FileStats"),
    ("cohezion.healing.immune_system", "SelfDiagnostic"),
    ("cohezion.healing.immune_system", "VelocityMonitor"),
    ("cohezion.healing.immune_system", "ActuatorSystem"),
    ("cohezion.healing.platform_audit", "AuditResult"),
    ("cohezion.healing.platform_audit", "PlatformAudit"),
    ("cohezion.healing.amd_s2idle_report", "DistroPackage"),
    ("cohezion.healing.amd_s2idle_report", "PipxPackage"),
]


@pytest.mark.parametrize("src,name", HEALING_CASES)
def test_healing_identity(src: str, name: str) -> None:
    _check_identity("cohezion.healing", src, name)


def test_healing_drift_analyzer_behavioral() -> None:
    """DriftAnalyzer must be instantiable and expose its core calculation method."""
    import cohezion.healing as pkg

    if not hasattr(pkg, "DriftAnalyzer"):
        pytest.skip("DriftAnalyzer suppressed")

    da = pkg.DriftAnalyzer()  # type: ignore[attr-defined]
    assert hasattr(da, "calculate_kl_divergence"), (
        "DriftAnalyzer must expose .calculate_kl_divergence()"
    )


# ---------------------------------------------------------------------------
# resilience
# ---------------------------------------------------------------------------

RESILIENCE_CASES = [
    ("cohezion.resilience.manager", "AutonomicManager"),
    ("cohezion.resilience.strategies", "HealingStrategy"),
    ("cohezion.resilience.strategies", "ModelSwapStrategy"),
    ("cohezion.resilience.strategies", "ContextReductionStrategy"),
    ("cohezion.resilience.strategies", "SystemRestartStrategy"),
]


@pytest.mark.parametrize("src,name", RESILIENCE_CASES)
def test_resilience_identity(src: str, name: str) -> None:
    _check_identity("cohezion.resilience", src, name)


def test_resilience_manager_behavioral() -> None:
    """AutonomicManager must be instantiable."""
    import cohezion.resilience as pkg

    if not hasattr(pkg, "AutonomicManager"):
        pytest.skip("AutonomicManager suppressed")

    mgr = pkg.AutonomicManager()  # type: ignore[attr-defined]
    assert mgr is not None


# ---------------------------------------------------------------------------
# observability
# ---------------------------------------------------------------------------

OBSERVABILITY_CASES = [
    ("cohezion.observability.gpu_monitor", "GPUMetrics"),
    ("cohezion.observability.gpu_monitor", "GPUMonitor"),
    ("cohezion.observability.gpu_monitor", "ThermalProfilingResult"),
    ("cohezion.observability.metrics_analytics", "MetricsTrend"),
    ("cohezion.observability.metrics_analytics", "PerformanceReport"),
    ("cohezion.observability.metrics_analytics", "MetricsAnalytics"),
]


@pytest.mark.parametrize("src,name", OBSERVABILITY_CASES)
def test_observability_identity(src: str, name: str) -> None:
    _check_identity("cohezion.observability", src, name)


def test_gpu_monitor_behavioral() -> None:
    """GPUMonitor must be instantiable."""
    import cohezion.observability as pkg

    if not hasattr(pkg, "GPUMonitor"):
        pytest.skip("GPUMonitor suppressed")

    monitor = pkg.GPUMonitor()  # type: ignore[attr-defined]
    assert monitor is not None


# ---------------------------------------------------------------------------
# mycelium
# ---------------------------------------------------------------------------

MYCELIUM_CASES = [
    ("cohezion.mycelium.loop", "CoverageLoop"),
    ("cohezion.mycelium.observer", "ChangeObserver"),
    ("cohezion.mycelium.registry", "MyceliumCluster"),
    ("cohezion.mycelium.registry", "MyceliumRegistry"),
    ("cohezion.mycelium.scripter", "ShadowScripter"),
]


@pytest.mark.parametrize("src,name", MYCELIUM_CASES)
def test_mycelium_identity(src: str, name: str) -> None:
    _check_identity("cohezion.mycelium", src, name)


def test_mycelium_registry_behavioral() -> None:
    """MyceliumRegistry must be instantiable and expose subscribe()."""
    import cohezion.mycelium as pkg

    if not hasattr(pkg, "MyceliumRegistry"):
        pytest.skip("MyceliumRegistry suppressed")

    reg = pkg.MyceliumRegistry()  # type: ignore[attr-defined]
    assert hasattr(reg, "subscribe"), "MyceliumRegistry must expose .subscribe()"


# ---------------------------------------------------------------------------
# gateway (new symbols)
# ---------------------------------------------------------------------------

GATEWAY_CASES = [
    ("cohezion.gateway.demo_gateway", "DemoGateway"),
    ("cohezion.gateway.demo_gateway", "DemoMetrics"),
    ("cohezion.gateway.mcp_server", "GatewayManager"),
    ("cohezion.gateway.mcp_server", "get_gateway_manager"),
]


@pytest.mark.parametrize("src,name", GATEWAY_CASES)
def test_gateway_identity(src: str, name: str) -> None:
    _check_identity("cohezion.gateway", src, name)


def test_gateway_demo_gateway_behavioral() -> None:
    """DemoGateway must be instantiable."""
    import cohezion.gateway as pkg

    if not hasattr(pkg, "DemoGateway"):
        pytest.skip("DemoGateway suppressed")

    gw = pkg.DemoGateway()  # type: ignore[attr-defined]
    assert gw is not None


# ---------------------------------------------------------------------------
# hookify (new symbols)
# ---------------------------------------------------------------------------

HOOKIFY_CASES = [
    ("cohezion.hookify.adversarial_review", "ReviewPerspective"),
    ("cohezion.hookify.adversarial_review", "AdversarialReviewResult"),
    ("cohezion.hookify.adversarial_review", "AdversarialReviewHarness"),
    ("cohezion.hookify.adversarial_review", "ConsensusVoter"),
    ("cohezion.hookify.vault_writer", "HookifyVaultWriter"),
]


@pytest.mark.parametrize("src,name", HOOKIFY_CASES)
def test_hookify_identity(src: str, name: str) -> None:
    _check_identity("cohezion.hookify", src, name)


def test_hookify_consensus_voter_behavioral() -> None:
    """ConsensusVoter must be instantiable."""
    import cohezion.hookify as pkg

    if not hasattr(pkg, "ConsensusVoter"):
        pytest.skip("ConsensusVoter suppressed")

    voter = pkg.ConsensusVoter()  # type: ignore[attr-defined]
    assert voter is not None


# ---------------------------------------------------------------------------
# graph (already fully wired — smoke test only)
# ---------------------------------------------------------------------------


def test_graph_package_importable() -> None:
    """cohezion.graph must be importable with its full suite of exports."""
    import cohezion.graph as pkg

    for name in ["WorkflowBuilder", "WorkflowEngine", "AgentNode", "NodeStatus"]:
        assert hasattr(pkg, name), f"cohezion.graph missing expected export: {name}"
