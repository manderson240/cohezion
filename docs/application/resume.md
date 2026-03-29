# Mike Anderson

**Research Engineer** | Physics-Grounded Agentic Training Environments | RL Systems | ML Infrastructure

---

## Summary

Research engineer building physics-grounded training environments for agentic AI. Creator of Cohezion, a 12D/2048D manifold-based universe engine with Gymnasium-compatible RL environments, Lagrangian dynamics, and a complete trajectory-to-training pipeline. Demonstrated results in kernel optimization (423x speedup), quantum simulation (36-qubit MPS, SNR 9,947 sigma), and GPU kernel engineering (MI355X). 5,919 tests, 2,684 commits, one developer.

---

## Cohezion: 12D Agentic Universe Engine

*Solo project, 2,684 commits | Python, PyTorch, Gymnasium, SurrealDB*

### Training Environments

- Designed and implemented **ManifoldEnv**: a Gymnasium-compatible RL environment where agents navigate a 12-dimensional Riemannian manifold governed by Euler-Lagrange equations, SU(2) spinor coherence, and Yang-Mills gauge fields. 19D observation space (12D state + 3D Bloch vector + 4D fiber base), 12D continuous action space. Registered as `Cohezion/ManifoldEnv-v0`.
- Built **SwarmEnv**: a multi-agent environment (PettingZoo-compatible) where N agents interact through gauge field coupling on the same manifold. Each agent's motion generates curvature affecting other agents' dynamics. Cooperative objective with mixed individual/collective reward shaping.
- Implemented **ARCEnvironment**: Gymnasium wrapper for ARC-AGI-3 interactive games with a 12D manifold projection bridge (`to_12d`) for JEPA/FLUME encoding of visual observations.
- Created **5 task archetypes** with 4 difficulty levels each (20 TaskSpecs): HIHO Basin Navigation, TRIUNE Balance, Interruption Recovery, Exotic Charge Tolerance, and Kordylewski Orbit Maintenance. Interruption Recovery directly tests the ability to maintain context and recover coherence after mid-episode perturbation.
- Built a **10-step cosmogony** (symmetry-breaking cascade from SO(12) to HIHO equilibrium via Landau phase transitions) that generates diverse initial conditions for environment episodes.

### Reward Shaping and RL

- Implemented **HIHO coherence** as a physics-grounded reward signal: agents are rewarded for approaching the free energy minimum at coherence 0.5, with energy efficiency bonus and JEPA surprise penalty. This is equivalent to Friston's variational free energy minimization, providing a principled reward landscape.
- Built the **TRIUNE policy network** (Knower/Thinker/Doer, 256D to 12D), a 3-tier hierarchical architecture trained with PPO (clip epsilon 0.2, GAE lambda 0.95, Adam lr 3e-4).
- Created the **LLM Training Bridge**: converts 12D universe trajectories into RLHF rewards (coherence to scalar), DPO preference pairs (trajectory comparison by HIHO proximity), and judgment assessments. Includes `JourneyToTrainingBridge` for end-to-end pipeline from journey capture to training export.
- Implemented Lagrangian dynamics with a **symplectic Stormer-Verlet integrator** for bounded energy drift, fabric-block Riemannian metric, and HIHO Gaussian attractor potential.

### Evaluation and Metrics

- Designed a **6-axis CapabilityScorecard**: Coherence Amplitude, Phase Locking, Exotic Charge Lifetime, Orbit Quality, TRIUNE Balance, and Recovery Basin Radius. Each axis has a defined physics interpretation and maps to a distinct agent capability.
- Implemented **full statistical rigor**: bootstrap 95% CIs (1,000 samples), Mann-Whitney U tests, Bonferroni correction across 6 metrics x N archetypes, and power analysis for minimum detectable effect sizes.
- Built a **compound evaluation loop**: RequestAlignmentAnalyzer (coherence/completeness/drift-risk), DegradationDetector (thermal and quality thresholds), JourneyTracker (full 12D trajectory recording), and RetrospectionEngine (automated pattern extraction and anomaly flagging).

### World Model

