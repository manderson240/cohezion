<div align="center">

<img src="docs/media/genesis-compound.png" width="900" alt="Cohezion Genesis UI — Compound Engineering Loop">

# Cohezion

[![CI](https://github.com/manderson240/cohezion/actions/workflows/ci.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/ci.yml)
[![CodeQL](https://github.com/manderson240/cohezion/actions/workflows/codeql.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/codeql.yml)
[![Security Scan](https://github.com/manderson240/cohezion/actions/workflows/security-scan.yml/badge.svg)](https://github.com/manderson240/cohezion/actions/workflows/security-scan.yml)
[![Python 3.13](https://img.shields.io/badge/python-3.13%2B-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-AGPL--3.0-blue.svg)](LICENSE)
[![AMD Native](https://img.shields.io/badge/inference-AMD%20NPU%20%2F%20iGPU%20%2F%20CPU-red)](https://www.amd.com/en/products/processors/consumer/ryzen/ai.html)

**A self-improving agent orchestration loop that runs end to end on consumer AMD silicon at zero marginal inference cost, with a physics-grounded RL environment and reproducible benchmarks behind it.**

Every execution is reflected on and folded back into the skill definitions the next run uses (300+ version-controlled skills so far). Routing is tiered across the local NPU, iGPU and CPU behind one Lemonade endpoint, so a 10k-token loop costs $0.00. The RL layer stands alone: a Gymnasium environment on a 12D Riemannian manifold where unsafe actions fight the dynamics instead of a penalty term.

[Ten-minute tour](#ten-minute-tour) · [Architecture](#architecture) · [Local Inference](#local-inference-stack) · [Benchmarks](#training-results) · [Contributing](#contributing)

</div>

---

## Why Cohezion?

| Other AI Frameworks | Cohezion |
|---|---|
| Each session starts fresh | **300+ skills compound** — session N+1 builds on session N |
| Assumes NVIDIA GPU | **AMD-first**: XDNA2 NPU (42 TPS) + iGPU + CPU, no CUDA |
| Cloud API = cost per token | **No per-token API fees** — local inference via the Lemonade router at `:13305` |
| Safety = penalty terms in reward | **Safety = physics** — the Lagrangian attractor makes unsafe actions fight the dynamics |
| Agent coordination is ad-hoc | **HIHO equilibrium** — six mathematical frameworks converge at coherence = 0.5 |
| Manual knowledge management | **Self-improving loop** — SkillRefiner version-bumps skills from execution results |

---

## Ten-minute tour

Three commands, each with the output you should see. Nothing here needs a GPU, a network
connection, credentials or a running inference server.

```bash
git clone https://github.com/manderson240/cohezion.git && cd cohezion
uv sync
```

**1. Step an agent through the 12D manifold** (seconds):

```bash
uv run python examples/quickstart.py
```
```
reset -> obs.shape=(19,)  coherence=0.8563
step  1  coherence=0.8559  hiho_deviation=0.1699  reward=-0.0854  stage=1
...
step 10  coherence=0.8516  hiho_deviation=0.1727  reward=-0.0868  stage=1

episode summary: 11 positions visited, episode_reward=-0.8609

Quickstart complete. No network, credentials, or local inference were used.
```

**2. Validate the compound loop end to end** (27 steps, about 10 s):

```bash
make validate
```
```
[10/11] Routing Orchestrator (Unified Entry)
  [PASS] RoutingOrchestrator creation
  [PASS] Unified routing decision — model=..., confidence=0.71
VALIDATION RESULT: 27/27 steps passed
```

**3. Train a small PPO agent and compare it with a random policy** (5K steps, a few minutes on CPU;
needs the RL extra):

```bash
uv sync --extra rl && make demo      # examples/demo_train_eval.py
make train                           # 20K steps, ~5 min; results in results/training/
```

The outputs above were captured on 2026-10-22 from the commands as written. If what you see
differs materially, that is a bug worth an issue.

**Requires**: Python 3.13+, [uv](https://github.com/astral-sh/uv).
Installs from source only (not yet on PyPI); GPU extras pin AMD ROCm wheels — see
[`docs/tutorials/`](docs/tutorials/) for a guided setup.

---

## Key Capabilities

### Self-Improving Compound Loop

Every execution extracts learnings that refine the skill definitions agents use next time:

```
Execute (CompoundExecutor 11-step pipeline)
  → Reflect  (RetrospectionEngine extracts non-obvious patterns)
  → Refine   (SkillRefiner version-bumps the PRIME skill)
  → Compound (better skill → smarter next execution)
```

300+ PRIME skill definitions in [`src/cohezion/skills/`](src/cohezion/skills/) are the accumulated output of 100+ development sessions — version-controlled, keyword-indexed, and auto-discoverable. Run the cycle: `uv run python scripts/drivers/compound_cycle.py`

---

### Physics-Grounded Agent Safety

<img src="docs/media/genesis-animating.png" width="700" alt="Genesis physics simulation">

Instead of adding penalty terms to reward functions, Cohezion shapes the environment dynamics so unsafe behavior works against the physics. Agents operate inside a 12D Riemannian manifold governed by:

- **Lagrangian dynamics** — large unsafe actions fight the Lagrangian attractor (self-correcting)
- **SU(2) gauge theory** — flat connection = Yang-Mills vacuum = HIHO equilibrium
- **Bioelectric percolation** — Levin-inspired gap junction network distributes coherence across agents
- **Fisher information metric** — connects FLUME latent space, manifold geometry, and thermodynamics

**Result** (from our 8-run diagnostic, reproducible via `make benchmark`): a random agent shows ~40% safe behavior without any training — the physics guides it — and PPO trained with the Lagrangian attractor reaches **0.9+ coherence** without explicit safety constraints.

---

### Multi-Agent Swarm with Cost-Aware Routing

<img src="docs/media/genesis-swarm.png" width="700" alt="Agent swarm topology">

Specialist sub-agents collaborate through the compound engineering pipeline. Cost-aware routing sends 70% of requests to local silicon ($0), 20% to mid-tier, and only 10% to high-cost models:

```python
from cohezion.compound import make_executor

executor = make_executor(mcp_client)  # wires Lemonade → SemanticCache → CompoundExecutor
result = await executor.execute_task("Your task here")
```

A three-tier semantic cache (L1 exact hash, L2 cosine similarity, L3 vault) sits in front of inference so repeat and near-repeat work is served without a model call. Hit rates depend on the workload; the cache reports its own counters, and this README makes no claim beyond that until a benchmark is checked in under `docs/benchmarks/`.

---

## Architecture

```mermaid
graph TD
    A[PRIME Skill] --> B[InstructionExpander]
    B --> C[PlanExecutor]
    C --> D[ExecutionOrchestrator]
    D --> E[RequestAlignmentAnalyzer]
    D --> F[DegradationDetector]
    D --> G[JourneyTracker 12D]
    D --> H[SemanticCache L1/L2/L3]
    D --> J[Result]
    J --> K[RetrospectionEngine]
    K --> L[SkillRefiner]
    L --> M[SkillConsensusVoter]
    M -->|Updated Skill| A
    F -->|feedback| N[CostAwareRouter]
    N --> O["NPU  42 TPS  $0"]
    N --> P["iGPU ~200ms $0"]
    N --> Q["CPU  ~800ms $0"]
    N --> R["Cloud  last resort"]
```

### Module Map

| Layer | Module | Entry Point |
|---|---|---|
| **Compound Loop** | `compound/` — Executor, SkillRefiner, RetrospectionEngine, JourneyTracker | `CompoundExecutor` |
| **Swarm** | `swarm/` — TeamOrchestrator, CostAwareRouter, OI-MAS scoring | `CostAwareRouter` |
| **Semantic Cache** | `cache/` — L1 hash + L2 cosine + L3 vault | `SemanticCache` |
| **Physics Engine** | `physics/` — SU(2) spinors, Lagrangian, fiber bundles, gauge theory, cosmogony | `SpinorState` |
| **RL Environments** | `environments/` — ManifoldEnv (19D obs), SwarmEnv (multi-agent gauge coupling) | `gym.make('Cohezion/ManifoldEnv-v0')` |

The `info` dict returned by `ManifoldEnv.reset()` / `step()` carries these keys (see the class and `step()` docstrings in `src/cohezion/environments/manifold_env.py` for the authoritative, fully-specified list):

| Key | Meaning |
|---|---|
| `coherence` | current coherence (1.0 = HIHO safe equilibrium) |
| `avg_coherence` | running episode average |
| `invariant_passed` / `invariant_failed` | physics-invariant check counts (only present when the optional `InvariantChecker` is active; absent otherwise) |
| **World Model** | `world_model/` — JEPA predictor (86K params), bioelectric network, EVO model | `JEPAWorldModel` |
| **FLUME VAE** | `flume/` — 256D thought vectors, PolarQuant (2.7x compression), QJL (32x) | `ThoughtEncoder` |
| **Knowledge** | `ouroboros/` + vault — Mycelium transport, SurrealDB, Obsidian | `OuroborosBridge` |
| **API** | `api/` — FastAPI backend, AG-UI event streaming (15+ typed SSE events) | `uvicorn cohezion.api:app` |
| **Genesis UI** | `src/web/` — Next.js 16, Three.js Bloch sphere, swarm topology viz | `/genesis` route |

---

## Local Inference Stack

Cohezion runs its entire inference pipeline on AMD silicon — no NVIDIA, no cloud required:

```
Lemonade Router :13305  (single endpoint for the full model catalog)
│
├── NPU  — llama3.2-1b-FLM      42 TPS  │ classification, routing, short answers
├── iGPU — Gemma-4-E4B-it-GGUF  ~200ms  │ code gen, structured output
└── CPU  — DeepSeek-Qwen3-8B     ~800ms  │ reasoning, multi-step analysis
```

Routing is automatic — cheap tiers first, escalate only when quality gates fail:

```python
from cohezion.inference.triune_orchestrator import build_triune_orchestrator
from cohezion.compound import make_executor

executor = make_executor(mcp_client, provider=build_triune_orchestrator())
```

**Hardware**: AMD Strix Halo — Ryzen AI MAX+ 395 (16C/32T, XDNA2 NPU), Radeon 8060S (iGPU), 128 GiB LPDDR5X unified memory. No CUDA. No NVIDIA tax.

Check availability: `curl -s http://localhost:13305/v1/models`

---

## Training Results

The physics and RL layers stand alone — you can train agents in the manifold without ever
touching the compound loop. An 8-run diagnostic across the 2×2 algorithm-reward matrix
(PPO/SAC × curriculum/dense). Reproduce with `make train` (20K steps, ~5 min) or
`make benchmark` (100K steps):

| Algorithm | Reward Mode | Steps | Reward | vs Random | vs Greedy |
|---|---|---|---|---|---|
| PPO | curriculum | 100K | 14.23 | +7.51 | +1.34 |
| **SAC** | **dense** | **100K** | **40.77** | **+3.40** | **-1.20** |
| PPO | dense | 100K | 38.95 | -1.79 | +3.73 |

**Best**: SAC + dense reward, 100K steps. SAC's off-policy replay cooperates with the Lagrangian attractor; dense reward gives simpler gradients than curriculum at scale.

Provenance: this table was recorded on 2026-04-01 from a local run; the raw results are not checked into the repository, so treat it as a reported result and `make benchmark` as the way to reproduce it. Checking the run artifacts in under `docs/benchmarks/` is open work.

Checkpoint: `data/rl/checkpoints/policy_final.pt`

---

## The HIHO principle

HIHO (Half-In, Half-Out) — coherence = 0.5 — is where six mathematical frameworks independently converge to the same stable equilibrium:

1. **Brahmagupta (628 CE)**: deviation = coherence − 0.5 = 0
2. **Friston Free Energy**: F = E − TS minimization
3. **Yang-Mills gauge theory**: flat connection at HIHO vacuum
4. **Fisher information metric**: natural gradient minimum
5. **Bloch sphere equator**: (|↑⟩ + |↓⟩)/√2 superposition
6. **Landau phase transition**: order parameter at critical temperature

This convergence is not a coincidence — it is the mathematical structure of stable complex systems. HIHO is the attractor. Implementation: [`src/cohezion/physics/cosmogony.py`](src/cohezion/physics/cosmogony.py)

---

## Agentic-First Development

Cohezion is built **by** agents, not just **for** agents. The 300+ PRIME skill definitions are the compounded output of 100+ agentic development sessions.

The [CLAUDE.md](CLAUDE.md) agent contract is inherited by every sub-agent spawned on this repo. It encodes patterns discovered in production:
- **Deferred tool loading** — load `SendMessage` schema before calling it, or it raises `InputValidationError`
- **Vault-first knowledge** — all learnings go to `~/vaults/cohezion-vault/`, not inline comments
- **Post-formatter re-read** — ruff reformats files in place; re-read before the next `Edit`
- **Inference routing** — port `:13305` (Lemonade) serves NPU/iGPU/CPU on demand

The full agent contract, specialist routing table, and coding standards live in
[CLAUDE.md](CLAUDE.md) — start there if you develop with an AI coding agent.

---

## Development

```bash
make format      # ruff format
make lint        # ruff check + auto-fix
make test        # 13,900+ test suite
make validate    # 27 compound loop invariant checks (measured 2026-10-22)
make train       # Train PPO on ManifoldEnv (20K steps; uv sync --extra rl)
make evaluate    # Evaluate trained model vs baselines
make benchmark   # Full 100K training + comparisons
make demo        # 5K-step PPO vs random (examples/demo_train_eval.py; needs --extra rl)
```

```bash
# Start the FastAPI backend
uv run uvicorn cohezion.api:app --reload   # :8080

# Start the Genesis UI
cd src/web/anima_dashboard && npm run dev  # :3000
```

---

## Documentation

- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — system architecture deep-dive
- [`docs/tutorials/`](docs/tutorials/) — guided day-1 to day-5 onboarding path
- [`examples/`](examples/) — runnable examples, starting with `quickstart.py`
- [`docs/`](docs/README.md) — full documentation index

---

## Contributing

Contributions are welcome. See [CONTRIBUTING.md](CONTRIBUTING.md).

The most valuable contributions are new **PRIME skill definitions** — if you discover a non-obvious pattern while working with Cohezion, encode it as a skill file in `src/cohezion/skills/`. Every verified skill improves every future session for everyone.

---

## License

Dual-licensed: [AGPL-3.0-or-later](LICENSE) for open-source use, with a commercial
license available for closed-source deployments — see [LICENSING.md](LICENSING.md).

---

## References

- [Gymnasium API](https://gymnasium.farama.org/)
- [Friston Free Energy Principle](https://doi.org/10.1038/nrn2787)
- [Levin Bioelectric Networks](https://doi.org/10.1016/j.biosystems.2022.104787)
- [HIHO convergence](src/cohezion/physics/cosmogony.py)
- [Research manuscripts](research/manuscripts/)

---

<div align="center">

Built on AMD Strix Halo. No NVIDIA required. AGPL-3.0 (commercial licensing available).

</div>
