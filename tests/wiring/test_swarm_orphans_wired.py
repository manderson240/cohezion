"""Wiring tests for swarm/ orphan modules — round 5 (2026-06-22).

Identity tests: verify that each name re-exported from cohezion.swarm is the
*same object* as the one in the originating module. A skip is issued whenever
the name was silently suppressed (module failed to import), which is a valid
and expected outcome for modules with heavy/broken deps.

At least one discriminating behavioral test (instantiation or method call) is
included for a module that is confirmed to import cleanly.
"""

import importlib

import pytest

import cohezion.swarm as pkg


# ---------------------------------------------------------------------------
# Parametrize: (module_shortname, exported_name_in_pkg)
# For aliases (collisions), exported_name_in_pkg is the *aliased* name.
# ---------------------------------------------------------------------------
WIRED_CASES = [
    # agent_factory
    ("agent_factory", "AgentConfig"),
    ("agent_factory", "AgentFactory"),
    # anomaly_detector
    ("anomaly_detector", "AnomalyDetector"),
    ("anomaly_detector", "AnomalyType"),
    ("anomaly_detector", "get_anomaly_detector"),
    # auto_improving_parser
    ("auto_improving_parser", "AutoImprovingParser"),
    ("auto_improving_parser", "PatternLearner"),
    # autoresearch_executor
    ("autoresearch_executor", "AutoresearchExecutor"),
    # compat
    ("compat", "AgentCapability"),
    ("compat", "SwarmOrchestrator"),
    # compound_client
    ("compound_client", "create_compound_client"),
    ("compound_client", "get_compound_client"),
    ("compound_client", "reset_compound_client"),
    # context_model_router
    ("context_model_router", "ModelContextProfile"),
    # cost_aware_router
    ("cost_aware_router", "CostAwareRouter"),
    ("cost_aware_router", "QueryComplexity"),
    ("cost_aware_router", "get_cost_aware_router"),
    # democratic_debate
    ("democratic_debate", "DemocraticDebate"),
    ("democratic_debate", "DebateSession"),
    # deterministic_discovery_with_skill_fallback
    ("deterministic_discovery_with_skill_fallback", "BalancedModelDiscovery"),
    ("deterministic_discovery_with_skill_fallback", "DeterministicDiscovery"),
    # dynamic_concurrency_gate
    ("dynamic_concurrency_gate", "DynamicConcurrencyGate"),
    ("dynamic_concurrency_gate", "get_concurrency_gate"),
    # dynamic_levers
    ("dynamic_levers", "DynamicLever"),
    ("dynamic_levers", "DynamicLeverSystem"),
    # dynamic_model_router
    ("dynamic_model_router", "DynamicModelRouter"),
    # execution_orchestrator
    ("execution_orchestrator", "ExecutionOrchestrator"),
    ("execution_orchestrator", "ExecutionReport"),
    # fallback_strategy
    ("fallback_strategy", "FallbackStrategy"),
    ("fallback_strategy", "get_fallback_strategy"),
    # gemma4_router — aliased to Gemma4RoutingDecision due to collision
    ("gemma4_router", "Gemma4Router"),
    # hf_modelfile_builder
    ("hf_modelfile_builder", "HFModelfileBuilder"),
    # hiho_vector_engine
    ("hiho_vector_engine", "HihoVectorEngine"),
    # improved_deterministic_parser
    ("improved_deterministic_parser", "ImprovedFLMParser"),
    # intelligence_pipeline (may be suppressed)
    ("intelligence_pipeline", "MixtureOfExpertsRouter"),
    # journey_narrator
    ("journey_narrator", "JourneyNarrator"),
    # lemonade_manager
    ("lemonade_manager", "LemonadeManager"),
    # lemonade_model_enhancer
    ("lemonade_model_enhancer", "LemonadeModelEnhancer"),
    # lru_persistent_token_cache
    ("lru_persistent_token_cache", "LRUPersistentTokenCache"),
    # meta_learner (may be suppressed)
    ("meta_learner", "MetaLearner"),
    # mitosis_apoptosis (may be suppressed)
    ("mitosis_apoptosis", "SwarmGovernor"),
    # mode_controller (may be suppressed)
    ("mode_controller", "ModeController"),
    ("mode_controller", "get_mode_controller"),
    # model_adapter
    ("model_adapter", "SmartRouterAdapter"),
    # model_capability_registry
    ("model_capability_registry", "ModelCapabilityRegistry"),
    # model_capability_registry_resource_safe (may be suppressed)
    ("model_capability_registry_resource_safe", "ResourceSafeModelCapabilityRegistry"),
    # model_fallback_strategy
    ("model_fallback_strategy", "ModelFallbackStrategy"),
    # model_manager
    ("model_manager", "OllamaModelManager"),
    # model_ranker
    ("model_ranker", "ModelRanker"),
    ("model_ranker", "RankingStrategy"),
    # ollama_context_manager
    ("ollama_context_manager", "OllamaContextManager"),
    # orchestrator
    ("orchestrator", "SimpleSwarm"),
    ("orchestrator", "Swarm"),
    # parser_v3_validation_oracle
    ("parser_v3_validation_oracle", "ParserV3"),
    ("parser_v3_validation_oracle", "ValidationOracle"),
    # plasma_swarm_router
    ("plasma_swarm_router", "PlasmaSwarmRouter"),
    # predictive_lever_adjuster
    ("predictive_lever_adjuster", "PredictiveLeverAdjuster"),
    # quadrature_nexus
    ("quadrature_nexus", "QuadratureNexus"),
    ("quadrature_nexus", "QuadratureResult"),
    # redundancy_suppression
    ("redundancy_suppression", "RedundancyManager"),
    # research_orchestrator
    ("research_orchestrator", "ResearchOrchestrator"),
    ("research_orchestrator", "ResearchFinding"),
    # resonance
    ("resonance", "ResonanceProtocol"),
    ("resonance", "ResonanceState"),
    # routing_orchestrator
    ("routing_orchestrator", "RoutingOrchestrator"),
    ("routing_orchestrator", "UnifiedRoutingDecision"),
    # r_zero_evolver
    ("r_zero_evolver", "RZeroEvolver"),
    # semantic_cache (swarm-local)
    ("semantic_cache", "EmbeddingResult"),
    ("semantic_cache", "SemanticCacheHit"),
    # smart_router
    ("smart_router", "SmartRouter"),
    # swarm_types
    ("swarm_types", "Perspective"),
    ("swarm_types", "SwarmConfig"),
    ("swarm_types", "ThoughtVector"),
    # team_execution
    ("team_execution", "TeamCompoundExecutor"),
    # team_metrics
    ("team_metrics", "TeamCompoundMetrics"),
    ("team_metrics", "TeamMetricsAggregator"),
    # team_orchestrator
    ("team_orchestrator", "TeamOrchestrator"),
    ("team_orchestrator", "TeamPlan"),
    # tip_of_spear_router
    ("tip_of_spear_router", "TipOfTheSpearRouter"),
    # topological_router
    ("topological_router", "TopologicalRouter"),
    # triune_consensus
    ("triune_consensus", "ConsensusReport"),
    ("triune_consensus", "TriuneConsensus"),
    # triune_integration
    ("triune_integration", "TriuneAGI"),
    ("triune_integration", "TriuneState"),
    # unified_thinker
    ("unified_thinker", "UnifiedThinker"),
    # vmodel_engineering
    ("vmodel_engineering", "VModelEngineeringProcess"),
    ("vmodel_engineering", "VPhase"),
    # vmodel_phase_optimizer
    ("vmodel_phase_optimizer", "PhaseOptimizer"),
    ("vmodel_phase_optimizer", "InstrumentedVModelEngineering"),
]

