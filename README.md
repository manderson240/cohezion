# Cohezion: The Technical Reckoning (Full-Repo Showcase v3.0)

**A Living Research Environment for Autonomous Agentic Evolution**

> "Every feature makes every future feature easier." — The Cohezion Axiom

---

## 🌌 The Technical Reckoning
This repository represents more than a codebase; it is a **Living Research Environment (Universe Simulation v2.0)**. It documents its own evolution through agentic journeys, validated by **Constitutional and Simulation-Based Validation (CSV)**.

### Key Components
Explore the core systems that drive Cohezion:
- **[GPU Acceleration](src/cohezion/core/gpu_acceleration.py)**: Physics simulation manager with cupy-based GPU integration.
- **[FLUME Autoencoder](src/cohezion/flume/autoencoder.py)**: Transformer-based thought vector compression (256D latent space). Rust acceleration available via [cohezion_core](src/cohezion_core/) (PyO3).
- **[Sovereign Allostatica](src/cohezion/allostatica/engine.py)**: Autonomic homeostasis that stabilizes agentic trajectories at the HIHO attractor (0.5).
- **[HIHO Sonification](apps/webapp/src/hooks/useHomeostasisHarmonics.ts)**: Real-time audio mapping of the 12D manifold stability state.
- **[Constitutional Shield](src/cohezion/validation/constitutional.py)**: Dynamic alignment filtering that critiques agent steps.

<!-- Image removed: referenced a private local filesystem path not available in the repository -->

---

## 🏛️ Platform Architecture

### The 12D/512D Dual-State Manifold
Every task becomes a journey through the manifold:
- **512D Latent ("Soul")**: Semantic intent, reasoning, and meaning captured via FLUME.
- **12D Axiomatic ("Body")**: Measurable physical projection (Spatial, Temporal, Logic, Biology, etc.).
- **HIHO Stability**: Systems are actively regulated toward the **0.5 Coherence Point** to maximize reality precipitation.

### Core Ecosystem
```
cohezion/
├── src/cohezion/
│   ├── core/                # Persistence (SurrealDB), Cache, Bus, GPU
│   ├── agents/              # ~45 Specialized agents
│   ├── flume/               # 256D Latent trajectory autoencoders
│   ├── universe/            # 12D Journey tracking and replay
│   ├── allostatica/         # Proactive homeostasis engine
│   ├── validation/          # Constitutional Shield & Manifold Equilibrium
│   └── ...
├── apps/                    # Webapps (Vite/WebGL/WASM)
├── research/                # Fundamental research and challenge solutions
└── .agent/                  # Constitution, Charter, and Capability Map
```

---

## 🚀 Experience the Universe

### 1. Start a Journey
Capture 12D/512D trajectories for any task:
```bash
uv run python -m cohezion journey start "Build a secure VLIW kernel"
```

### 2. Verify Equilibrium
Run the Constitutional and Manifold audit:
```bash
uv run python3 src/cohezion/validation/constitutional.py
```

### 3. Visual Experience (WASM/WebGL)
Interact with the state-space in real-time:
```bash
cd apps/webapp && npm run dev
```

---

## Validation

Validation methodology: **Constitutional and Simulation-Based Validation (CSV)**

Health metrics are generated dynamically by `src/cohezion/validation/constitutional.py`. Run the validator to see current status:
```bash
uv run python3 src/cohezion/validation/constitutional.py
```

---

## 🛠️ Requirements & Install
- **Hardware**: 128GB RAM recommended (developed on AMD Ryzen AI MAX+ 395, Radeon 8060S iGPU)
- **Runtime**: Python 3.13+, SurrealDB. Optional: Rust toolchain (for building `cohezion_core` native extensions)
- **Tooling**: `uv` (required for dependency alignment)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
git clone https://github.com/manderson240/cohezion.git
cd cohezion && uv sync
```

---

## 📜 License
Cohezion is released under the [Apache License 2.0](LICENSE).
