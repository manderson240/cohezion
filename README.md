# Cohezion: A Self-Evolving Agentic Sandbox
**Research Engineering Portfolio for Anthropic's "Universes" Application**

> "We design and implement novel training environments that go far beyond what models can do today — environments where models learn to navigate ambiguity, handle interruptions, maintain context over extended interactions, and exercise judgment." — *Universes Job Description*

## 1. Research Objective
**Cohezion** is an experimental training environment designed to produce **Anti-Fragile Agentic Reasoning**. Unlike traditional RL environments with static rewards, Cohezion implements **R-Zero**, a co-evolutionary protocol where the environment itself plays the role of an adversarial "Challenger."

### Core Research Questions
*   **Plateau Prevention:** Can we prevent reasoning stagnation by dynamically adjusting constraints ($\mathcal{D}$) based on system variance?
*   **Pragmatic Grounding:** How do we penalize "hallucinated complexity" (Overhype) while encouraging genuine novelty?
*   **Unified Ontology:** Can an agent maintain coherence across 12+ conflicting theoretical frameworks (Physics vs Metaphysics) simultaneously?

## 2. The R-Zero Architecture
The system operates as a closed-loop triad, running 24/7 on local hardware (128GB RAM, 32 Cores).

| Agent | Role | Anthropic Alignment |
|-------|------|---------------------|
| **Challenger** | Inject Entropy / Constraints | **Automated Red Teaming** |
| **Solver** | Logic / Synthesis | **Long-Horizon Agency** |
| **Pragmatist** | Rules / Evaluation | **Constitutional AI / Safety** |
| **Mem0** | Persistent Memory | **Self-Improving Memory Layer** |

### Live Simulation Streams
As of Jan 2026, the system orchestrates 3 parallel "Universes":
1.  **Physics (Pragmatic):** Exploring Zero Point Energy boundaries under strict conservation laws.
2.  **Societal (Crisis):** Governance simulation under resource scarcity.
3.  **Linguistic (Memetic):** Modeling language mutation rates (Babel Protocol).

## 3. High-Fidelity Infrastructure
Designed for long-horizon simulation and deep interpretability.

*   **12D Physics State**: Every agent thought is modeled as a 12-dimensional vector in latent space, tracking parameters like *Coherence*, *Stability*, *Complexity*, and *Morphic Resonance*.
*   **SurrealDB Substrate**: High-performance persistence for agent "Experiences" (119+ nodes captured in the latest Dawn Simulation).
*   **Journey Narration**: Automatic 1st-person narration of agent reasoning paths, persisted in the cosmic chronicle.
*   **Interactive Observability**: [Universe Explorer](research/notebooks/marimo/universe_explorer.py) (Marimo) providing 12D Radar projections and PCA evolution maps.
*   **Capabilities Matrix**: [Taxonomy of 71+ Skills](.agent/CAPABILITY_MAP.md) driving the self-evolving swarm.

## 4. Key Artifacts
*   [Cohezion Capabilities Matrix](.agent/CAPABILITY_MAP.md): Strategic taxonomy of skills.
*   [Portfolio Map](docs/ANTHROPIC_PORTFOLIO_MAP.md): Direct mapping of this repo to the Anthropic Job Description.

## 5. Quick Start (Reproducibility)

```bash
# 1. Install Dependencies (uv)
uv sync

# 2. Launch the Swarm (Physics Stream)
# Exposes Prometheus on :9090
uv run python scripts/drivers/overnight_driver.py

# 3. Query the Knowledge Graph
uv run python -m cohezion.registry.capability_registry
```

## 6. License
Apache 2.0. Built by Mike Anderson.
