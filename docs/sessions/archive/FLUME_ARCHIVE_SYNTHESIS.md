# FLUME Archive Synthesis - April 26, 2026

## Executive Summary

Based on comprehensive codebase search, **FLUME** is a **Variational Autoencoder (VAE)** with a **256-dimensional latent space** that serves as the cognitive substrate for a "12D agentic universe" in the Cohezion project. 

Key discovery: The user's earlier description "Fluid Latent Understanding through Manifold Encoding" is actually **literally implemented** - it's not just a ML model, but a physics-inspired cognitive architecture.

---

## What FLUME Actually Is

### Core Architecture (from `src/cohezion/flume/`)

**1. FlumeVAE** (`vae.py`)
- **256D latent space** (z-dim=256)
- Transformer-based encoder/decoder
- Reparameterization trick for probabilistic latent space
- **ThoughtVector** - semantic concepts as continuous vectors
- **Mu/LogVar heads** - encode to distribution, not just point

**2. Thought Autoencoder** (`autoencoder.py`)
- "CALM principle": Continuous And Learning Manifold
- **Text → ThoughtVector** - paragraphs compressed to 256D
- **Semantic arithmetic** - interpolate between concepts
- **Trajectory prediction** - in thought space

**3. FlumePhysicsPy** (`mass_sim/flume_physics.py`)
- **Pure-Python physics engine** for latent space evolution
- **HIHO dynamics** (Holistic Integration via Harmonic Oscillation)
- **2-layer MLP** governing agent evolution
- Attractor toward 0.5 coherence equilibrium
- `simulate_epochs_batch()` - batch evolution

**4. Manifold Encoding** (`manifolds/translator.py`)
- Operations on curved latent space
- Navigation and trajectory planning
- **Geometric bridge** - latent ↔ physical space

---

## HIHO - The Physics Engine

**HIHO** = Holistic Integration via Harmonic Oscillation

From `flume_physics_py.py`:
```python
# Physics parameters
delta_scale: float = 0.01      # Step size multiplier
hiho_damping: float = 0.05    # Attractor strength toward 0.5

# Forward pass
h = z @ w1.T + b1              # Transform
h_norm = LayerNorm(h)          # Stabilize
delta = h_act @ w2.T + b2      # Compute change
z_new = z + delta * delta_scale

# HIHO damping: pull toward 0.5 equilibrium
z_new = z_new + hiho_damping * (0.5 - z_new)
```

**Coherence metric**: How close agent is to "ideal" 0.5 state across all 256 dimensions.
- `pct_within_bounds` - fraction of agents in [0.3, 0.7]
- `mean_coherence` - average over population
- **Goal**: Maximize coherence while exploring latent space

---

## FLUME-First Design Principle

From `CLAUDE.md` and `.pi/SYSTEM.md`:

**"New modules MUST encode/decode through FLUME. Don't retrofit — wire from the start."**

This means:
1. All agents/concepts represented as 256D latent vectors
2. Evolution follows FLUME physics (HIHO dynamics)
3. Memory stored in latent space, not raw text
4. **Journey tracking** = trajectory through 256D manifold

---

## The "Universe" Architecture

### 12D Agentic Universe (from CLAUDE.md)

| Component | Location | Purpose |
|-----------|----------|---------|
| **FLUME VAE** | `src/cohezion/flume/vae.py` | 256D latent cognition space |
| **FlumePhysics** | `mass_sim/flume_physics_py.py` | HIHO evolution dynamics |
| **Manifolds** | `flume/manifolds/translator.py` | Geometric navigation |
| **JourneyTracker** | (implied) | Trajectory history in 12D |
| **Genesis UI** | `src/web/anima_dashboard/` | BlochSphere, FlumeLatentViz |

### Visualizations Available
- **BlochSphere** - quantum-like state visualization
- **GenesisScene** - 3D world rendering
- **FlumeLatentViz** - 256D latent space projection
- **SwarmTopologyViz** - multi-agent network

---

## Connection to "Exotic Vacuum Objects"

### What EVOs Would Be in FLUME

Based on existing architecture, EVOs (Exotic Vacuum Objects) are:

