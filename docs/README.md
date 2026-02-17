# Cohezion Documentation

Documentation index for the Cohezion compound AI orchestration framework.

## Architecture

Cohezion implements a 12-dimensional agentic universe with compound engineering loops,
multi-agent swarms, and autonomous skill refinement.

### Core Layers

| Layer | Purpose | Entry Point |
|-------|---------|-------------|
| **Compound** | Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `CompoundExecutor` |
| **Swarm** | TeamOrchestrator, ExecutionOrchestrator, DynamicModelRouter | `TeamExecutor` |
| **Cache** | L1 hash + L2 cosine + L3 vault semantic cache (95%+ hit rate) | `SemanticCache` |
| **Cost Optimization** | CostAwareRouter (27.3% savings), BudgetEnforcer | `CostAwareRouter` |
| **Persistence** | SurrealDB + JSONL session persistence | `SessionManager` |
| **Knowledge** | Vault-first decisions/patterns/experiments | `vault_find_relevant_context` |

### Compound Engineering Loop

```
PRIME Skill (markdown)
  -> InstructionExpander (parse -> tasks)
  -> PlanExecutor (tactical plan)
  -> ExecutionOrchestrator (11-step pipeline)
  -> RetrospectionEngine (extract learnings)
  -> SkillRefiner (update skill definition)
  -> SkillConsensusVoter (multi-agent validation)
  -> Updated Skill (loop again)
```

## Key References

| Document | Purpose |
|----------|---------|
| [CLAUDE.md](../CLAUDE.md) | Development guide and coding standards |
| [.agent/CONSTITUTION.md](../.agent/CONSTITUTION.md) | Hard constraints and governance |
| [.agent/COHEZION_CHARTER.md](../.agent/COHEZION_CHARTER.md) | Design theory (SPIN, FLUME, HIHO) |
| [HARDWARE_PROFILE_PRIME.md](../HARDWARE_PROFILE_PRIME.md) | Hardware truth anchor |

## Quick Start

```bash
# Install dependencies
uv sync

# Run test suite
uv run pytest tests/ -q

# Start API server
uv run uvicorn cohezion.api:app --reload

# Run compound cycle (dry-run)
uv run python scripts/drivers/compound_cycle.py
```

## Hardware

- **CPU**: AMD Ryzen AI MAX+ 395 (16C/32T, AVX-512)
- **GPU**: Radeon 8060S (iGPU, unified memory) — no CUDA
- **RAM**: 128 GiB LPDDR5X
- **Local Models**: Ollama (deepseek-r1:70b, qwen3-coder:30b, phi3:mini)
