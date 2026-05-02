# EcoResilience Distributed Swarm: System Traceability Map

## 🗺️ High-Level Architecture
The EcoResilience swarm is a compound AI system designed to bridge Indigenous Traditional Ecological Knowledge (TEK) with Unified Physics (12D Manifolds).

### 1. Sensing Layer (The Edge)
*   **Sensing Nodes**: Pixel 10 Pro Fold / Pixel 6.
*   **Logic**: `src/cohezion/swarm/core/edge_gateway.py` (Registration & Routing).
*   **Ground Truth**: `src/cohezion/compound/copernicus_bridge.py` (Sentinel-2 Spectral Data).

### 2. Valuation Layer (The Grounding)
*   **Biophysical Mapping**: `src/cohezion/compound/invest/bridge.py` (InVEST Quantitative Valuation).
*   **Latent Encoding**: `src/cohezion/flume/vae_encoder.py` ( Text/Data $\rightarrow$ $\mathbb{R}^{256}$).

### 3. Reasoning Layer (The Symphony)
*   **Regime Router**: `src/cohezion/swarm/providers/gemma4_provider.py` (Local NPU $\rightarrow$ Local GPU $\rightarrow$ Cloud).
*   **Manifold Projection**: `src/cohezion/flume/manifolds/translator.py` ($\mathbb{R}^{256} \rightarrow \mathbb{R}^{12}$).
*   **Specialist Agent**: `src/cohezion/agents/specialists/ecoresilience_agent.py` (4-Regime Cycle).

### 4. Assurance Layer (The Guardrails)
*   **Stability Guard**: `src/cohezion/compound/stability_guard.py` (HIHO Coherence $\ge 0.5$).
*   **Adversarial Review**: `src/cohezion/compound/triune_reviewer.py` (Physicist/Ecologist/Engineer).
*   **Meta-Review**: `src/cohezion/compound/meta_reviewer.py` (Prompt Rigor Audit).
*   **Compound Engine**: `src/cohezion/compound/eco_symphony.py` (Reflexive Convergence).

## 🧬 Bidirectional Logic Flow
`Copernicus Sensing` $\rightarrow$ `FLUME Latent` $\rightarrow$ `Manifold Coordinates` $\rightarrow$ `Triune Review` $\rightarrow$ `HIHO Stability` $\rightarrow$ `Refined Strategy`

## 🛠️ Hardware Mapping
- **Sensing**: Pixel devices (Local NPU).
- **Symphony**: AMD Ryzen AI MAX+ 395 (LPDDR5X 128GB UMA).
- **Calculation**: Ollama Cloud (31B Dense).

## 🔗 Related Documentation
- [[src/cohezion/swarm/providers/gemma4_model_card.md]] - Model Capabilities.
- [[HARDWARE_PROFILE_PRIME.md]] - Strix Halo Specifications.
