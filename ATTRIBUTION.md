# Academic Attribution, Benchmark Provenance & Licensing Compliance

**Project**: Cohezion AI Swarm Orchestration Framework  
**Root License**: [GNU Affero General Public License v3.0 or later (AGPL-3.0-or-later)](LICENSE)  
**Copyright**: (c) 2026 Mike Anderson & Cohezion Contributors  

---

## 1. Academic & Theoretical Foundations

Cohezion operationalizes foundational theorems, mathematical principles, and bleeding-edge research papers from AI, cybernetics, differential geometry, and theoretical physics. We gratefully credit the original authors and institutions:

### A. Agentic Verification & Recursive Learning
- **AutoHarness** (Code-as-Action Verifiers & Bytecode Policy Synthesis):
  - *Citation*: AutoHarness: Deterministic Verification and Policy Synthesis for Autonomous Agents. arXiv:2603.03329v1 (2026).
  - *Application*: `src/cohezion/agi/autoharness_policy.py`, AST verification, zero-cost bytecode policies.
  - *License/Usage*: Academic research prior; implemented as cleanroom Python AST policies.

- **LLM-to-Flow Distillation (LFD)**:
  - *Citation*: De Santi, R., Di Gennaro, M., Gnazzo, A., Tang, K., Chatterjee, S., Yang, K., Ceylan, H., Bronstein, M., & Krause, A. *LLM-to-Flow Distillation: Teaching Natural Language Goals to Scientific Generators*. arXiv:2610.17246 (Oct 2026).
  - *Application*: `src/cohezion/physics/lfd_distiller.py`, Bradley-Terry flow DPO, permutation-invariant preference filtration, continuous geodesic steering.

- **Terminal-RSI (Success-Prioritized Reward)**:
  - *Citation*: *Terminal-RSI: Success-Prioritized Reward and Invariant Monotonicity in Recursive Self-Improvement*. arXiv:2610.22192 (Oct 2026).
  - *Application*: `src/cohezion/agi/recursive_self_improvement.py`, Success-Prioritized Reward ($R_{\text{SPR}} \in [1.0, 2.0)$ vs $[0.0, 1.0)$), ZKFV polynomial certification.

- **Weight-Harness Co-Evolution (Evo$^2$ / EvoTIDE)**:
  - *Citation*: *Evo$^2$: Dual-Role Policy Decomposition and Evolutionary Trajectory Recovery*. arXiv:2610.12842 (Oct 2026).
  - *Application*: `src/cohezion/compound/evo2_coevolution.py`.

### B. Cybernetics & Systems Theory
- **Stafford Beer — Viable System Model (VSM)**:
  - *Works*: *Brain of the Firm* (Allen Lane, 1972); *The Heart of Enterprise* (John Wiley & Sons, 1979).
  - *Application*: `src/cohezion/platform/equilibrium_governor.py`, 5-tier VSM mapping (System 1 Operations to System 5 Purpose/Policy).

- **W. Ross Ashby — Law of Requisite Variety**:
  - *Work*: *An Introduction to Cybernetics* (Chapman & Hall, 1956).
  - *Core Theorem*: "Only variety can destroy variety."
  - *Application*: Multi-tier hierarchical entropy absorption (AutoHarness, MBSE contracts, 2048D Poincaré manifold, autogenic inhibition).

- **R.C. Conant & W. Ross Ashby — Conant-Ashby Theorem**:
  - *Citation*: Conant, R. C., & Ashby, W. R. (1970). *Every good regulator of a system must be a model of that system*. International Journal of Systems Science, 1(2), 89-97.
  - *Application*: The 2048D Poincaré ball model as Cohezion's internal isomorphic world model.

### C. Differential Geometry & Theoretical Physics
- **Henri Poincaré — Hyperbolic Geometry**:
  - *Works*: *Théorie des groupes fuchsiens* (Acta Mathematica, 1882); *Sur les hypothèses de la géométrie* (1887).
  - *Application*: `src/cohezion/physics/poincare_manifold.py`, `src/cohezion-physics-core/src/lib.rs`, Poincaré distance, Möbius addition, CTAC conformal scaling.

- **Ilya Prigogine — Dissipative Structures & Non-Equilibrium Thermodynamics**:
  - *Work*: Nobel Prize in Chemistry (1977); *Order Out of Chaos* (1984).
  - *Application*: Negentropy Invariant ($\Delta S \le 0$) in recursive self-improvement and swarm trajectory convergence.

- **Roger Penrose & Stuart Hameroff — Twistor Theory & Orch-OR**:
  - *Citation*: Hameroff, S., & Penrose, R. (1996). *Orchestrated reduction of quantum coherence in brain microtubules: A model for consciousness*. Mathematics and Computers in Simulation, 40(3-4), 453-480.
  - *Application*: `src/cohezion/physics/quantum_twistor.py`, HIHO 0.50 stability attractor.

- **Claude E. Shannon — Information Theory**:
  - *Citation*: Shannon, C. E. (1948). *A Mathematical Theory of Communication*. Bell System Technical Journal, 27(3), 379-423.
  - *Application*: Shannon entropy calculation, Signal-to-Noise Ratio (SNR) in synthesized artifacts.

