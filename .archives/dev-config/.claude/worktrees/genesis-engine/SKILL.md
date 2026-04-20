---
name: cohezion
description: Compound AI orchestration framework with 12D universe simulation,
  FLUME VAE training, multi-agent swarm coordination, and autonomous skill
  refinement. Use when building AI agent pipelines, orchestrating multi-model
  workflows, managing compound engineering loops, or implementing autonomous
  skill refinement. Handles model routing, semantic caching, cost optimization,
  journey tracking, and coherence monitoring.
metadata:
  author: Cohezion
  version: 1.0.2
  mcp-server: cohezion-bridge
compatibility: Python 3.13+, SurrealDB, Ollama (local models). Works with
  Claude Code and Claude.ai. Requires uv package manager.
---

# Cohezion - Compound AI Orchestration

## Instructions

### Step 1: Understand the Request

Identify which Cohezion subsystem is needed:

- **Compound Engineering** - Multi-step AI pipelines with skill refinement loops
- **Swarm Orchestration** - Multi-agent team execution with model routing
- **Semantic Caching** - L1/L2/L3 cache with 95%+ hit rate
- **Cost Optimization** - Budget-aware routing with 27% savings
- **Universe Simulation** - 12D physics simulation with FLUME VAE
- **Journey Tracking** - Agent state tracking through 12D coordinates

### Step 2: Route to the Right Component

| Need | Entry Point | Key File |
|------|------------|----------|
| Run compound loop | `CompoundExecutor` | `src/cohezion/compound/executor.py` |
| Orchestrate agents | `TeamExecutor` | `src/cohezion/swarm/team_executor.py` |
| Cache results | `SemanticCache` | `src/cohezion/cache/semantic_cache.py` |
| Optimize costs | `CostAwareRouter` | `src/cohezion/swarm/cost_aware_router.py` |
| Track journeys | `JourneyTracker` | `src/cohezion/compound/journey_tracker.py` |
| Run simulations | `EnhancedSimulator` | `src/cohezion/simulation/enhanced_simulator.py` |

### Step 3: Follow the Compound Engineering Loop

```
PRIME Skill (markdown) -> InstructionExpander -> PlanExecutor
  -> ExecutionOrchestrator (11-step pipeline)
  -> RetrospectionEngine (extract learnings)
  -> SkillRefiner (update skill)
  -> SkillConsensusVoter (validate)
  -> Updated Skill (loop again)
```

### Step 4: Verify Results

```bash
uv run pytest tests/ -q                    # Full test suite
uv run pytest tests/compound/ -v           # Module tests
make format && make lint && make all       # Format + lint + verify
```

## Common Issues

### Test Isolation Failures
Tests pass individually but fail in suite due to singleton pollution.
Fix: Check `tests/conftest.py` for FLUME VAE, RL policy, and logger resets.

### Ollama Timeouts
Tests hitting live Ollama instead of mock.
Fix: Mock at source with `@patch("cohezion.swarm.compound_client.get_compound_client")`.

### MCP Connection Issues
1. Verify SurrealDB is running: `surreal start`
2. Check connection: `ws://localhost:8000`
3. Verify auth credentials in `.env`
