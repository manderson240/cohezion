# ARCHITECTURE: EcoResilience Distributed Swarm (Project Symphony)

## 1. The Symphony Graph: Regime-Aware Orchestration
The system utilizes a la-phase cycle, transitioning through four distinct computational regimes to bridge Indigenous Traditional Ecological Knowledge (TEK) with Unified Physics.

### 🔄 Regime Flow & Contracts

| Regime | Model Target | Hardware | Input Contract | Output Contract | Purpose |
| :--- | :--- | :--- | :--- | :--- | :--- |
| **SENSING** | Gemma4-2B/4B | NPU (XDNA2) | `Field Report` + `CopernicusState` | `SensingInsights` (Text + Latent) | Extract ecological interconnectedness & systemic balance. |
| **CALCULATION** | Gemma4-31B | Cloud (H100) | `SensingInsights` (Sovereignty-Scrubbed) | `ManifoldProjection` ($\mathbb{R}^{12}$) | Map TEK to 12D physics manifold for HIHO stability. |
| **SYNTHESIS** | Gemma4-26B-MoE | GPU (RDNA3.5) | `ManifoldProjection` + `SensingInsights` | `ProposedStrategy` (Text) | Synthesize sustainable state based on Unified Physics. |
| **STEERING** | Gemma4-4B | NPU (XDNA2) | `ProposedStrategy` + `TriuneCritique` | `ImplementationAction` (Text) | Refine strategy for immediate local deployment. |

---

## 2. The la-Phase Core Components

### 🛡️ Sovereignty Fortress (Privacy Layer)
**Location**: `src/cohezion/protocols/sovereignty/filter.py`
**Mechanism**: A deterministic scrubbing layer applied at the boundary of `SENSING` $\rightarrow$ `CALCULATION`. It ensures zero-leakage of sacred TEK identifiers into cloud endpoints via replacement mapping and regex-based masking.

### 📐 Manifold Projection (The Physicality Guard)
**Location**: `src/cohezion/flume/manifolds/translator.py`
**Mechanism**: Maps 256D FLUME latent vectors into a 12D physical state. Stability is measured via HIHO coherence ($\text{coherence} \ge 0.4$), which serves as the "Symmetry Gate" for the system.

### ⚖️ Triune Review & Red Team (The Consensus Engine)
**Location**: `src/cohezion/compound/triune_reviewer.py`
**Mechanism**: 
1. **Consensus**: Perspectives from Physician, Ecologist, and Engineer.
2. **Symmetry Breaker**: An `AdversarialRedTeamAgent` performs a stress test on the synthesis to identify coherence holes or inferred TEK leakage.
3. **Veto**: A hard veto is triggered if the Red Team detects a "Sovereignty Breach" or a "Physical Impossibility."

---

## 3. Hardware Optimization (Symphony Max)

### ⚡ Lemonade-SOTA Configuration
- **LPDDR5X UMA Pooling**: Implements a `Symphony` mode pinning policy to keep the `26B-MoE` weights resident, eliminating regime-shift jitter.
- **Triton-Saliency Pruning**: Adaptive KV-cache pruning in `Gemma4Provider` ($0.1 \rightarrow 0.3$ threshold) to maximize throughput on the Strix Halo NPU.
- **MXFP4 Block-Scaling**: Fused E8M0 quantization for the MoE layer to reduce memory bandwidth pressure.

## 4. BMad-Alignment & Protocol Standard
- **Skill Composition**: Uses `Stitch-Skills` for dynamic la-phase thread composition.
- **State Handoffs**: All inter-regime transitions are wrapped in `AgentHandoff` packets (Google AI Agent Protocols), ensuring a traceable "Symphony Journey."