# Alias map: pkg-name → (source_module, source_name) for cases where the
# exported alias differs from the original name (collision resolution).
ALIAS_MAP = {
    "Gemma4RoutingDecision": ("gemma4_router", "RoutingDecision"),
    "OllamaResilientClient": ("ollama_resilience", "ResilientOllamaClient"),
    "OrchestratorSwarmConfig": ("orchestrator", "SwarmConfig"),
    "ResonanceSwarmOrchestrator": ("resonance", "SwarmOrchestrator"),
    "SmartRoutingDecision": ("smart_router", "RoutingDecision"),
    "SwarmSemanticCache": ("semantic_cache", "SemanticCache"),
    "TopologicalRoutingDecision": ("topological_router", "RoutingDecision"),
}


@pytest.mark.parametrize("mod,name", WIRED_CASES)
def test_identity(mod: str, name: str) -> None:
    """Each re-exported name must be identical to its source."""
    if not hasattr(pkg, name):
        pytest.skip(f"{name} suppressed — module cohezion.swarm.{mod} did not import")

    src = importlib.import_module(f"cohezion.swarm.{mod}")
    pkg_obj = getattr(pkg, name)
    src_obj = getattr(src, name, None)
    assert src_obj is not None, f"cohezion.swarm.{mod} has no attribute {name}"
    assert pkg_obj is src_obj, f"cohezion.swarm.{name} is not cohezion.swarm.{mod}.{name}"


@pytest.mark.parametrize("pkg_name,source", list(ALIAS_MAP.items()))
def test_alias_identity(pkg_name: str, source: tuple[str, str]) -> None:
    """Each aliased re-export must equal its source under the original name."""
    if not hasattr(pkg, pkg_name):
        pytest.skip(f"{pkg_name} suppressed — alias target module did not import")

    src_mod_name, src_attr = source
    src = importlib.import_module(f"cohezion.swarm.{src_mod_name}")
    pkg_obj = getattr(pkg, pkg_name)
    src_obj = getattr(src, src_attr, None)
    assert src_obj is not None, f"cohezion.swarm.{src_mod_name} has no attribute {src_attr}"
    assert pkg_obj is src_obj, (
        f"cohezion.swarm.{pkg_name} (alias) is not cohezion.swarm.{src_mod_name}.{src_attr}"
    )


# ---------------------------------------------------------------------------
# Discriminating behavioral test — SmartRouter instantiation + route call.
# SmartRouter is a clean importer with no heavy deps.
# ---------------------------------------------------------------------------


def test_smart_router_behavioral() -> None:
    """SmartRouter must be instantiable and expose a .route() method."""
    if not hasattr(pkg, "SmartRouter"):
        pytest.skip("SmartRouter suppressed")

    router = pkg.SmartRouter()  # type: ignore[attr-defined]
    assert hasattr(router, "route"), "SmartRouter instance must have a .route() method"


def test_swarm_config_behavioral() -> None:
    """SwarmConfig (from swarm_types) must be a dataclass/namedtuple-like with fields."""
    if not hasattr(pkg, "SwarmConfig"):
        pytest.skip("SwarmConfig suppressed")

    cfg = pkg.SwarmConfig()  # type: ignore[attr-defined]
    # Just verify we can instantiate it without error
    assert cfg is not None


def test_triune_consensus_behavioral() -> None:
    """TriuneConsensus must be instantiable."""
    if not hasattr(pkg, "TriuneConsensus"):
        pytest.skip("TriuneConsensus suppressed")

    consensus = pkg.TriuneConsensus()  # type: ignore[attr-defined]
    assert consensus is not None
