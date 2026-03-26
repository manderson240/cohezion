# Getting Started with the Genesis Engine

The Genesis Engine is Cohezion's interactive physics-grounded universe simulator. It visualizes a 12-dimensional Riemannian manifold where AI agents navigate using Lagrangian mechanics, SU(2) spinor coherence, and gauge field theory.

## Prerequisites

- **Python 3.13+** with `uv` package manager
- **Bun** (frontend build tool): `curl -fsSL https://bun.sh/install | bash`
- **SurrealDB** (optional, for persistence): `curl -sSf https://install.surrealdb.com | sh`

## Quick Start

### 1. Install Backend

```bash
cd ~/dev/cohezion
uv pip install -e .
```

### 2. Start the API Server

```bash
uv run uvicorn cohezion.api:app --reload --port 8080
```

The API runs at `http://localhost:8080`. Verify with:

```bash
curl http://localhost:8080/api/genesis/spinor/hiho | python3 -m json.tool
```

You should see the HIHO Bloch vector `[1, 0, 0]` (equatorial state).

### 3. Start the Frontend

```bash
cd src/web/anima_dashboard
bun install
bun run dev
```

Open `http://localhost:3000/genesis` in your browser.

## Navigating the Genesis Engine

The `/genesis` page has 6 tabs:

### Tab 1: Genesis (Cosmogony)

Interactive cosmogony from Brahmagupta's void to the 12D manifold.

1. **Click the void** — your first interaction is the first distinction ("It from Bit")
2. **Drag the temperature slider** — cool the universe through 5 phase transitions:
   - T > 100: Void (nothing exists)
   - T = 100 → SO(12): Symmetry crystallizes
   - T = 10 → SO(3)^4: Four fabrics emerge
   - T = 1.0 → U(1)^4: Axes select
   - T = 0.1 → Z_2^4: SPIN discretizes
   - T = 0.01 → HIHO: Equilibrium at delta = 0
3. **Watch the equations** — KaTeX panels update in real-time

### Tab 2: SPIN Lab (Bloch Sphere)

Interactive SU(2) spinor visualization.

1. **Drag the Logic slider** — moves the spinor from north pole (|up>) to south pole (|down>)
2. **Drag the Quantum slider** — rotates azimuthally
3. **Apply Rotation/Precession** — SU(2) rotations around sigma_x and sigma_y
4. **Watch the Bloch vector** — the green dot shows (r_x, r_y, r_z)
5. **Compare to HIHO** — the green dot on the equator is the HIHO state

### Tab 3: Thermo (Statistical Mechanics)

Live thermodynamic state + free energy landscape.

- **8 metric cards**: entropy, free energy, entropy production, susceptibility, temperature, heat capacity, order parameter, energy
- **F(T) curve**: Landau free energy with critical temperature markers
- **HIHO status**: delta = order_parameter - 0.5

### Tab 4: Compound (11-Step Pipeline)

Visualization of the compound engineering feedback loop.

- **11 steps**: vault query → template match → alignment check → plan → execute → quality gate → journey track → metrics → retrospection → skill refine → consensus vote
- **Color coding**: green=complete, yellow=active, gray=pending, red=error

### Tab 5: Cache/Cost

Semantic cache topology and cost optimization.

- **L1/L2/L3 hit rate gauges**: hash, cosine similarity, vault lookup
- **Token savings counter**: millions of tokens saved
- **Cost routing**: simple→phi3, medium→qwen, complex→deepseek

### Tab 6: About

Mathematical references and philosophical grounding.

## Audio Controls

- **Sound ON/OFF**: Toggles Tone.js sonification (coherence→pitch, entropy→noise)
- **Volume slider**: Master volume control
- **Narration ON/OFF**: Toggles PocketTTS narration (requires `uv pip install pocket-tts`)

## API Endpoints

### Spinor (5 endpoints)
```
GET  /api/genesis/spinor/hiho          — HIHO Bloch state
POST /api/genesis/spinor/from-values   — Create from logic/quantum
POST /api/genesis/spinor/rotate        — Apply SU(2) rotations
GET  /api/genesis/spinor/sweep         — N points across sphere
GET  /api/genesis/spinor/algebra-check — Verify SU(2) identities
```

### Cosmogony (6 endpoints)
```
GET  /api/genesis/cosmogony/state               — Current state
POST /api/genesis/cosmogony/cool                 — Cool by delta_T
POST /api/genesis/cosmogony/set-temperature      — Jump to temperature
POST /api/genesis/cosmogony/reset                — Reset to void
GET  /api/genesis/cosmogony/free-energy-landscape — F(T) curve
GET  /api/genesis/cosmogony/12d-state            — Generate 12D state
```

### Manifold (4 endpoints)
```
POST /api/genesis/fiber-bundle          — Decompose 12D into base+fiber
POST /api/genesis/gauge-state           — Gauge field strengths
POST /api/genesis/lagrangian-trajectory  — Euler-Lagrange simulation
GET  /api/genesis/manifold-summary      — Complete physics snapshot
```

### World Model (5 endpoints)
```
GET  /api/world-model/status    — Model parameters and metrics
POST /api/world-model/train     — Train on synthetic data
POST /api/world-model/predict   — Predict next 12D state
POST /api/world-model/simulate  — N-step trajectory rollout
POST /api/world-model/surprise  — Surprise score for transition
```

## Using ManifoldEnv (Gymnasium)

```python
import gymnasium as gym
from cohezion.environments import ManifoldEnv

# Standard gymnasium loop
env = gym.make("Cohezion/ManifoldEnv-v0")
obs, info = env.reset()

for step in range(1000):
    action = env.action_space.sample()
    obs, reward, terminated, truncated, info = env.step(action)

    if step % 100 == 0:
        print(f"Step {step}: coherence={info['coherence']:.4f}, "
              f"HIHO_dev={info['hiho_deviation']:.4f}")

    if terminated:
        print(f"HIHO reached at step {step}!")
        obs, info = env.reset()
```

## Using SwarmEnv (Multi-Agent)

```python
from cohezion.environments import SwarmEnv

env = SwarmEnv(n_agents=4)
observations, infos = env.reset()

for step in range(500):
    actions = {agent: env._rng.uniform(-0.1, 0.1, 12).astype("float32")
               for agent in env.agents}
    observations, rewards, terminateds, truncateds, infos = env.step(actions)

    if any(terminateds.values()):
        print(f"All agents at HIHO at step {step}!")
        break
```

## Next Steps

- **Physics walkthrough**: See `docs/tutorials/02-physics-walkthrough.md`
- **World model training**: See `docs/tutorials/03-world-model.md`
- **RL environment tutorial**: See `docs/tutorials/04-rl-environment.md`
- **Research document**: See `docs/genesis-engine-research.md` (962 lines of mathematical grounding)