- Implemented a **JEPA World Model** (~86K parameters): ManifoldEncoder (12D to 64D with Gaussian reparameterization), ActionEncoder (12D to 64D), Predictor (128D to 64D). Causal masking upgrade (inspired by Causal-JEPA, arXiv:2602.11389) forces learning of causal relationships.
- Built **surprise-driven exploration**: SurpriseExplorer scans the manifold for regions where JEPA predictions diverge from reality, driving exploration toward novel states.
- Implemented **TDA-driven swarm optimization**: persistent homology classifies agent trajectories into topological regimes (H0 clusters for specialization, H1 loops for stuck agents), driving topology-aware task routing.

### Sandboxing and Infrastructure

- Built a **multi-backend sandbox system**: ContainerizedUniverse (Docker isolation with memory/CPU limits), SystemdRunBackend (cgroups via systemd-run), SubprocessBackend (setrlimit fallback). Protocol-based abstraction with automatic backend selection. SandboxManager tracks active sandboxes and enforces a system-wide memory budget with DivergenceDetector per sandbox.
- Implemented a **distributed multi-agent swarm** with QuadratureNexus (4-voice consensus governance: Architect/Engineer/Ethicist/Resource), CostAwareRouter (27.3% cost reduction via complexity-based model selection), and TopologicalRouter (persistent homology for agent routing).
- Built **SemanticCache** (L1 hash + L2 cosine + L3 vault, 95%+ hit rate) and a compound engineering loop with automatic retrospection, skill refinement, and multi-agent consensus voting.
- **5,919 tests** across the full stack with singleton isolation patterns for FLUME VAE, RL policy, and loggers. 160+ learnings extracted and persisted in vault.

### Physics Engine

- Implemented the complete physics stack: SU(2) spinors (Bloch sphere representation, Fubini-Study metric), Riemannian metric (fabric-block structure), Lagrangian and Hamiltonian dynamics, fiber bundles (P(B^4, SO(3)^4) principal bundle with base/fiber decomposition), Yang-Mills gauge theory (SO(3) gauge connections with 4 coupling constants), Fisher information metric (Rosetta Stone unifying geometry, dynamics, thermodynamics, and projection), and cosmogony (Landau phase transition cascade).
- The **FLUME VAE** (256D latent, transformer encoder/decoder, 4 heads, 2 layers) provides the Fisher metric that simultaneously defines the Riemannian geometry, kinetic energy for Lagrangian mechanics, thermodynamic metric, and optimal 256D to 12D projection.

---

## Competition Results

| Competition | Result | Technique |
|---|---|---|
| **Anthropic VLIW Challenge** | **423x speedup** (349 cycles, bit-exact) | Systematic kernel optimization via compound engineering loop |
| **BlueQubit Quantum** | **36-qubit simulation, SNR 9,947 sigma** | Matrix Product State decomposition |
| **Luma AMD Speedrun** | 3 GPU kernels on MI355X (GEMM, MoE, MLA) | HIP kernel optimization, active competition |
| **AIMO Progress Prize 3** | 1,048,576-phase compound engineering campaign | Multi-phase reasoning with skill refinement |

---

## Research

**"FLUME and the Genesis Engine: Physics-Grounded Agentic Environments via Manifold Encoding"** (27 citations)

Demonstrates that the Fisher information metric on a VAE latent space simultaneously serves as the Riemannian metric for dynamics, the thermodynamic metric for statistical mechanics, and the projection operator for dimensionality reduction. Implements the first Gymnasium-compatible RL environment grounded in differential geometry and gauge theory.

---

## Technical Skills

**Languages**: Python 3.13+, PyTorch, CUDA/HIP, assembly (VLIW)
**ML/RL**: PPO, DPO, RLHF, Gymnasium, Stable-Baselines3, JEPA, VAE
**Infrastructure**: Docker, systemd sandboxing, SurrealDB, FastAPI (55 endpoints), FastMCP
**Math**: Riemannian geometry, Lagrangian mechanics, gauge theory, persistent homology, information geometry
**Hardware**: AMD Ryzen AI MAX+ 395 (AVX-512, AMX), Radeon 8060S, 128GB LPDDR5X

---

## Education

*[To be filled in by Mike]*
