# Cohezion Demo: 12D Manifold RL Environment

Evaluate the Cohezion system in 3 commands:

```bash
cd demo
uv run python quickstart.py        # Train agent for 50 episodes (~60s)
uv run python evaluate.py           # Compute FLUME metrics with 95% CIs
uv run python export_dataset.py     # Export DPO/RLHF training data
```

## What You'll See

### 1. `quickstart.py` - Training
Runs a Gymnasium-compatible RL environment (`ManifoldEnv`) where an agent
navigates a 12D Riemannian manifold governed by Lagrangian mechanics and
SU(2) spinor coherence. The environment uses a Stormer-Verlet symplectic
integrator for energy-conserving dynamics and a HIHO (0.5) attractor potential.

Output: per-episode coherence, reward, and steps. Trajectories saved to
`data/trajectories.json`.

### 2. `evaluate.py` - Statistical Analysis
Computes the 6 FLUME capability metrics from trajectory data:
- **Coherence Amplitude**: proximity to HIHO equilibrium (0.5 target)
- **Phase Locking Rate**: fraction of steps with SPIN alignment
- **Exotic Charge Lifetime**: consecutive steps maintaining charge sign
- **Orbit Quality**: smoothness of manifold trajectory (low jerk)
- **TRIUNE Balance Index**: equality across Space/Field/Control fabrics
- **Recovery Basin Radius**: how far from HIHO the agent can recover

Bootstrap 95% confidence intervals on all metrics. Optional radar chart
saved to `data/capability_radar.png`.

### 3. `export_dataset.py` - LLM Training Data
Converts trajectories into training signals for language models:
- `preferences.jsonl` - DPO preference pairs (chosen vs rejected by HIHO score)
- `rewards.jsonl` - Scalar reward labels for RLHF reward modeling
- `judgments.jsonl` - Per-decision judgment assessments for fine-tuning

## Architecture

```
ManifoldEnv (Gymnasium)
    |
    +-- LagrangianDynamics (Stormer-Verlet integrator)
    |       +-- fabric_block_metric (block-diagonal Riemannian metric)
    |       +-- hiho_potential (Gaussian attractor at 0.5)
    |
    +-- SpinorState (SU(2) Bloch sphere coherence)
    +-- FiberBundle (P(B^4, SO(3)^4) decomposition)
    +-- FourFabricGauge (Yang-Mills field strength)
```

## Requirements

- Python 3.12+, numpy, gymnasium (core deps of cohezion)
- matplotlib (optional, for radar chart)
- Install from repo root: `uv pip install -e .`