- **John von Neumann — Automata & Game Theory**:
  - *Work*: *Theory of Self-Reproducing Automata* (Univ. of Illinois Press, 1966).
  - *Application*: Autopoietic agent state machines and Minimax arbitration in multi-agent debate.

- **Leslie Lamport — Logical Time & Distributed Consensus**:
  - *Citation*: Lamport, L. (1978). *Time, clocks, and the ordering of events in a distributed system*. Communications of the ACM, 21(5), 558-565.
  - *Application*: `EventBus` causal ordering, vector clocks, and cross-session event bridging.

---

## 2. Competitive Kaggle Benchmarks & Datasets

Cohezion actively participates in competitive scientific benchmarks hosted on Kaggle. All training and evaluation protocols strictly adhere to official competition terms and platform rules:

| Benchmark / Competition | Host / Sponsoring Organization | License / Terms of Use | Compliance & Usage Discipline |
|---|---|---|---|
| **ARC Prize (ARC-AGI-1, ARC-AGI-2, ARC-AGI-3)** | François Chollet / ARC Prize Foundation | Apache-2.0 / CC-BY-4.0 / Competition Rules | Pure offline code competition. Zero external internet access during evaluation. No memorization of test sets. |
| **Enveda CASMI26 (Molecule ID Mass Spectra)** | Enveda Biosciences & CASMI | Contest Rules / Academic Research | Mass spectrometry ionization & neutral loss matching. Used exclusively for competitive scientific evaluation. |
| **RSNA Knee Abnormality Detection** | Radiological Society of North America (RSNA) & Osteoarthritis Initiative (OAI) / NIH | RSNA Non-Commercial Research License | Anonymized clinical DICOM imagery. Used strictly for academic research and competition evaluation. |
| **Name That LLM** | Kaggle Competitions Platform | Competition Rules / Creative Commons | Stylometric classification of anonymized model generation outputs. |
| **Google Gemma 4 Developer Agent** | Google LLC | Gemma Terms of Use / Competition Rules | Dockerized container evaluation of autonomous code modification agents. |

---

## 3. Industry-Standard Evaluation Suites

| Benchmark | Authors / Organization | License | Repository / Source |
|---|---|---|---|
| **SWE-bench & SWE-bench Verified** | Carlos E. Jimenez, John Yang, Alexander Wettig, Shunyu Yao, Karthik Narasimhan, Ofir Press (Princeton NLP) | MIT License | `github.com/princeton-nlp/SWE-bench` |
| **GAIA (General AI Assistants)** | Grégoire Mialon et al. (Meta FAIR, Hugging Face, AutoGPT) | CC-BY-4.0 | `huggingface.co/datasets/gaia-benchmark/GAIA` |
| **MLPerf Inference** | MLCommons Association | Apache-2.0 | `github.com/mlcommons/inference` |
| **EvalPlus (HumanEval+ & MBPP+)** | Jiawei Liu et al. (UIUC) | Apache-2.0 | `github.com/evalplus/evalplus` |
| **WildJailbreak / WildChat** | Allen Institute for AI (AI2) | Apache-2.0 | `allenai.org/data/wildjailbreak` |

---

## 4. Hardware Platforms, Silicon Runtimes & Infrastructure

| Technology | Creator / Maintainer | Upstream License | Cohezion Integration |
|---|---|---|---|
| **AMD ROCm & XDNA 2 NPU** | Advanced Micro Devices, Inc. (AMD) | MIT / AMD Open Source | FastFlowLM SRAM compilation on XDNA 2, UMA aperture management. |
| **Ollama** | Ollama Authors | MIT License | Local and cloud model streaming gateway. |
| **Bun Runtime** | Oven-sh | MIT License | High-throughput TypeScript execution, fast AST parsing, and sandboxing. |
| **Rust Programming Language** | The Rust Foundation & Contributors | MIT OR Apache-2.0 | Native PyO3 SIMD kernels (`cohezion_physics_core.so`), background sentinels. |
| **SurrealDB** | SurrealDB Ltd. | Business Source License (BSL 1.1) / Apache-2.0 | Dual-store hyper-relational knowledge mesh and experiment telemetry. |
| **Apache Arrow / PyArrow** | Apache Software Foundation | Apache-2.0 | Shared-memory IPC meshes (`src/cohezion/data_mesh/shm_mesh.py`). |
| **FastMCP** | FastMCP Contributors | MIT License | Low-overhead Model Context Protocol microservice endpoints. |

---

## 5. Software Bill of Materials (SBOM) & Dependencies

For a complete, automated manifest of all 285+ installed open-source libraries across Python, Rust, and TypeScript—including author, version, and license compatibility classification—see:

👉 **[`THIRD_PARTY_LICENSES.md`](THIRD_PARTY_LICENSES.md)**

---

## 6. Ethical Compliance & Data Governance

1. **Zero Contamination Invariant**: No evaluation holdout sets (SWE-bench private tests, ARC test splits, Kaggle private test data) are ever incorporated into training data or prompt memory.
2. **Patient Data Privacy**: All medical imaging used in RSNA benchmarks is fully anonymized and devoid of Protected Health Information (PHI) under HIPAA guidelines.
3. **Reproducibility & Auditability**: All benchmark runs are backed by deterministic seed configurations, formal ZKFV polynomial certificates, and immutable telemetry in SurrealDB and the Obsidian Vault.
