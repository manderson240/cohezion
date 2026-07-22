# swarm — Local Context

This file loads in addition to the root `CLAUDE.md`. Root applies here too.

**Purpose:** Swarm orchestration and token-efficient inference.

## Entry points (74 modules)

| Module | Key class(es) | LOC |
|---|---|---|
| `adaptive_router.py` | `RoutingDecision`, `RoutingHistory`, `TaskAnalyzer` | 614 ⚠ |
| `agent_factory.py` | `AgentConfig`, `AgentFactory` | 316 |
| `anomaly_detector.py` | `AnomalyType`, `AnomalyAlert`, `ModelCostHistory` | 475 |
| `auto_improving_parser.py` | `LearnedPattern`, `PatternLearner`, `AutoImprovementResult` | 358 |
| `autoresearch_executor.py` | `AutoresearchExecutor` | 142 |
| `batch_processor.py` | `CacheEntry`, `BatchItem`, `BatchResult` | 368 |
| `compat.py` | `SwarmOrchestrator`, `LegacyAgentResult`, `AgentCapability` | 169 |
| `compute_backend_router.py` | `BackendType`, `BackendStatus`, `BackendCapability` | 614 ⚠ |
| `context_model_router.py` | `ModelContextProfile` | 42 |
| `cost_aware_router.py` | `QueryComplexity`, `ModelRoutingDecision`, `RoutingStatistics` | 1407 ⚠ |
| `democratic_debate.py` | `AgentRole`, `AgentPersona`, `VoteValue` | 463 |
| `deterministic_discovery_with_skill_fallback.py` | `DeterministicDiscovery`, `HeuristicDiscovery`, `BalancedModelDiscovery` | 419 |
| `dynamic_agent_registry.py` | `AgentModule`, `DynamicAgentRegistry` | 539 ⚠ |
| `dynamic_concurrency_gate.py` | `HardwareMetrics`, `HardwareProfilerFactory`, `ConcurrencyDecision` | 278 |

## Over the 500-LOC limit (decompose non-destructively)

- `adaptive_router.py` — 614 LOC
- `compute_backend_router.py` — 614 LOC
- `cost_aware_router.py` — 1407 LOC
- `dynamic_agent_registry.py` — 539 LOC
- `dynamic_levers.py` — 517 LOC
- `dynamic_model_router.py` — 702 LOC
- `fallback_strategy.py` — 702 LOC
- `lemonade_model_enhancer.py` — 586 LOC
- `model_capability_registry.py` — 704 LOC
- `model_pool_manager.py` — 566 LOC
- `multi_agent_orchestrator.py` — 508 LOC
- `multi_layer_cache.py` — 671 LOC
- `predictive_lever_adjuster.py` — 543 LOC
- `quadrature_nexus.py` — 827 LOC
- `research_orchestrator.py` — 681 LOC
- `smart_router.py` — 551 LOC
- `tip_of_spear_router.py` — 563 LOC
- `vmodel_engineering.py` — 694 LOC

## Invariants / notes referencing this package (from harness.md / root CLAUDE.md)

- - Closes a producer→consumer gap: `JEPAWorldModel.simulate_trajectory` existed (used by the API service) but the gate never called it.
- # MANDATORY: Agent MARKDOWN files (AGENTS.md) must start with valid YAML frontmatter
- ### ⚡ Reporting Findings (Multi-Agent)
- 3. **Mock live services at source**: `@patch("cohezion.swarm.compound_client.get_compound_client")`
- ### ⚡ Execution Priority (Sessions 56+)
- ### ⚡ Development Agent Routing

_Auto-generated 2026-07-22 (gen_nested_claude.py): facts deterministic (ast/grep), Purpose from __init__/module docstrings. Validated by scripts/ci/doc_code_consistency.py. Hand-enrich as needed._
