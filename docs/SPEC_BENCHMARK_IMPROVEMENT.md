# COHEZION Benchmark Improvement System - SPEC.md

## Vision
Build an autonomous, self-improving benchmark system that uses FLUME journey tracking to optimize code generation performance, aligned with Anthropic Research Engineer (Universes) goals.

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                    BENCHMARK ORCHESTRATOR                       │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────────────┐ │
│  │ HumanEval    │  │ SWE-bench    │  │ AgentBench           │ │
│  │ Runner       │  │ Runner       │  │ Runner               │ │
│  └──────┬───────┘  └──────┬───────┘  └──────────┬───────────┘ │
└─────────┼──────────────────┼──────────────────────┼─────────────┘
          │                  │                      │
          ▼                  ▼                      ▼
┌─────────────────────────────────────────────────────────────────┐
│                   JOURNEY TRACKER LAYER                         │
│  ┌──────────────────────────────────────────────────────────┐   │
│  │ 12D Physics State → phi_score → coherence → HIHO        │   │
│  └──────────────────────────────────────────────────────────┘   │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   FLUME LATENT SPACE                            │
│  256D VAE with HIHO stability optimization                     │
└─────────────────────────────────────────────────────────────────┘
          │
          ▼
┌─────────────────────────────────────────────────────────────────┐
│                   IMPROVEMENT LOOP                              │
│  1. Run benchmarks → 2. Track journeys → 3. Analyze patterns  │
│  4. Identify successful patterns → 5. Fine-tune/adjust        │
└─────────────────────────────────────────────────────────────────┘
```

## Components

### 1. Benchmark Orchestrator
- **Location**: `src/cohezion/eval/orchestrator.py`
- **Purpose**: Coordinate benchmark runs across HumanEval, SWE-bench, AgentBench
- **Features**: Parallel execution, result aggregation, model comparison

### 2. Journey-Enhanced Runner
- **Location**: `src/cohezion/eval/journey_runner.py`
- **Purpose**: Inject FLUME journey tracking into benchmark generation
- **Features**: Real-time phi_score computation, coherence monitoring

### 3. Pattern Analyzer
- **Location**: `src/cohezion/eval/pattern_analyzer.py`
- **Purpose**: Identify success patterns from journey data
- **Features**: Statistical analysis, correlation discovery, recommendation generation

### 4. Self-Correction Loop
- **Location**: `src/cohezion/eval/self_correction.py`
- **Purpose**: Generate → Test → Regenerate on failure
- **Features**: Configurable retry limits, timeout handling, best-of-n selection

### 5. Fine-Tuning Pipeline
- **Location**: `src/cohezion/training/finetune_pipeline.py`
- **Purpose**: Create domain-specific models from successful patterns
- **Features**: LoRA support, dataset generation, evaluation

## Milestones (Git-Safe Handoffs)

### Milestone 1: Orchestrator Foundation (Git branch: `milestone/orchestrator`)
- [ ] BenchmarkOrchestrator class
- [ ] Parallel execution support
- [ ] Result aggregation
- **Handoff**: Commit with tag `milestone-1-complete`

### Milestone 2: Journey Integration (Git branch: `milestone/journey`)
- [ ] Journey-enhanced benchmark runner
- [ ] Real-time phi_score tracking
- [ ] Coherence monitoring
- **Handoff**: Commit with tag `milestone-2-complete`

### Milestone 3: Pattern Analysis (Git branch: `milestone/patterns`)
- [ ] Success/failure pattern extraction
- [ ] Correlation analysis
- [ ] Recommendation engine
- **Handoff**: Commit with tag `milestone-3-complete`

### Milestone 4: Self-Correction (Git branch: `milestone/self-correction`)
- [ ] Generate-test-regenerate loop
- [ ] Best-of-n selection
- [ ] Timeout handling
- **Handoff**: Commit with tag `milestone-4-complete`

### Milestone 5: End-to-End (Git branch: `milestone/e2e`)
- [ ] Full pipeline integration
- [ ] CLI interface
- [ ] Results dashboard
- **Handoff**: Commit with tag `milestone-5-complete`

## Token Efficiency Strategies

1. **Batch similar tasks** - Run multiple benchmarks in parallel
2. **Cache journey data** - Don't recompute FLUME metrics
3. **Incremental analysis** - Analyze patterns as data arrives
4. **Git handoffs** - Branch-based work allows resume without full context
5. **Checkpointing** - Save progress after each milestone

## Anthropic Alignment

This system directly aligns with Anthropic Research Engineer (Universes) requirements:

| Requirement | Implementation |
|-------------|----------------|
| Build agentic environments | FLUME journey tracking for agent behavior |
| Rigorous evaluations | SWE-bench, HumanEval, AgentBench |
| Cross-research-production | Continuous improvement loop |
| Debug/iterate rapidly | Self-correction and pattern analysis |

## Success Metrics

- HumanEval pass@10: >30% (from 0%)
- SWE-bench resolution: >10% 
- AgentBench overall: >40%
- Journey-coherence correlation: >0.7
