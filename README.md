# Cohezion

An AI agent orchestration framework built around physics-inspired simulation, multi-agent consensus, and the HIHO stability principle.

> Systems achieve maximum stability not by maximizing parameters, but by maintaining dynamic equilibrium at the 0.5 coherence point.

---

## What This Is

Cohezion explores how AI agents can reason about complex problems through physics-inspired metaphors. Knowledge is encoded as trajectories on high-dimensional manifolds. Agents navigate these manifolds using multi-expert consensus, with stability emerging from balance rather than optimization.

The project implements a 12D universe simulation (3 spatial + 1 temporal + 8 abstract dimensions), a Transformer-based manifold encoder, quantum circuit simulation, and a real-time Three.js visualization with custom GLSL shaders.

---

## Verified Capabilities

### VLIW Performance Optimization
Anthropic's public VLIW scheduling challenge, optimizing a tree-traversal-with-hashing kernel on a simulated VLIW SIMD architecture.

| Metric | Cycles | Speedup |
|--------|--------|---------|
| Baseline | 147,734 | 1x |
| Claude Opus 4.5 (best) | 1,363 | 108x |
| **Cohezion** | **349** | **423x** |

Verified: deterministic, reproducible, passes all 9 Anthropic submission tests including correctness across 8 random seeds.

```bash
cd research/challenges/anthropic_challenge
uv run python tests/submission_tests.py -v
```

### Quantum Circuit Simulation
36-qubit tensor network simulation via quimb + cotengra. MPS evolution with SWAP routing and bond dimension control. Safe QASM parsing without eval.

### FLUME Manifold Encoder
PyTorch Transformer autoencoder mapping to 256D latent space. Supports encode, decode, interpolate, and semantic similarity. Trained on real mass simulation data (11K vectors from 10 universes). MSE 0.1322 on real data (5.9x harder than synthetic), KL divergence 0.4329 (13.8x richer latent structure).

### Reinforcement Learning
Gymnasium environment (`cohezion/FlumeNav-v0`) with REINFORCE trainer and composable reward shaping. Trained on Hamiltonian dynamics with HIHO-well potential. 200 episodes, average coherence 0.991.

### Multi-Agent Consensus
Democratic debate system with 5 parallel expert streams, 0.85+ consensus threshold, and full transparency logging. Agents are routed via TF-IDF capability matching across 193 registered capabilities.

### 12D Universe Visualization
Three.js particle field with custom GLSL shaders (simplex noise, 4 attribute channels), Rust/WASM physics worker at 60Hz, Web Audio sonification of coherence state. Connects to FastAPI backend via REST + WebSocket.

### Infrastructure
- **Circuit breakers**: CLOSED/OPEN/HALF_OPEN with failure threshold and recovery timeout
- **Resource monitor**: CPU/RAM/VRAM tracking, global LLM concurrency semaphore (limit=4), backpressure signals
- **Security**: Prompt injection guard (70+ patterns, multilingual), rate limiter, JWT auth, input validators
- **Persistence**: Async SurrealDB client with in-memory fallback, compression, vector similarity search
- **Self-healing**: Drift detection, self-diagnosis, auto-correction

---

## Architecture

```
src/cohezion/
├── api/              # FastAPI backend (15+ endpoints, circuit-breaker wrapped)
├── agents/           # BaseAgent ABC + ~30 specialized agents (Ollama-backed)
├── flume/            # Transformer autoencoder, manifold navigation, git encoder
├── physics/          # Quantum solver (quimb tensor networks), dimension extractor
├── universe/         # 12D simulation engine, sandbox (Docker/bubblewrap)
├── swarm/            # Democratic debate, smart router, model manager, evolution
├── reliability/      # Circuit breaker, resource monitor, semantic cache
├── security/         # Prompt guard, rate limiter, auth, validators
├── healing/          # Drift detection, immune system, platform audit
├── registry/         # TF-IDF capability search across skills/agents/MCP
├── mcp/              # MCP servers (SurrealDB, Knowledge, Skills, Research, Gmail)
├── mass_sim/         # Mass simulation engine (batch runner, exporter, OOM protection)
├── rl/               # Reinforcement learning (Gymnasium FlumeNav-v0, REINFORCE)
├── pipeline/         # Data pipeline (mass sim → .npy → training)
├── skills/           # 126 PRIME skill definitions (markdown)
└── core/             # Persistence, routing, event bus, config templates

apps/
├── webapp/           # Vite + React + Three.js + WASM (main visualization)
└── morphospace-loom/ # Standalone 12D demo (self-contained)

research/
└── challenges/anthropic_challenge/  # VLIW optimizer (349 cycles verified)

src/cohezion_core/    # Rust: PyO3 bindings + WASM bridge (FlumePhysics, rayon batch)
```

