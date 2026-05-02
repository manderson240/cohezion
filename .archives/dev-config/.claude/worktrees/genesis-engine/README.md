# Cohezion

[![Health Check](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml)
[![CI](https://github.com/manderson240/cohezion/actions/workflows/ci.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/ci.yml)
[![Security](https://img.shields.io/badge/security-bandit-blue)](https://github.com/manderson240/cohezion)

**Training environments, evaluation systems, and ML infrastructure for agentic AI operating in simulated universes.**

## 🚀 Genesis Engine Production System

**NEW**: Session 80 — Genesis Engine Unification Complete.
- ✅ **120+ PRIME skills** unified across 13 worktrees (non-destructive archival)
- ✅ **Genesis Engine Active**: Compound executor, unified registry, vault queue
- ✅ **"As Above, So Below"**: Worktree structure mirrored in unified codebase
- ✅ **Competition Sustainment**: Active monitoring during infrastructure refactoring
- ✅ **AMD Research Extracted**: 4 new PRIME skills from $4.4M competition research
- ✅ **Production ready**

### Quick Start
```bash
# Run complete optimization
uv run python3 production_scheduler.py --mode full

# Validate system
uv run python3 production_scheduler.py --mode validate

# Deploy to production
./deploy_production.sh
```

**📊 Validation Report**: See `PRODUCTION_VALIDATION.md` for complete results.

Cohezion is a framework for building and evaluating autonomous agents that perform long-horizon tasks within a 12-dimensional simulated universe. Agents navigate continuous latent spaces, coordinate in multi-agent swarms, and are evaluated through trajectory-based coherence metrics — all within sandboxed, reproducible environments.

---

## What This Project Demonstrates

### Training Environments for Agentic AI

Agents operate in a **12D/2048D dual-state manifold** — a simulated universe where every task becomes a measurable trajectory through continuous space. The 12D axiomatic layer captures observable state (spatial, temporal, physics, biology, logic, quantum, field, control, novelty, precipitation), while the 2048D latent layer encodes semantic intent and reasoning.

- **Universe simulation engine** with trajectory tracking, coherence scoring, and deterministic replay ([`src/cohezion/universe/engine.py`](src/cohezion/universe/engine.py))
- **Fractal universe simulator** — grid-based environment where stabilizer agents maintain HIHO coherence across manifold sectors ([`src/cohezion/simulation/fractal_universe.py`](src/cohezion/simulation/fractal_universe.py))
- **Gymnasium-compatible RL environment** (`FlumeNav-v0`) with 256D continuous observation/action spaces and Hamiltonian dynamics ([`src/cohezion/rl/environment.py`](src/cohezion/rl/environment.py))

### RL Training and Latent Space Navigation

A REINFORCE policy network learns to navigate the FLUME latent space toward a target coherence of 0.5 (the HIHO stability point — a double-well attractor in the energy landscape).

- **REINFORCE trainer** with Gaussian policy, composable reward shaping, and episode checkpointing ([`src/cohezion/rl/trainer.py`](src/cohezion/rl/trainer.py))
- **Reward shaping** — coherence reward (Gaussian peak at target), diversity bonus (prevents dimensional collapse), smoothness penalty ([`src/cohezion/rl/reward_shaping.py`](src/cohezion/rl/reward_shaping.py))
- **Trained results**: 0.991 avg coherence, 92.7% of executions within HIHO band (0.4–0.6), stable over 25M simulation cycles

### FLUME VAE (Thought Autoencoder)

A variational autoencoder that compresses text into 256D continuous "thought vectors," enabling interpolation between concepts and trajectory prediction in semantic space.

- **Architecture**: Transformer encoder/decoder with 256D latent bottleneck ([`src/cohezion/flume/autoencoder.py`](src/cohezion/flume/autoencoder.py))
- **Training pipeline**: Incremental training with checkpointing, trained on 11K vectors from simulation data ([`src/cohezion/flume/training.py`](src/cohezion/flume/training.py))
- **Metrics**: MSE 0.1322, KL divergence 0.4329 (real data), mean coherence 0.63 +/- 0.15

### Evaluation Systems

Rather than pass/fail benchmarks, Cohezion evaluates agents through continuous trajectory analysis:

- **Coherence tracking** — per-step measurement of agent alignment with the HIHO stability point
- **Degradation detection** — thermal forecasting and quality threshold monitoring that catches coherence collapse before it happens ([`src/cohezion/compound/degradation_detector.py`](src/cohezion/compound/degradation_detector.py))
- **Request alignment analysis** — pre-execution assessment of whether an agent's capabilities match the task ([`src/cohezion/compound/request_alignment_analyzer.py`](src/cohezion/compound/request_alignment_analyzer.py))
- **Phi score** — composite quality metric: 0.5 * coherence + 0.3 * smoothness + 0.2 * convergence
- **Journey tracking** — full 12D trajectory recording with anomaly detection for debugging and skill refinement ([`src/cohezion/compound/journey_tracker.py`](src/cohezion/compound/journey_tracker.py))

### Multi-Agent Orchestration

Agents coordinate through a swarm architecture with dependency-aware execution:

- **Team orchestrator** — decomposes tasks and assigns to specialist agents (Architect, Engineer, Biologist, Quantum HW, Quantum Algo) ([`src/cohezion/swarm/team_orchestrator.py`](src/cohezion/swarm/team_orchestrator.py))
- **Execution orchestrator** — topological sorting, parallel independent tasks, aggregated reporting ([`src/cohezion/swarm/execution_orchestrator.py`](src/cohezion/swarm/execution_orchestrator.py))
- **Cost-aware model routing** — routes to the cheapest model meeting quality thresholds, 27.3% cost reduction ([`src/cohezion/swarm/cost_aware_router.py`](src/cohezion/swarm/cost_aware_router.py))

### Sandboxed Execution

All agent execution runs in isolation with resource governance:

- **Container-based sandboxing** with CPU/memory/disk limits and OOM detection ([`src/cohezion/sandbox/executor.py`](src/cohezion/sandbox/executor.py))
- **Rollback support** — checkpoint-based recovery for deterministic replay ([`src/cohezion/sandbox/rollback.py`](src/cohezion/sandbox/rollback.py))
- **Universe sandbox manager** with multiple isolation backends and security profiles ([`src/cohezion/universe/sandbox_manager.py`](src/cohezion/universe/sandbox_manager.py))

---

## Architecture

```
                    ┌─────────────────────────────────────────────┐
                    │           Compound Engineering Loop          │
                    │                                             │
  PRIME Skill ──>   │  InstructionExpander ──> PlanExecutor       │
  (markdown)        │       │                      │              │
                    │       v                      v              │
                    │  ExecutionOrchestrator (11-step pipeline)   │
                    │       │                                     │
                    │       ├── RequestAlignmentAnalyzer          │
                    │       ├── GlobalMetricsAggregator           │
                    │       ├── DegradationDetector               │
                    │       └── JourneyTracker (12D)              │
                    │       │                                     │
                    │       v                                     │
                    │  RetrospectionEngine ──> SkillRefiner       │
                    │       │                      │              │
                    │       v                      v              │
                    │  SkillConsensusVoter ──> Updated Skill ─┐   │
                    │                                         │   │
                    └─────────────────────────────────(loop)───┘   │
                                                                   │
    ┌──────────────────────────────────────────────────────────────┘
    │
    v
┌─────────────────────────────────────────────────┐
│              Universe Simulation Layer            │
│                                                  │
│  12D/2048D Dual-State Manifold                   │
│  ├── AxiomaticState (12D observable)             │
│  ├── LatentState (2048D semantic intent)         │
│  └── TrajectoryPoint (per-step recording)        │
│                                                  │
│  FlumeNav-v0 (Gymnasium RL Environment)          │
│  ├── 256D observation/action spaces              │
│  ├── Hamiltonian dynamics + thermal noise        │
│  └── Composable reward shaping                   │
│                                                  │
│  FLUME VAE (Thought Autoencoder)                 │
│  ├── Transformer encoder → 256D latent → decoder │
│  └── Continuous interpolation in thought-space   │
└──────────────────────────────────────────────────┘
```

---

## Key Modules

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| [`universe/`](src/cohezion/universe/) | 12D/2048D simulation engine, trajectory tracking | `UniverseSimulationEngine` |
| [`simulation/`](src/cohezion/simulation/) | Fractal universe, grid-based multi-agent environments | `FractalSimulator` |
| [`rl/`](src/cohezion/rl/) | Gymnasium environment, REINFORCE trainer, reward shaping | `FlumeNavEnv` |
| [`flume/`](src/cohezion/flume/) | VAE autoencoder, latent space navigation, training | `ThoughtEncoder` |
| [`compound/`](src/cohezion/compound/) | Compound execution loop, journey tracking, skill refinement | `CompoundExecutor` |
| [`swarm/`](src/cohezion/swarm/) | Multi-agent orchestration, cost routing, model selection | `ExecutionOrchestrator` |
| [`sandbox/`](src/cohezion/sandbox/) | Container isolation, resource limits, rollback | `SandboxExecutor` |
| [`cache/`](src/cohezion/cache/) | L1 hash + L2 cosine + L3 vault semantic cache (95%+ hit rate) | `SemanticCache` |
| [`persistence/`](src/cohezion/persistence/) | SurrealDB + JSONL checkpoint storage | `SessionManager` |
| [`security/`](src/cohezion/security/) | Prompt guardrails, output filtering | `GuardrailPipeline` |
| [`reliability/`](src/cohezion/reliability/) | Circuit breakers, resource monitoring | `get_circuit()` |
| [`api/`](src/cohezion/api/) | FastAPI server (72 endpoints) | `app` |

---

## Quick Start

```bash
# Requirements: Python 3.13+, uv package manager
git clone https://github.com/manderson240/cohezion.git
cd cohezion
uv sync

# Run the test suite (3,200+ tests)
uv run pytest tests/ -q

# Start the API server
uv run uvicorn cohezion.api:app --reload --port 8080

# Run the fractal universe simulator
uv run python src/cohezion/simulation/fractal_universe.py --duration 1h
```

### RL Training Example

```python
from cohezion.rl.environment import FlumeNavEnv
from cohezion.rl.trainer import PolicyNetwork, TrainingConfig, train

# Train a REINFORCE policy to navigate toward HIHO coherence
config = TrainingConfig(n_episodes=100, lr=3e-4, gamma=0.99)
results = train(config)

# Inspect training trajectory
for r in results[-5:]:
    print(f"Episode {r.episode}: coherence={r.mean_coherence:.3f}, reward={r.total_reward:.1f}")

# Evaluate directly with the Gymnasium environment
env = FlumeNavEnv(z_dim=256, max_steps=200, use_hamiltonian=True)
policy = PolicyNetwork(state_dim=256, action_dim=256)
obs, _ = env.reset()
for _ in range(200):
    action, _ = policy.get_action(obs)
    obs, reward, done, _, info = env.step(action)
    print(f"Coherence: {info['coherence']:.3f}")
    if done:
        break
```

### Universe Simulation Example

```python
import asyncio
from cohezion.universe.engine import UniverseSimulationEngine, AxiomaticState

async def main():
    engine = UniverseSimulationEngine()

    # Start a journey through the 12D/2048D manifold
    journey = await engine.start_journey(
        agent_name="researcher-1",
        intent="Explore coherence stability in quantum dimensions",
    )

    # Each step records a TrajectoryPoint with 12D axiomatic + 2048D latent state
    print(f"Journey {journey.id}: coherence={journey.initial_axiomatic.coherence_score():.3f}")
    print(f"12D state: {journey.initial_axiomatic.to_vector()}")

asyncio.run(main())
```

### Compound Execution Loop

```python
from cohezion.compound import CompoundExecutor, ExecutorFactory
from cohezion.core.mcp_client import MCPClient

# The compound loop: execute -> evaluate -> refine -> repeat
executor = ExecutorFactory.create(MCPClient(config={}))

result = executor.execute_task(
    task_description="Navigate latent space to discover stable manifold regions",
    skill_name="explorer",
    operation_type="generate",
    execute_fn=exploration_function,
)

# Result includes trajectory data, coherence scores, token metrics
print(f"Success: {result.success}")
print(f"Duration: {result.duration_seconds:.1f}s")
print(f"Metrics: {result.metrics}")
```

---

## Testing

```bash
# Full suite
uv run pytest tests/ -q  # 3,486 pass; SurrealDB integration tests require live DB

# By module
uv run pytest tests/compound/ -v       # Compound engineering (275 tests)
uv run pytest tests/flume/ -v          # FLUME VAE
uv run pytest tests/swarm/ -v          # Multi-agent swarm
uv run pytest tests/integration/ -v    # End-to-end

# With coverage
uv run pytest tests/ --cov=src/cohezion --cov-report=html

# Lint and format
make format && make lint && make type-check
```

---

## Technical Stack

- **Language**: Python 3.13+
- **ML**: PyTorch (VAE, RL policy), Gymnasium (RL environments), sentence-transformers (embeddings)
- **Backend**: FastAPI, SurrealDB (async), JSONL fallback
- **Inference**: Ollama (local models), Anthropic API, cost-aware model routing
- **Quality**: ruff (format + lint, 203 errors remaining), mypy (type checking), pytest (3,486 passing)
- **Deployment**: Docker, Cloud Run, systemd

---

## Project Metrics

| Metric | Value |
|--------|-------|
| Source modules | 391 Python files across 68 packages |
| Test functions | 3,530 collected |
| Test pass rate | 3,486 passing / 0 failing (SurrealDB integration tests require live DB) |
| PRIME skill definitions | 74 (registry) / 134 (.md files) |
| API endpoints | 72 |
| RL coherence (trained) | 0.991 avg |
| HIHO band compliance | 92.7% of executions |
| Simulation stability | 25M cycles |
| Cache hit rate | 95%+ |
| Cost reduction (routing) | 27.3% |

---

## License

See LICENSE file for details.

## Citation

```bibtex
@software{cohezion2026,
  title={Cohezion: Training Environments and Evaluation Systems for Agentic AI},
  author={Anderson, Mike},
  year={2026},
  url={https://github.com/manderson240/cohezion}
}
```
