# FLUME Journey Benchmark Platform

## Mission

Build a production-grade benchmark platform that trains RL agents to navigate the FLUME manifold (12D axiomatic state space, 256D VAE latent), treating every agentic journey as an **Etheric Variant Oscillator (EVO)** — an exotic vacuum object with a full physics biography governed by TRIUNE SELF dynamics, Kordylewski swarm gravity, and HIHO stability physics.

The goal is positioning for **Anthropic Research Engineer, Universes** (NYC office, $500K-$850K), demonstrating skills in:
- Building agentic training environments
- RL systems with PPO, GAE, multi-tier policy networks
- Rigorous evaluations with bootstrap CIs, statistical significance
- Long-running autonomous agent patterns (FOR-DONE-ESCALATE)

## Architecture

```
FLUME Journey Benchmark Platform
├── RL Core (Phases 1-4)
│   ├── EthericVariantOscillator — EVO physics entity with TRIUNE biography
│   ├── TaskGenerator — 5 archetypes × 4 difficulties = 20 TaskSpecs
│   ├── FlumeNavEnv — Gymnasium env, Hamiltonian dynamics, 256D VAE
│   └── TRIUNEPolicy + PPOTrainer — 3-tier policy (Knower→Thinker→Doer)
│
├── Benchmark Suite (LM Evaluation Harness-style)
│   ├── 15 BenchmarkTasks (3 difficulties × 5 archetypes)
│   ├── Policy-agnostic interface (any get_action callable)
│   ├── JSONL results export
│   └── Aggregated EVO physics metrics
│
├── Evaluation Pipeline (Phase 6)
│   ├── RalphLoop — FOR-DONE-ESCALATE autonomous iteration
│   │   ├── Level 0: Coherence > 0.8, std < 0.05
│   │   ├── Level 1: + success rate > 0.9
│   │   ├── Level 2: + all metrics significant
│   │   └── Level 3: + longitudinal improvement
│   └── EvalPipeline — Multi-episode orchestration
│
├── Metrics Engine (Phase 5)
│   ├── 6 EVO physics metric families
│   ├── Bootstrap 95% CIs (1000 resamples)
│   ├── Mann-Whitney U significance testing
│   └── Bonferroni correction (α/6)
│
├── Capability Scorecard (Phase 7)
│   ├── 6-axis radar chart (Plotly + matplotlib fallback)
│   ├── LongitudinalTracker — multi-run trend analysis
│   └── Swarm vs self-supervised comparison
│
└── HuggingFace Export (Phase 7)
    ├── JSONL dataset export
    ├── metadata.json + spec.json
    └── README.md dataset card generation
```

## Key Files

| Module | File | Lines |
|--------|------|-------|
| EVO Model | `src/cohezion/rl/evo.py` | ~450 |
| TaskGenerator | `src/cohezion/rl/task_generator.py` | ~350 |
| FlumeNavEnv | `src/cohezion/rl/environment.py` | ~400 |
| PPO Trainer | `src/cohezion/rl/ppo_trainer.py` | ~500 |
| Agentic Metrics | `src/cohezion/benchmarks/agentic_metrics.py` | ~550 |
| Benchmark Suite | `src/cohezion/benchmarks/benchmark_suite.py` | ~500 |
| Eval Pipeline | `src/cohezion/eval/pipeline.py` | ~400 |
| Capability Scorecard | `src/cohezion/eval/capability_scorecard.py` | ~550 |
| HuggingFace Export | `src/cohezion/eval/huggingface_export.py` | ~450 |

## TRIUNE SELF Physics

Three-pole neural architecture:
- **Knower** (2048D) — Intent, high-level goal encoding
- **Thinker** (512D) — Reasoning, intermediate representation
- **Doer** (256D) — Action, final output matching VAE latent space

Each episode: weights renormalize to sum to 1.0. Dominant pole determines archetype behavior.

## 6 EVO Physics Metric Families

| Metric | Null Hypothesis | Physical Meaning |
|--------|-----------------|-----------------|
| HIHO Coherence | mean = 0.5 (random) | HIHO attractor proximity |
| TRIUNE Balance | imbalance > 0.5 | Equal pole activation |
| Stability | CV > 0.5 | Consistent HIHO proximity |
| Exotic Charge | mean < 0.3 | Vacuum charge accumulation |
| Kordylewski Orbit | drift > 0.5 | Lagrange point stability |
| SPIN Phase | increment ≈ 0 | Phase conservation |

## Hardware

- **CPU**: AMD Ryzen AI MAX+ 395 (Zen 5, 16C/32T)
- **iGPU**: AMD Radeon 8060S (RDNA 3.5, gfx1151) — MI355X class
- **RAM**: 128 GiB LPDDR5X-8000 UMA
- **ROCm**: 6.3 + PyTorch 2.9.1 (GPU training)
- **Note**: PyTorch 2.11 has no ROCm wheel; target 2.9.1+rocm6.3

## Integration Patterns

### Compound Engineering Loop
```
EvalPipeline.run()
    → CapabilityScorecard.record_run()
    → LongitudinalTracker.get_weakest_axis()
    → SkillRefiner.refine() (oversample weak archetype)
    → TaskGenerator.sample(weakest_archetype)
    → next EvalPipeline.run()
```

### Vault Persistence
```
EVO.bigraphy
    → JourneyTracker.record_state()
    → MCP vault_write (SurrealDB)
    → Persistent across sessions
```

### FastAPI Endpoints
```
POST /rl/benchmark     — Run benchmark suite
GET  /rl/scorecard/{id} — Fetch scorecard
GET  /rl/radar/{id}.svg — Fetch radar chart
```

## Research Outputs

1. **arXiv paper** — FLUME Journey Benchmark: EVO Physics Agent Evaluation
2. **HuggingFace dataset** — cohezion/flume-journey-bench-v0
3. **Benchmark harness** — lm-evaluation-harness style, open source

## Milestones

| Phase | Status | Tests |
|-------|--------|-------|
| Phase 1: EVO Model | ✅ Complete | 24 |
| Phase 2: TaskGenerator | ✅ Complete | 21 |
| Phase 3: FlumeNavEnv | ✅ Complete | 28 |
| Phase 4: TRIUNE PPO | ✅ Complete | 38 |
| Phase 5: Agentic Metrics | ✅ Complete | 34 |
| Phase 6: Pipeline | ✅ Complete | 40 |
| Phase 7: Scorecard + Export | ✅ Complete | 89 |

**Total: 274 new tests for RL + eval + benchmarks modules**