---

## Quick Start

```bash
# Install uv
curl -LsSf https://astral.sh/uv/install.sh | sh

# Clone and sync
git clone https://github.com/manderson240/cohezion.git
cd cohezion && uv sync

# Start the API server
uv run uvicorn cohezion.api:app --reload --port 8080

# In another terminal, start the frontend
cd apps/webapp && npm install && npm run dev

# Run the VLIW benchmark
cd research/challenges/anthropic_challenge
uv run python tests/submission_tests.py -v
```

### Requirements
- **Python**: 3.13+
- **Package manager**: uv
- **Database**: SurrealDB (optional -- API falls back to synthetic data)
- **Local models**: Ollama with deepseek-r1:70b, qwen3-coder:30b, phi3:mini (for agent tasks)
- **Hardware**: Developed on AMD Ryzen AI MAX+ 395, 128 GiB LPDDR5X, Radeon 8060S iGPU. No CUDA required.

---

## Limitations (Honest)

- **FLUME model is lightly trained**: Trained on 11K real mass sim vectors (MSE 0.1322), but needs more data and epochs for production quality. Latent space shows structure but is not yet fully converged.
- **RL environment is too easy**: REINFORCE trainer achieves 0.991 coherence in 200 episodes because the Hamiltonian naturally attracts to the target. Needs adversarial perturbations and curriculum learning for meaningful policy learning.
- **Agents are LLM wrappers**: Most specialized agents inherit BaseAgent and delegate reasoning to Ollama prompts. The infrastructure (caching, circuit breakers, security) is real; the agent "intelligence" lives in system prompts.
- **Simulation physics are mostly conceptual**: Only `peaked_solver.py` implements genuine computational physics. Other simulation modules use heuristic models with physics terminology.
- **Test coverage is growing**: 357 tests across 50 test files (covering 192 source files). Solid coverage for reliability, ML pipeline, agents, and validation; thinner elsewhere.
- **Rust extensions**: The `cohezion_core` Rust code compiles to WASM (16KB) and has PyO3 bindings, but the inner physics loop is minimal (coherence attraction + sin jitter).

---

## Theoretical Framework

| Concept | Description |
|---------|-------------|
| **SPIN** | Fundamental unit of information: rotation + precession creating toroidal momentum |
| **HIHO** | Half-In-Half-Out: maximum stability at 0.5 coherence (verified by 25M-cycle simulation) |
| **FLUME** | Fluid Latent Understanding through Manifold Encoding: semantic momentum in 256D latent space |
| **12D Universe** | 3 spatial + 1 temporal + 8 brane dimensions, grounded in hardware telemetry |
| **Expert Domain Lattice** | 5 parallel expert streams (Architect, Engineer, Biologist, Quantum HW, Quantum Algo) |
| **Quadrature Nexus** | Four-phase coordination: Space, Field, Control, Precipitation |
| **Compound Engineering** | Every feature enables future features -- fractal self-similarity |

See `.agent/COHEZION_CHARTER.md` for the full theoretical framework.

---

## License

Copyright 2025-2026 Mike Anderson. All rights reserved. Source available for reference only. See [LICENSE](LICENSE) for details. For licensing inquiries, contact mike@cohezion.dev.
