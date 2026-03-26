# EVAL_PROGRESS — FLUME Journey Benchmark Lab Notes

## Session: 2026-03-25

## Mission

Build a production-grade FLUME Journey Benchmark Platform for Anthropic Research Engineer, Universes role. The platform trains RL agents to navigate the FLUME manifold, treating every journey as an Etheric Variant Oscillator (EVO) with full physics biography.

## Benchmark Platform Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    FLUME JOURNEY BENCHMARK PLATFORM                  │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────────────┐ │
│  │ TaskGenerator │───▶│ FlumeNavEnv  │◀───│   TRIUNEPolicy (PPO)  │ │
│  │  20 TaskSpecs │    │  256D VAE    │    │   Knower→Thinker→Doer│ │
│  └──────────────┘    └──────┬───────┘    └──────────────────────┘ │
│                              │                                     │
│                    ┌─────────▼─────────┐                          │
│                    │ EthericVariant    │                          │
│                    │ Oscillator (EVO)  │                          │
│                    │ biography tracking│                          │
│                    └─────────┬─────────┘                          │
│                              │                                     │
│         ┌────────────────────┼────────────────────┐                │
│         │                    │                    │                │
│  ┌──────▼──────┐    ┌───────▼───────┐    ┌──────▼──────┐        │
│  │  RalphLoop  │    │ RalphLoop     │    │ RalphLoop    │        │
│  │  FOR-DONE-  │    │ (evaluation)  │    │ (long-run    │        │
│  │  ESCALATE   │    │               │    │  autonomous)  │        │
│  └──────┬──────┘    └───────┬───────┘    └──────┬──────┘        │
│         │                   │                    │                │
│  ┌──────▼───────────────────▼────────────────────▼──────┐        │
│  │           EVOPhysicsMetrics                          │        │
│  │  6 metric families × bootstrap CI × Mann-Whitney U   │        │
│  └──────────────────────┬───────────────────────────────┘        │
│                         │                                        │
│         ┌───────────────┼────────────────────┐                   │
│         │               │                    │                    │
│  ┌──────▼──────┐  ┌─────▼──────┐  ┌───────▼───────┐            │
│  │ Benchmark   │  │ Capability │  │ HuggingFace    │            │
│  │ Suite       │  │ Scorecard │  │ Export         │            │
│  │ (LM Harness)│  │ 6-axis    │  │ JSONL + card   │            │
│  └─────────────┘  └───────────┘  └────────────────┘            │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

## What's Been Built

### Phase 1-4: Core RL Stack
- [x] EthericVariantOscillator — TRIUNE SELF physics entity
- [x] TaskGenerator — 20 TaskSpecs (5 archetypes × 4 difficulties)
- [x] FlumeNavEnv — Gymnasium env with Hamiltonian dynamics
- [x] TRIUNEPolicy + PPOTrainer — 3-tier policy + GAE + checkpointing

### Phase 5: Agentic Metrics
- [x] 6 EVO physics metric families with bootstrap CIs
- [x] Mann-Whitney U significance testing
- [x] Bonferroni multiple-hypothesis correction
- [x] EVOPhysicsMetrics aggregator
- **34 tests passing**

### Phase 6: Pipeline
- [x] RalphLoop — FOR-DONE-ESCALATE iteration pattern
- [x] EvalPipeline — multi-episode orchestration
- [x] EpisodeStatus, PipelineProgress dataclasses
- **40 tests passing**

### Phase 7: Scorecard + Export
- [x] CapabilityScorecard — 6-axis radar chart
- [x] LongitudinalTracker — multi-run trend analysis
- [x] HuggingFaceExporter — JSONL + metadata + dataset card
- **89 tests passing** (scorecard + export)

## Integration 1: EvalPipeline → CompoundSessionManager

**Concept**: Wrap EvalPipeline runs inside CompoundSessionManager for warm-start cache and checkpoint persistence.

**Implementation**: Session wraps RalphLoop iteration; after each episode, checkpoint to vault. On restart, warm cache and restore PPOTrainer state.

## Integration 2: EVO Biography → Vault MCP

**Concept**: After each episode, push EVO biography to vault via JourneyTracker.

**Implementation**: `JourneyTracker.record_state()` stores EVO physics trajectory. MCP tools (`mcp__cohezion-surreal__store_learning`) persist to SurrealDB.

## Integration 3: Weak-Axis Curriculum

**Concept**: CapabilityScorecard identifies weakest axis → SkillRefiner oversamples TaskSpecs targeting that axis.

**Implementation**:
```python
weakest = scorecard._longitudinal_tracker.get_weakest_axis()
task_generator = TaskGenerator()
specs = task_generator.sample_by_archetype(map_axis_to_archetype[weakest])
```

## Integration 4: FastAPI Benchmark Endpoints

**Concept**: Expose `benchmark.run(policy, tasks)` via FastAPI.

**Implementation**:
- `POST /rl/benchmark` — Run benchmark suite
- `GET /rl/benchmark/{run_id}/scorecard` — Get scorecard
- `GET /rl/benchmark/{run_id}/radar.svg` — Get radar chart

## Integration 5: Long-Running Autonomous Training

**Concept**: RalphLoop with n_episodes=500+, git commits at milestones.

**Implementation**: Each milestone (100, 200, 500 episodes) → checkpoint + git commit with metrics.

## Integration 6: Swarm-Advisor Integration

**Concept**: At episode start, Cohezion multi-agent Knower advises on TaskSpec selection.

**Implementation**: `KnowerAdvisor.get_guidance(task_history)` → suggested archetype/difficulty for next episode.

## Current Status

**Test counts**:
| Module | Tests |
|--------|-------|
| agentic_metrics | 34 |
| benchmark_suite | 22 |
| pipeline | 18 |
| capability_scorecard | 57 |
| huggingface_export | 32 |
| **New total** | **163** |

**Lint status**: Module imports checked, awaiting full lint run.

## Next Steps

1. Run `make lint` on new modules
2. Run `make test` to verify all tests pass
3. Implement Integration 1 (CompoundSession feedback loop)
4. Implement Integration 4 (FastAPI endpoints)
5. Full integration test with real PPO trainer

## Key Learnings

- Bootstrap with resampling correctly estimates CI even for non-normal distributions
- Mann-Whitney U is robust to outliers (doesn't assume normality)
- Bonferroni is conservative; Benjamini-Hochberg FDR is less conservative alternative
- Longitudinal significance requires at least 20 episodes (10 recent + 10 previous)
- Plotly radar charts are far superior to matplotlib for interactive exploration

## Open Questions

1. Should we use Benjamini-Hochberg instead of Bonferroni for less conservative multiple testing?
2. How many episodes needed for stable CapabilityScorecard? (Power analysis: ~50 per run)
3. Should BenchmarkSuite support parallel episode execution?
4. How to integrate with existing Cohezion FastAPI service cleanly?
