# Cohezion

[![Health Check](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/health-check.yml)
[![CI](https://github.com/manderson240/cohezion/actions/workflows/ci.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/ci.yml)
[![License: AGPL v3](https://img.shields.io/badge/License-AGPL_v3-blue.svg)](LICENSE)
[![Python 3.11](https://img.shields.io/badge/python-3.11-blue.svg)](pyproject.toml)

**An RL environment where agent safety comes from physics, not reward penalties.**

Most RL safety research bolts penalty terms onto a reward function — and agents learn
to game them. Cohezion takes the opposite approach: agents act inside a simulated
physics where unsafe states are *energetically unfavorable*. Safety isn't a rule the
agent learns to satisfy; it's an attractor the environment's dynamics pull toward.

The result is a [Gymnasium](https://gymnasium.farama.org/)-compatible training
environment plus the tooling to train, evaluate, and reproduce agents in it — all of
it CPU-friendly and CUDA-free.

```bash
git clone https://github.com/manderson240/cohezion.git
cd cohezion
uv sync

make demo          # train + evaluate + show the loop (~5 min, no GPU needed)
```

---

## Who this is for

- **RL researchers** curious about structural (vs. learned) safety constraints, reward
  shaping that cooperates with — instead of fighting — the environment, and a concrete
  testbed for either.
- **Agent / orchestration builders** who want a worked example of a cost-aware,
  local-first inference router (NPU → iGPU → CPU → cloud) and a self-improving
  "compound engineering" execution loop.
- **The physics-curious** who want to see SU(2) gauge theory, Lagrangian mechanics, and
  information geometry doing real work in an ML system rather than sitting in slides.

If you just want to *run an agent*, start with `make demo`. If you want to *understand
why it's safe*, read [The HIHO principle](#the-hiho-principle). If you want to
*contribute*, jump to [Where to start](#where-to-start).

## What makes it different

| Standard RL safety | Cohezion |
|---|---|
| Safety = a learned constraint | Safety = a property of the dynamics |
| Agents learn to avoid violations | The attractor makes violations cost energy |
| Reward hacking bypasses constraints | Large/erratic actions fight the attractor and self-correct |
| A random policy is ~0% safe | A random policy drifts *toward* the safe equilibrium |

**Headline result:** with small actions that cooperate with the Lagrangian attractor,
PPO agents reach ~0.9 coherence (1.0 = the safe HIHO equilibrium). The environment's
geometry does part of the learning for you. Reproduce: `make train && make evaluate`.

## Quick start

```bash
uv sync                 # install (uses uv; no bare pip)

make validate           # sanity-check the compound loop (~18s)
make train              # train PPO on the 12D manifold (20K steps, ~5 min, CPU OK)
make evaluate           # compare the trained policy against random / greedy baselines
make demo               # the whole thing end-to-end
```

Use the environment directly:

```python
import gymnasium as gym
import cohezion.environments  # registers the env

env = gym.make("Cohezion/ManifoldEnv-v0")   # 19D obs, 12D action
obs, info = env.reset(seed=0)
obs, reward, terminated, truncated, info = env.step(env.action_space.sample())
print(info["coherence"])   # distance from the HIHO safe equilibrium
```

## Training results

The full algorithm × reward-mode matrix at 100K steps (reproduce with `make benchmark`).
Earlier 20K-step diagnostic runs — including a deliberately broken-reward baseline we
kept for the record — live in `CHANGELOG.md` and the training logs.

| Algorithm | Reward mode | Reward | vs. random | vs. greedy |
|-----------|-------------|-------:|-----------:|-----------:|
| **SAC**   | **dense**       | **40.77** | +3.40 | −1.20 |
| PPO       | dense           | 38.95 | −1.79 | **+3.73** |
| PPO       | curriculum      | 14.23 | +7.51 | +1.34 |
| SAC       | curriculum      | 10.91 | +8.59 | −1.98 |

**Takeaway:** the reward structure has to match the algorithm's learning dynamics.
On-policy PPO benefits from a structured curriculum; off-policy SAC wants simpler dense
gradients. Both need small actions that cooperate with the attractor rather than
overpowering it.

## Architecture

```
Physics layer (the "Genesis Engine")
  12D Riemannian manifold
    ├── SU(2) spinors on the Bloch sphere   (coherence = |Bloch vector|)
    ├── Lagrangian dynamics                 (Euler–Lagrange + Störmer–Verlet)
    ├── Yang–Mills gauge theory             (flat connection = HIHO vacuum)
    └── Fisher information metric           (ties geometry, dynamics, thermodynamics)

RL environments (Gymnasium)
    ├── ManifoldEnv  — single agent, 19D obs / 12D action, curriculum & dense modes
    └── SwarmEnv     — N agents coupled through a shared gauge field

Compound engineering loop  (optional; the "agent that improves itself" layer)
    skill → expand → plan → execute (with coherence + degradation monitoring)
         → retrospect → refine skill → repeat
```

The physics and RL layers stand alone — you can train agents without ever touching the
compound loop. The loop is for the second audience above.

## Key modules

| Module | Purpose | Entry point |
|--------|---------|-------------|
| `physics/` | SU(2) spinors, Riemannian metric, Lagrangian dynamics, gauge theory, Fisher metric | `SpinorState` |
| `environments/` | Gymnasium envs: `ManifoldEnv` (single), `SwarmEnv` (multi-agent) | `gym.make("Cohezion/ManifoldEnv-v0")` |
| `eval/` | Evaluator with bootstrap CIs, convergence metrics, baseline comparisons | `UniverseEvaluator` |
| `compound/` | Self-improving execution pipeline: journey tracking, retrospection, skill refinement | `CompoundExecutor` |
| `swarm/` | Team orchestration + cost-aware, local-first model routing | `CostAwareRouter` |
| `world_model/` | Small JEPA predictor + surprise-driven exploration | `JEPAWorldModel` |
| `cache/` | Layered semantic cache (hash + cosine + persistent store) | `SemanticCache` |
| `api/` | FastAPI backend with AG-UI event streaming | `uvicorn cohezion.api:app` |

## The HIHO principle

HIHO — **Half-In, Half-Out**, coherence = 0.5 — is the equilibrium the environment is
built around. It's the point where several independent formalisms describe the same
balance between order and freedom:

- **Bloch-sphere equator** — the maximal superposition `(|↑⟩ + |↓⟩)/√2`
- **Flat gauge connection** — Yang–Mills curvature vanishes
- **Fisher-metric minimum** — the natural-gradient sweet spot of information geometry
- **Friston free energy** — `F = E − TS` minimized
- **Landau phase transition** — an order parameter at its critical point

Coherence below 0.5 is rigid/exploitative; above it is unstable/exploratory. The safe
attractor sits in the middle, which is also where capable agents want to be. Details and
the derivation: `src/cohezion/physics/cosmogony.py`.

## Hardware

Runs CPU-only — **no CUDA required**. Training the demo agent takes minutes on a laptop.
It's developed on AMD (Ryzen AI + Radeon iGPU, unified memory), and the optional
local-inference router targets that silicon, but nothing in the core RL/physics stack
depends on a specific accelerator.

## Where to start

New here? Good entry points, roughly easiest-first:

1. Run `make demo` and read what it prints — that's the whole loop in one command.
2. Read `src/cohezion/environments/manifold_env.py` — the environment is the heart of the project.
3. Skim the design paper (draft): `docs/papers/genesis-engine-paper.md`.
4. Look for [`good first issue`](https://github.com/manderson240/cohezion/labels/good%20first%20issue) and `help wanted` labels.

**Contributions are welcome** — see [CONTRIBUTING.md](CONTRIBUTING.md) for the dev
setup, test commands, and PR conventions. Bugs, docs fixes, new baselines, and
additional reward modes are all genuinely useful. Open an issue to discuss anything
larger before you build it.

## References

- Gymnasium API — https://gymnasium.farama.org/
- Friston, *The free-energy principle* — https://doi.org/10.1038/nrn2787
- Levin, *Bioelectric networks* — https://doi.org/10.1016/j.biosystems.2022.104787
- Design paper (draft) — `docs/papers/genesis-engine-paper.md`

## License

Cohezion is **dual-licensed** — pick whichever fits:

- **[AGPL-3.0](LICENSE)** (open source, free). Use, modify, and self-host freely. Because
  the AGPL is network-copyleft, running a *modified* version as a service obligates you to
  offer that version's source to its users under the AGPL. Ideal for research, evaluation,
  and other open-source projects.
- **Commercial license.** To build on Cohezion in a closed-source product or hosted
  service without the AGPL's source-sharing terms, a commercial license is available.
  See **[LICENSING.md](LICENSING.md)** or email manderson240@gmail.com.

Contributions are accepted under the
[Contributor License Agreement](CONTRIBUTOR_LICENSE_AGREEMENT.md), which is what lets the
project offer both licenses.
