# Code Map - Source Navigation

**@ references to key source modules organized by architecture layer.** Use this map to quickly navigate to implementation files when working on specific subsystems.

> **Tip:** @ mention files from this map in your questions to Claude to load specific source code into context.

---

## Compound Engineering Layer

**Core orchestration for skill refinement and execution tracking.**

- @src/cohezion/compound/executor.py - 11-step compound execution pipeline (RequestAlignmentAnalyzer → GlobalMetricsAggregator → DegradationDetector → JourneyTracker)
- @src/cohezion/compound/journey_tracker.py - 12D universe position tracking, state transitions, rollback checkpoints
- @src/cohezion/compound/skill_refiner.py - PRIME skill definition updates based on RetrospectionEngine learnings
- @src/cohezion/compound/request_alignment_analyzer.py - Coherence checking before execution (HIHO threshold: 0.5)
- @src/cohezion/compound/retrospection_engine.py - Extract learnings from executions, flag anomalies for skill refinement
- @src/cohezion/compound/global_metrics_aggregator.py - Track efficiency, cost, quality across all agents and executions

---

## Swarm Orchestration Layer

**Multi-agent coordination, cost routing, model selection.**

- @src/cohezion/swarm/team_orchestrator.py - Multi-agent team orchestration with ExecutionOrchestrator integration
- @src/cohezion/swarm/cost_aware_router.py - Dynamic model routing for 27.3% cost savings
- @src/cohezion/swarm/dynamic_model_router.py - Quality-aware model selection based on task requirements
- @src/cohezion/compound/team_executor.py - Team execution coordination (compound layer integration)

---

## Caching Layer

**L1/L2/L3 semantic cache with 95%+ hit rate.**

- @src/cohezion/cache/semantic_cache.py - Three-tier caching: L1 hash + L2 cosine similarity + L3 vault lookup
- @src/cohezion/cache/cache_manager.py - Cache lifecycle management, eviction policies

---

## Cost Optimization Layer

**Budget enforcement, model quality classification.**

- @src/cohezion/cost_optimization/budget_enforcer.py - Monthly budget caps, cost tracking per execution
- @src/cohezion/cost_optimization/model_quality_classifier.py - Classify tasks by quality requirements to select appropriate models

---

## Persistence Layer

**SurrealDB integration, checkpoints, session recovery.**

- @src/cohezion/core/persistence/surreal_client.py - SurrealDB client for graph storage and queries
- @src/cohezion/core/persistence/session_manager.py - Session persistence with vault + JSONL fallback
- @src/cohezion/core/persistence/checkpoint_manager.py - Deterministic checkpoint storage and recovery

---

## API Layer

**FastAPI backend with FastMCP patterns.**

- @src/cohezion/api/__init__.py - FastAPI app initialization, MCP server setup (40+ tools proven pattern)
- @src/cohezion/api/routes_compound.py - Compound engineering endpoints (/compound, /skills, /retrospective)
- @src/cohezion/api/routes_swarm.py - Swarm orchestration endpoints (team execution, routing)
- @src/cohezion/api/routes_journeys.py - Journey tracking and 12D universe navigation

---

## FLUME VAE Layer

**256D latent space for experience encoding.**

- @src/cohezion/flume/vae_encoder.py - Variational autoencoder for trajectory compression
- @src/cohezion/flume/autoencoder.py - Core autoencoder architecture
- @src/cohezion/flume/experience_pipeline.py - Experience collection and encoding pipeline
- @src/cohezion/eval/flume_guided.py - FLUME-guided code generation and trajectory analysis

---

## Knowledge Management

**Vault-first knowledge persistence and retrieval.**

- @src/cohezion/knowledge_graph/vault_integration.py - Integration with cohezion-vault MCP for decisions/patterns/experiments
- @src/cohezion/knowledge_graph/KEY_LEARNINGS.md - Historical patterns, anti-patterns, cost lessons (manually curated)

---

## Testing & Configuration

**Core testing infrastructure and project configuration.**

- @tests/conftest.py - **CRITICAL:** Shared fixtures, singleton resets (FLUME VAE, RL policy, loggers) - **Read first when debugging tests**
- @pytest.ini - Test configuration, markers (unit/integration), pytest options
- @pyproject.toml - Python 3.13+ dependencies, build config, ruff/mypy/pytest tool settings

---

## Usage Examples

**Load specific subsystem context:**
```
# Working on compound execution pipeline
"Explain the 11-step pipeline in @src/cohezion/compound/executor.py"

# Debugging cache issues
"Why is the cache hit rate low? Check @src/cohezion/cache/semantic_cache.py"

# Understanding test failures
"Tests fail in suite but pass individually. Check @tests/conftest.py for singleton pollution."
```

**Multi-file analysis:**
```
"How does JourneyTracker (@src/cohezion/compound/journey_tracker.py) integrate with
SessionManager (@src/cohezion/persistence/session_manager.py)?"
```
