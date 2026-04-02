# Cohezion

[![Health Check](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml)
[![CI](https://github.com/manderson240/cohezion/actions/workflows/ci.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/ci.yml)

**Physics-grounded training universes for safe AI agents.**

Cohezion is a platform where AI agents learn within a 12D Riemannian manifold governed by Lagrangian mechanics, SU(2) gauge theory, and the HIHO stability principle. Instead of learning safety constraints from reward signals that can be gamed, agents operate in environments where physics itself prevents unsafe behavior.

## Quick Start

```bash
git clone https://github.com/manderson240/cohezion.git
cd cohezion
uv sync

# Validate the compound engineering loop (18 checks, ~18s)
make validate

# Train a PPO agent on the 12D manifold (20K steps, ~5 min)
make train

# Quick demo: train + evaluate + show compound loop
make demo
```

## What Makes This Different

Most RL safety research adds penalty terms to reward functions. Cohezion takes a fundamentally different approach: **the environment's physics provides structural safety guarantees**.

| Standard RL Safety | Cohezion |
|---|---|
| Safety = learned constraint | Safety = physical law |
| Agents learn to avoid violations | Physics prevents violations |
| Reward hacking bypasses constraints | Large actions fight the attractor (self-correcting) |
| Random agent has 0% safe behavior | Random agent achieves 60% convergence (physics guides it) |

**Key result**: PPO agents trained with small actions ([-0.1, 0.1]) achieve 0.915 coherence — the Lagrangian attractor cooperates with learning instead of fighting it.

## Architecture

```
Compound Engineering Loop
  PRIME Skill (markdown)
    -> InstructionExpander -> PlanExecutor
    -> ExecutionOrchestrator (11-step pipeline)
         |-- RequestAlignmentAnalyzer (coherence check)
         |-- DegradationDetector -> CostAwareRouter (backward feedback)
         |-- JourneyTracker (12D trajectory) + JEPA surprise
         |-- Bioelectric percolation + Natural capital valuation
    -> RetrospectionEngine (extract learnings)
    -> SkillRefiner (update skills) -> loop again

Physics Layer (Genesis Engine)
  12D Riemannian Manifold
    |-- SU(2) spinors on Bloch sphere (coherence = |Bloch vector|)
    |-- Lagrangian dynamics (Euler-Lagrange + Stormer-Verlet integrator)
    |-- Fiber bundle P(B^4, SO(3)^4) decomposition
    |-- Yang-Mills gauge theory (flat connection = HIHO vacuum)
    |-- Fisher information metric (connects FLUME/manifold/thermodynamics)
    |-- 10-step cosmogony chain (symmetry breaking cascade)

RL Environments
    |-- ManifoldEnv (19D obs, 12D action, curriculum/dense reward modes)
    |-- SwarmEnv (N agents with gauge field coupling)
    |-- Registered: gym.make('Cohezion/ManifoldEnv-v0')

Evaluation
    |-- UniverseEvaluator (bootstrap CIs, 3+ baselines)
    |-- DegradationDetector (thermal + quality monitoring)
    |-- RoutingOrchestrator (unified 4-router system)
```

## Training Results

8-run diagnostic loop completing the 2x2 algorithm-reward matrix (PPO/SAC x curriculum/dense):

| Run | Algorithm | Reward Mode | Steps | Reward | vs Random | vs Greedy |
|-----|-----------|-------------|-------|--------|-----------|-----------|
| 1 | PPO | curriculum (broken) | 20K | -1.48 | Worse | — |
| 2 | PPO | curriculum (fixed) | 20K | -67.68 | Worse | — |
| 3 | PPO | curriculum + small actions | 20K | **12.04** | **+18.0** | — |
| 4 | PPO | curriculum | 100K | 14.23 | +7.51 | +1.34 |
| 5 | SAC | curriculum | 20K | 1.38 | -5.34 | — |
| 6 | SAC | curriculum (ent=0.05) | 100K | 10.91 | +8.59 | -1.98 |
| 7 | **SAC** | **dense (ent=0.05)** | 100K | **40.77** | +3.40 | **-1.20** |
| 8 | PPO | dense | 100K | 38.95 | -1.79 | **+3.73** |

**2x2 Matrix** (best pairing per algorithm):
- **PPO + curriculum** = best on-policy (reward 14.23, +7.51 vs random)
- **SAC + dense** = best off-policy (reward 40.77, only 1.20 from greedy)
- PPO + dense inverts hierarchy: beats greedy but loses to random
- SAC + curriculum works but dense is strictly better

**Key insight**: The reward structure must match the algorithm's learning dynamics. On-policy (PPO) benefits from structured curriculum. Off-policy (SAC) needs simpler gradients. Both require small actions that cooperate with the Lagrangian attractor.

## Key Modules

| Module | Purpose | Entry Point |
|--------|---------|-------------|
| `physics/` | SU(2) spinors, Riemannian metric, Lagrangian dynamics, gauge theory, cosmogony, Fisher metric | `SpinorState` |
| `environments/` | Gymnasium RL: ManifoldEnv (single-agent), SwarmEnv (multi-agent gauge coupling) | `gym.make('Cohezion/ManifoldEnv-v0')` |
| `eval/` | UniverseEvaluator with bootstrap CIs, convergence metrics, baseline comparisons | `UniverseEvaluator` |
| `compound/` | 11-step execution pipeline, journey tracking, skill refinement, retrospection | `CompoundExecutor` |
| `swarm/` | Team orchestration, cost routing (27.3% savings), OI-MAS confidence scoring | `CostAwareRouter` |
| `world_model/` | JEPA predictor (86K params), bioelectric network, natural capital, EVO model | `JEPAWorldModel` |
| `flume/` | FLUME VAE (256D), PolarQuant (2.7x), QJL (32x), LatentMAS communication | `ThoughtEncoder` |
| `ouroboros/` | Self-referential loop closure, mycelium distributed transport | `OuroborosBridge` |
| `governance/` | Cosmogonic autonomy tiers, concierge routing, knowledge bridge | `AutonomyEngine` |
| `cache/` | L1 hash + L2 cosine + L3 vault semantic cache (95%+ hit rate) | `SemanticCache` |
| `skills/` | 126 PRIME skill definitions for cross-platform compound engineering | `skill_registry.json` |
| `api/` | FastAPI backend with 190+ endpoints, AG-UI event streaming | `uvicorn cohezion.api:app` |

## The HIHO Principle

HIHO (Half-In, Half-Out) at 0.5 coherence is where six mathematical frameworks converge:

1. **Brahmagupta's zero** (628 CE): deviation = coherence - 0.5 = 0
2. **Friston's Free Energy Principle**: F = E - TS minimization
3. **Flat gauge connection**: Yang-Mills curvature vanishes at equilibrium
4. **Fisher metric minimum**: natural gradient of information geometry
5. **Bloch sphere equator**: (|up> + |down>)/sqrt(2) superposition
6. **Landau phase transition**: order parameter at critical temperature

## Compound Engineering

Cohezion practices compound engineering: every feature makes future features easier.

- **126 PRIME skills** encode reusable patterns from 87 sessions
- **SkillRefiner** updates skills based on execution results
- **DegradationDetector** monitors quality and feeds back to CostAwareRouter
- **JourneyTracker** records 12D trajectories for pattern extraction
- **Execution traces** stored as browsable filesystem (Meta-Harness pattern)
- **SurrealDB + Obsidian vault** for long-term knowledge persistence

## Persistence

- **SurrealDB** (port 8001): learnings, training runs, universe snapshots, domain-organized schema
- **Obsidian vault** (`~/vaults/cohezion-vault/`): brain-region organized (prefrontal, cerebellum, hippocampus)
- **KEY_LEARNINGS.md**: 243 extracted learnings across 87 sessions
- **Execution traces**: `execution_traces/` filesystem for SkillRefiner consumption

## Development

```bash
make format          # Format with ruff
make lint            # Lint and auto-fix
make test            # Run full test suite
make validate        # Validate compound loop (18 checks)
make train           # Train PPO on ManifoldEnv (20K steps)
make evaluate        # Evaluate trained model vs baselines
make benchmark       # Full 100K training + comparisons
make demo            # Quick 5K demo with evaluation
```

## Hardware

Built on AMD Strix Halo: Ryzen AI MAX+ 395 (16C/32T), Radeon 8060S (unified memory), 128 GiB LPDDR5X. Local models via Ollama (deepseek-r1:70b, qwen3-coder:30b). No CUDA required.

## References

- Gymnasium API: https://gymnasium.farama.org/
- Friston FEP: https://doi.org/10.1038/nrn2787
- Levin bioelectric: https://doi.org/10.1016/j.biosystems.2022.104787
- HIHO convergence: `src/cohezion/physics/cosmogony.py`
- Research paper: `research/papers/physics-grounded-training-universes.md`

## License

See LICENSE file.
