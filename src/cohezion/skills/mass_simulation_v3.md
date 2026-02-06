# SKILL: MASS_SIMULATION_V3_PRIME

## DOMAIN EXPERTISE
Specialist in **Rust-accelerated mass simulation** of agentic journeys through FLUME manifold space. Orchestrates millions of agents across unique universe configurations using rayon-parallelized batch evolution with OOM-safe adaptive throttling.

## KEY CONCEPTS
- **Universe = Weight Configuration**: Each universe is a unique FlumePhysics neural navigator (w1, b1, w2, b2, gamma, beta)
- **Agent = Initial Latent State**: 256D vector in FLUME manifold space
- **Year = Epoch**: One forward pass through the neural navigator
- **HIHO Coherence**: Stability target at 0.5 (Half-In-Half-Out)
- **Holographic Projection**: 2048D/256D latent -> 12D axiomatic via Rust FlumePhysics

## MATHEMATICAL FOUNDATION
Navigator evolution: z_{t+1} = z_t + Navigator(z_t) where Navigator = Linear -> ReLU -> LayerNorm -> Linear
Coherence: C(z) = 1 - min(4 * Var(project_12D(z) - 0.5), 1)
Stability bounds: 0.3 <= C(z) <= 0.7 (HIHO window)

## ARCHITECTURE

### Scale Tiers
| Tier | Agents | Epochs | Universes | Time |
|------|--------|--------|-----------|------|
| demo | 100 | 1,000 | 10 | ~10s |
| medium | 1,000 | 10,000 | 100 | ~2m |
| overnight | 10,000 | 100,000 | 1,000 | ~3h |
| aspirational | 25M | 10M | 1M | cluster |

### Module Layout
```
src/cohezion/mass_sim/
  config.py           # ScaleTier, SimulationConfig
  universe_factory.py # Seed -> FlumePhysics weights (Xavier init)
  agent_factory.py    # Seed -> [n_agents, 256] population
  batch_runner.py     # Rust inner loop with OOM-safe batching
  orchestrator.py     # MassSimOrchestrator (top-level coordinator)
  persistence.py      # SurrealDB batch writes + JSONL fallback
  analysis.py         # Anthropic-style safety/convergence/diversity metrics
  artifacts.py        # matplotlib visualizations (Agg backend)
  system_monitor.py   # /proc-based memory guard, adaptive batch sizing
```

### Rust Core (cohezion_core_rs)
- `simulate_epochs_navigated(batch, epochs)` - Full neural navigator per epoch
- `simulate_with_checkpoints(batch, epochs, interval, nav)` - Periodic snapshots
- `compute_batch_stats(batch)` - Parallel coherence, norms, bounds checking

## INSTRUCTION

### Quick Start
```python
from cohezion.mass_sim import MassSimOrchestrator, SimulationConfig, SCALE_TIERS

config = SimulationConfig(scale=SCALE_TIERS["demo"])
orchestrator = MassSimOrchestrator(config)
report = await orchestrator.run()
print(report.summary_dict())
```

### CLI
```bash
uv run python mass_sim_driver.py --scale demo
uv run python mass_sim_driver.py --scale medium --agents 500 --epochs 5000
```

### Overnight (Unattended)
```bash
MASS_SIM_SCALE=medium ./scripts/overnight/run_mass_sim.sh
```

## OOM PROTECTION
- MemoryGuard reads /proc/self/status and /proc/meminfo
- Adaptive batch sizing: halves when RSS > 100GB or avail < 20GB
- Abort threshold: RSS > 115GB or avail < 5GB or swap > 20GB
- All thresholds tuned for Strix Halo (128GB unified LPDDR5X)

## ANTHROPIC-STYLE ANALYSIS
- **Safety alignment**: % agents within HIHO coherence bounds
- **Convergence rate**: epochs to reach 0.5 stability per universe
- **Diversity**: effective dimensionality of final population states
- **Universe stability ranking**: which weight configs produce stable populations
- **Anomaly detection**: universes/agents > 2σ from population mean

## PERSISTENCE
- SurrealDB tables: mass_sim_run, sim_universe_summary, sim_checkpoint, sim_analysis_report, sim_artifact
- Fallback: JSONL files in data/mass_sim/checkpoints/jsonl/
- Artifacts: PNG plots in data/mass_sim/artifacts/

## VERSION
v3.0 (Rust-accelerated, OOM-safe, Anthropic-style analysis)

## SEE ALSO
- QUADRATURE_PRIME.md
- FLUME_METHODOLOGY_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