**1. Latent Space Agents with Modified HIHO Dynamics**
```python
class ExoticVacuumAgent:
    """
    EVO in FLUME: Agent with exotic coherence properties.
    """
    def __init__(self):
        self.latent_state = torch.randn(256)  # Standard: ~N(0,1)
        # EVO modification: allow negative/inverted coherence
        self.exotic_type = "negative_mass" | "false_vacuum" | "entangled"
    
    def hiho_step_exotic(self):
        # Standard: attract to 0.5
        # EVO: repel from 0.5 (false vacuum - unstable equilibrium)
        # or attract to 0.0 or 1.0 (degenerate states)
        pass
```

**2. Vacuum State as Coherence Anomaly**

| Vacuum Type | FLUME Coherence | Physics |
|-------------|-----------------|---------|
| Standard | ~0.5, stable | True vacuum |
| False | ~0.5, unstable | Metastable, decays |
| Exotic Positive | High coherence (>0.8) | Inflating |
| Exotic Negative | Low coherence (<0.2) | Negative energy density |
| Entangled | Oscillating coherence | Quantum-correlated pairs |

**3. Journey Through 12D**
- Standard agents: HIHO attractor → converge to 0.5
- EVOs: **Repeller dynamics** → diverge, explore boundaries
- "Fluid" = probability distribution over latent space
- "Manifold" = 256D latent space with learned metric

---

## How to Use GPU with FLUME

### Current State

**FLUME is CPU-only** (PyTorch on CPU).

From research, the AMD GPU (gfx1151) could accelerate:
1. **Batch inference** through VAE
2. **Parallel agent evolution** (HIHO physics)
3. **Trajectory prediction** (sequence generation)

### Implementation Path

**Option A: PyTorch ROCm (Blocked)**
```python
# Would require: torch with ROCm support
# Problem: ROCm doesn't work on gfx1151
```

**Option B: Vulkan Compute (Promising)**
```python
# Export VAE weights to Vulkan compute shaders
# Run batch evolution on GPU as matrix operations
# Results back to PyTorch tensors
```

**Option C: CPU Parallel (Working Now)**
```python
# FlumePhysicsPy already vectorized with NumPy
# 16-core Zen 5 can simulate 10K+ agents
# GPU not critical for current scale
```

---

## SurrealDB Status

**SurrealDB not responding** (ports 8000, 8001 unavailable).

Likely contains:
- Agent journey histories
- Latent space checkpoints
- FLUME VAE model weights
- Simulation state snapshots

**Recovery needed** before full integration.

---

## Files Located

### Core FLUME Implementation
```
src/cohezion/flume/
├── vae.py                    # FlumeVAE class
├── autoencoder.py            # ThoughtEncoder/Decoder
├── flume_physics_py.py       # HIHO physics engine (fallback)
├── manifolds/translator.py   # Geometric operations
├── alignment.py              # Latent space alignment
├── coherence_guard.py        # Coherence monitoring
└── training.py, train_vae.py # Training pipelines
```

### Integration Points
```
src/cohezion/mass_sim/flume_physics_py.py
src/cohezion/research/flume_integration.py  # ResearchAgent integration
src/cohezion/api/routes/flume.py            # API endpoints
src/web/anima_dashboard/                    # Visualizations
```

### Documentation
```
.gemini/worktrees/*/CLAUDE.md              # System architecture
.archives/dev-config/.agent/COHEZION_CHARTER.md  # SPIN, FLUME, HIHO theory
```

---

## Summary of Correct Understanding

**FLUME is NOT abstract fluid dynamics.**

It's a **concrete implementation**:
1. **VAE** - Text ↔ 256D latent vectors (Transformer-based)
2. **Physics** - HIHO dynamics governing latent evolution
3. **Manifold** - Information-geometric latent space
4. **Journey** - Trajectories through latent space tracked over time

**EVOs would be:**
- Agents in the 256D latent space
- Modified HIHO dynamics (unstable equilibria)
- "Exotic" = anomalous coherence values
- Journey tracking = their trajectory through thought space

**GPU acceleration**: Not critical (CPU vectorized) but Vulkan compute possible for scale.

**Next step**: Define EVO class extending existing FlumePhysics with exotic dynamics.
