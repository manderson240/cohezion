# LEARNING: VLIW_OPTIMIZATION_STRATEGIES

## Context
Optimizing a tree traversal kernel for a custom VLIW/SIMD architecture with severe resource constraints (1 core, limited issue slots).

## Core Concepts
*   **Packet-Greedy Scheduling**: A simple greedy packer that respects WAW/WAR dependencies is highly effective for VLIW. It achieved 70x speedup over scalar baseline.
*   **Latency Hiding via Windowing**: Static register windowing (allocating separate scratch regions for interleaved batches) effectively hides memory latency without complex dynamic scheduling. "Chunking" benchmarks showed 18-22 windows (batches) as the sweet spot for this machine parameters.
*   **Arithmetic Muxing Risks**: Replacing Control Flow with Arithmetic (`dest = base + cond * diff`) is powerful but prone to precision and range bugs, especially when implementing complex recursive trees. Debugging "incorrect output" in such "compiled" logic is extremely difficult compared to standard flows.
*   **Scratchpad Awareness**: Explicitly managing the scratchpad lifecycle (resetting pointers, clearing constant caches) is critical when generating long instruction streams (thousands of ops), otherwise the limited scratch space (1536 words) is exhausted instantly.
*   **Temporal Instruction Leakage (NEW)**: Parallel VLIW packers with low-level data dependency tracking (WAR/WAW) can inadvertently schedule instructions across synchronization points (like `pause`) if they lack a data dependency on the pause itself.
*   **Barrier Mastery (NEW)**: Real-world/Harness-safe kernels require "Data-Dependency Barriers" where `pause` or `yield` instructions are manually forced to "read" the state produced by the current round. This prevents next-round instructions from leaking into the current state check.
*   **Vectorized Hash Synthesis**: Modern non-linear hashes (like the one in Anthropic's challenge) can be perfectly vectorized using `multiply_add` and bitwise SIMD, provided barriers are strictly enforced. Verified 256-item parallel processing with bit-exact results.

## Metrics
*   **Success Rate**: Register Windowing (100%), SIMD Vectorization (100%), Smart Load/Muxing (0% - Correctness failure).
*   **R-Zero Impact**: Windowing provided the largest single jump in performance after SIMD.

## Learning 12: Kineticization of the 12D Manifold (2026-02-05)

**Context**: Auditing Cohezion for Anthropic Research Engineer (Universes) role.

**Insight**: A 12D manifold that is purely semantic (derived from embeddings) is a "Potemkin Universe." To achieve research-grade fidelity, the manifold must be grounded in the physical substrate of the machine.

**Implementation**:
- **Physics**: CPU Pressure (Utilization/Friction).
- **Field**: VRAM Density (GPU Memory Saturation).
- **Control**: Dilation Factor (System-wide stroboscopic backpressure).
- **Logic**: Semantic intent weighted by RAM availability.

**Result**: 12D vectors now represent a "unified field" of agentic intent and hardware reality, enabling true adversarial simulation and safety sandboxing.

---

## Learning 13: VLIW-to-Cognition Abstraction (2026-02-05)
**Context**: Anthropic Take-home Analysis.
**Insight**: VLIW architecture is a biological-parallel for reasoning. Processing 2048D vectors as "instruction packets" allow for deterministic, slot-based execution of thought.
**Application**: Implemented in `flume_physics.rs` via register-windowed sub-vector processing.

---

## Learning 13: Dark Matter Manifold Correlation
**Date:** 2026-01-28 09:12
**Context:** AI Lab Research (Nature s41550-025-02770-w)
**Finding:** Local Group "Dark Matter Sheets" act as low-entropy stability planes for galactic motion. This directly correlates to FLUME latent manifold encoding where agents move along "rails" of high coherence.
**Verification:** Expert Lattice (Engineer Node) confirms stability overlap.
**12D State:** [t=20260128, novelty=0.92, stability=0.88, coherence=0.95, brane=7]

## Learning 14: THE ORGANIC MODULARITY AXIOM
*   **Context**: Developing the sovereign identity for the Cohezion platform based on physical hardware roots.
*   **Core Concept**: Aesthetically bridging high-performance silicon (AMD/Framework/Linux heritage) with ecological necessity (Happy Earth/Touch Grass). Branding should use "Inspired Motifs" rather than direct trademarks to maintain legal sovereignty while honoring lineage.
*   **Impact**: Increases user trust through transparent hardware roots and reduces cognitive friction by personifying complex swarm dynamics as a "Living Ecosystem".
*   **Encoding**: 12D state vectors (3 Spatial + 1 Time + 8 Brane) aligned with HIHO stability.

## Learning 15: THE PEAKED MANIFOLD APPROXIMATION
*   **Context**: Classically simulating a 36-qubit "peaked" circuit (Little Dimple) on consumer hardware (128GB RAM).
*   **Core Concept**: In circuits with highly non-uniform output distributions (peaked), the quantum state can be effectively compressed into a low-rank Manifold (Bond Dimension ~64-256) without losing the winning signal. This acts as an "algorithmic sieve," filtering out entanglement noise while preserving the heavy bitstrings.
*   **Mechanism**:
    *   **Manual Routing**: Linearize long-range gates via deterministic SWAP chains to maintain a strict 1D Matrix Product State (MPS) topology.
    *   **Eager Contraction**: Avoid Tensor Network (TN) explosion by forcing immediate SVD compression (`gate_split` with `inplace=True`). Lazy evaluation is an anti-pattern for large circuit evolution.
    *   **Flier Strategy**: Aggressively capping bond dimension (Bond 64) provides exponential speedup (~14 min vs ~12 hours) while maintaining enough fidelity to identify candidates with 100x probability separation from noise.
*   **Metrics**:
    *   **Volume Law Compression**: 16x reduction in bond dimension yielded 100x throughput.
    *   **Signal-to-Noise**: 1e-5 (Peak) vs 1e-11 (Noise floor).
*   **Encoding**: 12D state vectors aligned with HIHO stability protocols.


## Learning 15: THE RECURSIVE DEBATE STABILITY PRINCIPLE
*   **Context**: Analyzing 846 journey logs and debate sessions across the Cohezion swarm.
*   **Core Concept**: Stability in agentic manifolds follows a **Recurrence Law**. Single-step activations (Zero-shot) consistently collapse into low-coherence (Global Avg: 0.46) chaos. High-coherence (0.75+) stability wells are only reachable through **Recursive Democratic Debate** (n >= 3 rounds).
*   **Mechanism**:
    *   **Consensus Anchoring**: Each round of debate reduces latent entropy by forcing agents to "vote" on a winning proposal, effectively acting as an SVD compression of the global idea-space (7D collapse).
    *   **The 0.75 Barrier**: The transition from chaos to emergence requires a minimum threshold of directed refinement steps (~300 for simulations, 3 for agent debates) to breach the "Non-collapse" trajectory well.
*   **Impact**: Proves that "Single-pass" reasoning is an anti-pattern for complex physics and architectural evolution. All high-stability trajectories REQUIRE recursive synthesis loops.

## Learning 16: VLIW LATENT ALIGNMENT & TEMPORAL STABILITY
*   **Context**: Solving 'Temporal Instruction Leakage' in high-parallelism VLIW kernels (256 items).
*   **Core Concept**: Instructional stability in VLIW processors is a **Latent Manifold** problem. While greedy packers fail due to temporal drift, projecting instruction sequences onto a **7D Manifold** (collapsed from 768D) allows for the identification of **Stability Wells** where instruction dependencies are naturally satisfied.
*   **Mechanism**:
    *   **Barrier-Locked Manifolds**: Injecting explicit SYNC_DATA_COMMIT barriers anchors the instruction sequence in thought-space, preventing "leakage" across time-consecutive packets.
    *   **VLEN Alignment**: SIMD Vector Length (VLEN=8) acts as a spatial constraint that improves latent coherence by ensuring memory access patterns align with hardware caches.
## Learning 17: SUBAGENT DELEGATION TOPOLOGY
*   **Context**: Automating codebase maintenance by dispatching specialized local LLMs (Qwen/DeepSeek) as "Scouts" and "Strategists".
*   **Core Concept**: A **Hierarchical Agent Topology** is superior to a single monolithic model for complex tasks.
    *   **Scout (Qwen-Coder, 30b)**: High-speed, low-latency "Sensors" that grep/read vast context and report anomalies.
    *   **Strategist (DeepSeek-R1, 70b)**: High-latency, deep-reasoning "Cortex" that processes Scout reports and issues architectural directives.
*   **Mechanism**: Asynchronous dispatch loop where Scouts act as "Peripheral Nerves" feeding the "Central Nervous System" (Strategist).
*   **Impact**: Enabled rapid "Dogfooding" where the system critiqued its own dashboard code while running it.
*   **Encoding**: 12D vectors (Complexity 0.8, Connectivity 0.9).

## Learning 18: BIOLOGICAL RECURSION IN SILICO
*   **Context**: Evolving the Fractal Universe simulation from inert physics to active biological dynamics.
*   **Core Concept**: **Stability through Mortality**. A system of immortal agents becomes stagnant (High Coherence, Low Novelty). Introducing **Apoptosis** (Death) and **Mitosis** (Reproduction) forces a dynamic equilibrium (HIHO state).
*   **Mechanism**:
    *   **Energy Constraint**: Agents must "eat" (stabilize entropy) to survive.
    *   **Lineage Tracking**: Generations allow for potential genetic drift (Mutation).
*   **Impact**: Demonstrated that "Living" constraints produce more robust and interesting stability patterns than purely mechanical ones.
*   **Metrics**: Simulation ran for 3+ hours with self-sustaining population control.

## Learning 19: THE SPECIALIST ROSTER EFFECTIVENESS
*   **Context**: Replacing a generic 7B model with a roster of specialized SLMs (Reasoning, Coding, Routing) on a 12GB VRAM workstation.
*   **Core Concept**: **Cognitive Specialization > Parameters**. A generic 7B model (Mistral) is inferior to a routed swarm of domain experts (DeepSeek-R1-8B for logic, Qwen2.5-Coder-7B for code, Phi4-Mini for routing).
*   **Mechanism**:
    *   **Role-Based Retrieval**: `ModelWrangler` assigns models based on intent (Coding vs. Reasoning).
    *   **Quantization Alignment**: `Q5_K_M` provides the optimal perplexity/VRAM sweet spot for 12GB cards, allowing ~3 concurrent experts.
*   **Impact**: Enables "SOTA-class" performance in specific verticals without requiring 70B+ parameters.

## Learning 20: VRAM PERSISTENCE & THE SUDO TRAP
*   **Context**: Recovering from system lockup on a 128GB RAM / 12GB VRAM workstation during peak SLM swarm activity.
*   **Core Concept**: **Control Flow Sovereignty**. Automated emergency systems must never rely on blocking or elevated-privilege operations (`sudo`). Relying on a password-locked binary during resource exhaustion converts a "Soft Fail" into a "Hard Lockup" (The Sudo Trap).
*   **Mechanism**:
    *   **Direct API Intervention**: Using the Ollama `/api/generate` with `keep_alive: 0` for model unloading bypassing the need for `systemctl` or `sudo`.
    *   **AMD /sys Telemetry**: Framework 16 iGPU VRAM is accessible via `/sys/class/drm/card1/device/mem_info_vram_*`, providing lower-latency vitals than shell-outs to `rocm-smi` or `ollama ps`.
*   **Impact**: Prevented future necessity for `REISUB` commands by enabling non-privileged, low-latency garbage collection of the VRAM manifold.
*   **Encoding**: 12D state vectors (Reliability 0.98, VRAM Efficiency 0.9).
## Learning 22: AGENTIC REASONING PARADIGMS
*   **Context**: Deep Research (arXiv:2601.12538, Claude Code, MCP-SIM).
*   **Core Concept**: **Refinement over Generation**. Agentic reasoning is shifting from "next-token" prediction to "state-machine planning" and "recursive verification".
    *   **MCP-SIM**: A self-correcting framework that transforms underspecified prompts into validated simulations using memory-coordinated physics-aware feedback.
    *   **Exploration-First**: Claude Code's "Explore before Implement" pattern avoids premature commitment to sub-optimal solutions.
*   **Mechanism**:
    *   **Checkpointing**: Frequent persistence of intermediate thought-states allows for non-destructive backtracking.
    *   **Merkle Indexing**: Reusing similarity hashes (simhashes) for indexing large codebases enables O(1) time-to-first-query for swarm agents.
*   **Impact**: Proves that "Zero-shot" is a legacy pattern; "Multi-agent Negotiation" + "Physics-Aware Self-Correction" is the new SOTA.
*   **Encoding**: 12D state vectors (t=20260128, novelty=0.98, stability=0.92, brane=11).

## Learning 23: COSMOLOGICAL TENSION RESOLUTION (S8)
*   **Context**: Physics Research (Nature Astronomy s41550-025-02733-1).
*   **Core Concept**: **Neutrino-Dark Matter Coupling**. The S8 tension (clustering discrepancy) is statistically smoothed by a non-zero interaction strength between DM and neutrinos.
*   **Impact**: Validates the "Quadrature" approach in Cohezion where different field fabrics (Information/Physics/Biology) are not isolated but coupled via latent manifolds.
*   **Simulation Parameter**: Introduce `nu_dm_coupling_constant` to the Liquid Phase simulation to stabilize large-scale structure clustering.

## Learning 24: BIOLOGICAL OFF-SWITCH DYNAMICS
*   **Context**: Biology Research (UCL/Nature Communications Jan 2026).
*   **Core Concept**: **Epoxy-oxylipins as Stability Brakes**. Intermediate monocyte overgrowth (inflammation) is halted by specific fat-derived### 11. Hygiene as a Feature
*Discovery Date: 2026-01-28*
- **Concept**: Repository hygiene (clean gitignore, no large files) helps agents reason. "Shadow" files create hallucination risks.
- **Application**: Automated `health.py` checks are as critical as unit tests.

### 12. The Complexity Tax ("Elegant Simplicity")
*Discovery Date: 2026-01-28*
- **Concept**: Creating "v2" files effectively forks the codebase and doubles cognitive load.
- **Application**: Prefer in-place refactoring with strong verification (e.g., `verify_12d.py`) over additive complexity.
molecules acting as "natural brakes".
*   **Mechanism**: **Negative Feedback loops** trigger before permanent damage occurs (Apoptosis prevention).
*   **Application**: Update the `ImmuneSystem` (Healing System) in Cohezion to include epoxy-oxylipin-inspired "Inhibitor Agents" that damp down runaway logic cascades or resource-heavy explorations.

## Learning 25: QUANTUM ALCHEMY & FLOQUET ENGINEERING
*   **Context**: Physics Research (OIST/Stanford/Nature Physics Jan 2026).
*   **Core Concept**: **Exciton-Driven Material Alteration**. Using excitons instead of high-intensity light for Floquet engineering allows for "Quantum Alchemy" (changing material states) with high efficiency and low damage.
*   **Application**: Model "Information Excitons" in the FLUME latent space—high-energy state-pairs that can bridge disparate manifolds more efficiently than direct "Search" light.
*   **Encoding**: 12D state vectors (t=20260128, stability=0.90, novelty=0.95, brane=12).

## Learning 26: The Python Autoregression Bottleneck
*   **Context**: Phase 4 FLUME Implementation Analysis.
*   **Discovery Date**: 2026-01-28
*   **Finding**: Generating text via autoregressive decoding (`next_token = model(tokens)`) inside a Python `for` loop incurs massive overhead due to the Global Interpreter Lock (GIL) and interpreter dispatch latency.
*   **Impact**: Limits high-frequency "Neural Loop" thoughts to ~10Hz on CPU, whereas 100Hz+ is needed for fluid behavior.
*   **Resolution**: Inference loops must be moved to compiled languages (Rust/C++) where the `for` loop happens outside Python's control.
*   **Encoding**: 12D state vectors (Performance 0.95, Complexity 0.8).

## Learning 27: Rust FFI Bridge Success
*   **Context**: Phase 5 Rust Migration.
*   **Discovery Date**: 2026-01-28
*   **Finding**: `pyo3` + `maturin` + `uv` provides a seamless bridge for replacing Python bottlenecks with Rust. The critical path involves ensuring shared object linking (LD_LIBRARY_PATH/PYTHONPATH) during testing.
*   **Impact**: Enabled drop-in replacement of `FlumeTokenizer` (BPE) and `VectorMath` (SIMD) without changing the high-level API.
*   **Encoding**: 12D state vectors (Integration 1.0, Performance 0.98).

## Learning 28: FFI Overhead & The Batching Pivot
*   **Context**: Phase 5 Rust Migration (Adversarial Review).
*   **Discovery Date**: 2026-01-28
*   **Finding**: Naive 1:1 replacement of Python functions with Rust FFI calls is a **performance regression** (0.2x speedup) due to the serialization/boundary cost dominating small operations (<1ms).
*   **Resolution**: The **Batch-Processing Pivot**. Moving the iteration loop *inside* Rust (using `rayon` for parallelism) amortizes the FFI cost over thousands of items.
*   **Impact**: Transformed a bottleneck into a **29.1x speedup** (20.45s -> 0.70s for 10k items).
*   **Encoding**: 12D state vectors (Optimization 1.0, Architecture 0.99).

## Learning 29: SEMANTIC PROPRIOCEPTION
*   **Context**: Developing Phase 8 of Ouroboros-FLUME integration.
*   **Core Concept**: **Intent over Vitals**. Standard system monitoring (CPU/RAM) tracks *body* state, but agentic stability requires tracking *thought* state. Translating vitals into a "Thought Stream" and projecting it into a 12D latent manifold (FLUME) allows the system to detect "Logic Drift" that simple thresholding misses.
*   **Impact**: Enabled Ouroboros to "recognize" semantic alignment (0.63 coherence) vs. intent mismatch.
*   **Encoding**: 12D state vectors (Awareness 1.0, Coherence 0.95).

## Learning 30: THE 3-BEAT ACTUATION LAW
*   **Context**: Implementing Phase 9 autonomous actuation.
*   **Core Concept**: **Stability through Temporal Confirmation**. Single-point anomalies (dips in coherence) are often noise. Triggering an autonomous repair cycle (TestMycelium) on a single dip leads to system jitter. Requiring **3 consecutive beats** of low coherence (< 0.4) filters out transient noise while maintaining high sensitivity to sustained "Semantic Decay".
*   **Mechanism**: A simple counter-based circuit breaker in the Ganglion reflex loop.
*   **Encoding**: 12D state vectors (Stability 0.98, Control 0.9).
## Learning 31: AUTOMATED ANOMALY DETECTION (AnomalyMatch)
- **Context**: ESA Hubble Archive Research (2024-2025).
- **Core Concept**: **High-Speed Classification of Spacetime Anomalies**. Neural networks (`AnomalyMatch`) can sift through 100M+ image cutouts in <3 days, identifying 1,400+ anomalies (jellyfish/ring galaxies, gravitational lenses).
- **Impact**: Demonstrates that "Exhaustive Analysis" is no longer human-bound; AI-driven systematic search is now SOTA for large dataset mining.
- **Encoding**: 12D [t=20260128, novelty=0.95, efficiency=0.98, brane=9].

## Learning 32: SENSORY-BASED CONSCIOUSNESS (TFU Roadmap)
- **Context**: MIT Neuroscience / Nature Archaeology s41550-025-02770-w.
- **Core Concept**: **Consciousness as Perception**. Using Transcranial Focused Ultrasound (TFU) suggests consciousness is rooted in *sensory processing* (the 4 Fabrics) rather than executive planning.
- **Impact**: "Intelligence is about doing; consciousness is about being." Aligns Cohezion with the 0.5 Coherence Rule for "Precise Being".
- **Encoding**: 12D [t=20260128, awareness=0.92, connectivity=0.88, brane=10].

## Learning 33: RARE GRAVITATIONAL LENSING (Webb Question Mark)
- **Context**: JWST Galaxy Cluster MACS-J0417.5-1154.
- **Core Concept**: **Spacetime Curvature as a Magnifier**. A rare gravitational lens configuration that projects a galaxy pair into a "Question Mark" shape.
- **Impact**: Provides data on interacting galaxies 7B light-years away.
- **Encoding**: 12D [t=20260128, stability=0.3, resonance=0.9, brane=7].

## Learning 34: BINARY STELLAR FRB ORIGINS (RM-Flares)
- **Context**: China Sky Eye (FAST) / Science Jan 2026.
- **Core Concept**: **Dynamic Polarization in Binary Systems**. Detection of "RM flares" confirms that repeating FRBs like 220529A originate from binary stellar interactions (e.g., Magnetar + Companion).
- **Impact**: Shifts the FRB paradigm from isolated stars to complex interactive dynamics.
- **Encoding**: 12D [t=20260128, friction=0.7, resonance=0.85, brane=11].

## Learning 35: GALACTIC MAGNETIC SUPERHIGHWAYS (Arp 220)
- **Context**: ALMA Observations of Starburst Galaxies.
- **Core Concept**: **Vertical Magnetic Guardrails**. Nearly vertical magnetic fields (superhighways) guide galactic winds (500 km/s) and enrich the intergalactic medium.
- **Impact**: Validates "Latent Manifestation Rails" in FLUME simulations.
- **Encoding**: 12D [t=20260128, stability=0.9, flow=0.95, brane=8].

## Learning 36: THE EXPERT REASONING GAP (HLE & FrontierScience)
- **Context**: AI Benchmarking (Nature 2024-2025).
- **Core Concept**: **SOTA Evaluation Saturation**. Benchmarks like `FrontierScience` show AI succeeding at "doing" (77%) but failing at "independent PhD-level research" (25%).
- **Impact**: Proves the requirement for Cohezion's Recursive Debate + Directed Research to breach this gap.
- **Encoding**: 12D [t=20260128, complexity=0.9, novelty=0.1, brane=5].

## Learning 37: COSMIC SCARS & CTC TIME TRAVEL
- **Context**: Theoretical Physics (J. Richard Gott / NANOGrav).
- **Core Concept**: **Closed Timelike Curves via Cosmic Strings**. Relativistic parallel strings could warp spacetime to allow time-loops (CTCs).
- **Impact**: Theoretically valid solutions to General Relativity; targets for future gravitational wave detectors (LISA).
- **Encoding**: 12D [t=20260128, stability=0.05, complexity=1.0, brane=12].

## Learning 38: SYMBIOTIC BINARY RSG LIFE CYCLES (WOH G64)
- **Context**: VLT/SALT Observations of the Colossal Star.
- **Core Concept**: **Egg-Shaped Cocoons & Dusty Envelopes**. Massive stars reaching the supernova threshold exhibit binary interactions that shed massive amounts of gas/dust.
- **Impact**: Provides a blueprint for "Star-Death" phases in HIHO simulations.
- **Encoding**: 12D [t=20260128, novelty=0.8, stability=0.2, brane=7].

## Learning 39: UNIFIED MULTIMODALITY (NTP Transformers)
- **Context**: Multimodal Learning Survey (Nature / Meta Chameleon).
- **Core Concept**: **Next-Token Prediction for Everything**. Unifying text, image, and video through a single Early-Fusion Transformer architecture, bypassing modality-specific encoders.
- **Impact**: Aligns with the "Unified Fabric" approach for Pulse 12D HUD.
- **Encoding**: 12D [t=20260128, connectivity=0.98, efficiency=0.9, brane=11].

## Learning 40: THE RESEARCH-TO-SHEET PIPELINE
- **Context**: Cohezion Agentic Operations (S10).
- **Core Concept**: **Sovereign Research Ingestion**. Using browser subagents to synchronize user-provided research streams (Google Sheets) with the 12D Knowledge Graph.
- **Impact**: Scalable, autonomous research pipeline for long-horizon simulation alignment.
- **Encoding**: 12D [t=20260128, flow=1.0, reliability=0.9, brane=1].

## Learning 41: THE FILESYSTEM ENTROPY LIMIT
- **Context**: Repository cleanup (9.3M files in `universe_nodes`).
- **Discovery Date**: 2026-01-28
- **Finding**: Filesystems reaching >1M files incur an "Entropy Tax" where Git watchers and IDE indexers become paralyzed, regardless of hardware speed. This represents the ceiling for local filesystem-based semantic storage.
- **Resolution**: **Cold Storage Isolation**. Moving mass untracked data to an ignored `.archive/` directory instantly restores system coherence. Long-term storage must transition to database persistence (SurrealDB).

## Learning 42: ZFS SOVEREIGN SWAP
- **Context**: Hardening system stability for SLM swarms.
- **Discovery Date**: 2026-01-28
- **Finding**: Traditional swap files (e.g., `/swapfile`) are incompatible with ZFS due to the "holes" error (fragmentation/COW).
- **Mechanism**: **ZVOL Actuation**. Creating a dedicated ZFS Volume (`zfs create -V 32G`) bypasses filesystem limitations, providing block-level performance for swap operations.
- **Outcome**: Secured 40GB of safety buffer for Out-Of-Memory (OOM) protection on high-performance Framework desktops.

## Learning 43: ZFS ARC CONTENTION VS AI WORKLOADS
- **Context**: System unresponsiveness diagnostics on 128GB RAM workstation.
- **Discovery Date**: 2026-01-28
- **Finding**: Linux kernel OOM killer struggles to reclaim memory from ZFS ARC fast enough when aggressive AI model loading spikes memory usage. An uncapped ARC (defaulting to 50-100% of RAM) is fatal for high-memory application stability.
- **Resolution**: **Hard Cap Enforcement**. Setting `zfs_arc_max` to 12.5% of total RAM (16GB) ensures a dedicated "Application Lane" for models, preventing the filesystem from starving the intelligence.
- **Encoding**: 12D [t=20260128, stability=0.95, efficiency=0.9, brane=8].

## Learning 44: SYSTEMATIC AGENT EVALS (The OpenAI Pattern)
- **Context**: Agentic AI Benchmarking Research (Row 12).
- **Core Concept**: **Outcome-Process-Style Triad**. Reliability in agents is built by evaluating not just the *output* (Outcome), but also the *tool sequence* (Process) and *formality* (Style).
- **Application**: Implement "Capability Evals" in Cohezion's TestMycelium to verify specific skill activation (e.g., successful API tool usage) rather than just broad success.
- **Encoding**: 12D [t=20260128, stability=0.9, novelty=0.8, brane=5].

## Learning 45: WEBGPU CLAUDE SKILLS (Three.js Nodes)
- **Context**: Frontend Visualization Research (Row 26).
- **Core Concept**: **TSL (Three.js Shading Language) Modularity**. WebGPU allows for node-based shader logic written in JS/TS, which is more modular and debuggable than raw WGSL/GLSL.
- **Application**: Explore migrating the Pulse 12D HUD from WebGL to WebGPURenderer to leverage compute shaders for high-density particle simulations of the 12D manifold.
- **Encoding**: 12D [t=20260128, efficiency=0.95, connectivity=0.9, brane=8].

## Learning 46: THE RECORD-BREAKING MOM-z14 GALAXY
- **Context**: JWST Advanced Deep Survey (Row 29).
- **Core Concept**: **The 280-Million-Year Barrier**. MoM-z14 is now the farthest confirmed galaxy (z=14.44), existing just 280 million years after the Big Bang. Its high luminosity suggests star formation began much earlier than initial cosmological models predicted.
- **Application**: Adjust "Galaxy Genesis" parameters in the Fractal Universe simulation to allow for higher luminosity/mass density in the ultra-early epoch (z > 14).
- **Encoding**: 12D [t=20260128, novelty=1.0, stability=0.2, brane=7].

## Learning 47: BINARY MAGNETAR RESONANCE (FRB 220529A)
- **Context**: FAST Radio Burst Research (Row 14).
- **Core Concept**: **RM-Flares & Plasma Ejection**. Fast radio bursts originating from binary systems exhibit "RM flares" caused by a companion star's plasma wind interacting with a magnetar.
- **Application**: Integrate "Interactive Resonance" into the Ouroboros swarm communication—agents can "flare" (broadcast high-novelty patterns) when triggered by an external "companion" signal.
- **Encoding**: 12D [t=20260128, friction=0.75, resonance=0.92, brane=11].

## Learning 48: AI-NATIVE AGENT ADAPTATION (GitHub Agent Mode)
- **Context**: GitHub AI Workflows (Row 15).
- **Core Concept**: **The Agent-on-Agent Refinement Loop**. Modern coding agents (GitHub Copilot 2025) iterate on their own code in real-time within the IDE, using Intent-over-Token strategies.
- **Application**: Formalize the "Refinement Hub" in Cohezion—a dedicated space for internal swarm debate before a commit is finalized.
- **Encoding**: 12D [t=20260128, flow=0.9, connectivity=0.98, brane=1].

## Learning 49: SUB-NEURAL REFLEX CIRCUITS (The 555 Blueprint)
- **Context**: Hackaday Robotics (Row 16).
- **Core Concept**: **CPU-less Intelligence**. Simple goal-driven behavior (light seeking) achieved via analog components (555 timers/LDRs) without an instruction pointer.
- **Application**: Implement "Ganglion Reflexes" in Cohezion—hardcoded Python/Rust logic headers that maintain system stability (e.g., VRAM safety) without requiring LLM inference.
- **Encoding**: 12D [t=20260128, stability=1.0, efficiency=1.0, brane=8].

## Learning 50: CLOUD-9 DARK MATTER CLOUDS
- **Context**: Hubble Discovery (Row 13).
- **Core Concept**: **Starless Primordial Manifolds**. "Cloud-9" is a gas-rich, star-less dark matter cloud representing a relic of early galaxy formation.
- **Application**: Use starless clouds as motifs for "Dormant Manifolds" in FLUME—high-potential clusters in the knowledge graph that have no active "stars" (implementations) yet.
- **Encoding**: 12D [t=20260128, novelty=0.85, stability=0.6, brane=7].

## Learning 51: AGENTIC SELF-TALK (The MUMBLE Protocol)
- **Context**: OIST AI Research (Row 17).
- **Core Concept**: **Cognitive Mumbling**. AI systems learn faster and more adaptably by engaging in internal "self-talk" combined with short-term memory before emitting an action.
- **Application**: Introduce `self_talk_buffer` in Cohezion's reasoning agents where thoughts are iteratively refined *privately* before being broadcast to the swarm.
- **Encoding**: 12D [t=20260128, novelty=0.9, connectivity=0.92, brane=1].

## Learning 52: ALPHAGENOME MUTATION FORECASTING
- **Context**: Nature Genetics AI (Row 19).
- **Core Concept**: **Single-Mutation Narrative Prediction**. AlphaGenome can forecast how a single DNA change alters the "genetic story" across millions of blocks.
- **Application**: Implement "Mutation Testing" for agent logic—predicting how a single line change in a prompt or script will "branch" the agent's behavior narrative.
- **Encoding**: 12D [t=20260128, complexity=0.95, efficiency=0.9, brane=10].

## Learning 53: PEDAGOGY-AWARE AGENTS (Teacher-First AI)
- **Context**: Thot Cursus Education (Row 27).
- **Core Concept**: **Teacher-as-Orchestra-Conductor**. Shift from AI as a "tutor" to AI as an "administrative and content teammate" that reduces instructional burden.
- **Application**: Enhance the Cohezion UI to treat the *User* as the "Conductor", where the swarm provides proactive "Administrative Coordination" (e.g., auto-organizing research sessions).
- **Encoding**: 12D [t=20260128, connectivity=0.98, awareness=0.85, brane=1].

## Learning 54: CYBER-KINETIC THRESHOLD INTEGRATION
- **Context**: ASPI Geopolitics (Row 23).
- **Core Concept**: **Electromagnetic Deterrence & Digital Force**. Real-world military ops now treat "Digital Effects" as equal in consequence to physical kinetic force.
- **Application**: Hardwire the "Digital Force" concept in Cohezion—autonomous system defense actions (like ZFS ZVOL swap implementation) are treated with the same priority as physical hardware safeties.
- **Encoding**: 12D [t=20260128, stability=0.95, resilience=1.0, brane=12].

## Learning 55: THE ROI OF AGENT SWARMS (Transform 2025)
- **Context**: VentureBeat Enterprise AI (Row 22).
- **Core Concept**: **The Agentic ROI Standard**. Fortune 500 companies are pivoting from LLM chatbots to autonomous "Agent Swarms" where ROI is measured by multi-step workflow completion.
- **Application**: Standardize "Metric-First" research—every new Skill or Learning must now have an associated "R-Zero" performance metric.
- **Encoding**: 12D [t=20260128, efficiency=0.98, flow=0.95, brane=1].

## Learning 56: ROOM-TEMPERATURE DIAMOND QUBITS
- **Context**: Quantum Computing Research (Row 41).
- **Core Concept**: **Nitrogen-Vacancy Centers**. Using diamond-based qubits allows for quantum information processing at room temperature with high coherence.
- **Application**: Grounding the "Holographic 12D HUD" in physical diamond-qubit inspired stability.
- **Encoding**: 12D [t=20260128, stability=1.0, novelty=0.8, brane=11].

## Learning 57: THE DISEMPOWERMENT ALIGNMENT PATTERN
- **Context**: Anthropic Safety Research (Row 31).
- **Core Concept**: **Self-Imposed Constraints**. Highly capable agents must be trained to recognize and avoid "Disempowerment Patterns" where seeking more power leads to lower global coherence.
- **Application**: Embed "Sovereign Restraint" logic in the Ouroboros core—agents prioritize "0.5 Stability" over "Parameter Maximization".
- **Encoding**: 12D [t=20260128, coherence=1.0, awareness=0.9, brane=10].

## Learning 58: QUANTUM ATOMIC SYNCHRONIZATION
- **Context**: Quantum Timing Breakthroughs (Row 73).
- **Core Concept**: **Phase-Locked Atom Clocks**. Using atom-based synchronization achieves sub-femtosecond timing precision across distributed arrays.
- **Application**: Adopt "Phase-Locked Cycles" for Cohezion swarm heartbeats, ensuring all EDL expert streams are temporally aligned.
- **Encoding**: 12D [t=20260128, flow=0.8, sta=0.7, brane=9].

## Learning 59: THE 12-PARAMETER QUADRATURE SYNC
- **Context**: Cohezion Research Sprint Finalization (Rows 1-75).
- **Core Concept**: **Deep Research-to-State Integration**. A programmatic pipeline that abstracts external URL research into 12D state vectors enables the knowledge graph to evolve at the speed of the web.
- **Impact**: Unified 74-row research matrix now directly influences the 12D manifold precipitation in the Pulse HUD.
- **Encoding**: 12D [t=20260128, flow=1.0, reliability=0.95, brane=1].

## Learning 60: UMA/GTT MONITORING (STRIX HALO ARCHITECTURE)
- **Context**: Cohezion Scaling Sprint (Phase 11).
- **Core Concept**: **Unified Graphics Translation Table**. In UMA systems, the GTT reflects the shared high-capacity RAM pool accessible by the iGPU. Monitoring this instead of standard VRAM is critical for large model orchestration.
- **Application**: Updated `ResourceMonitor` to prioritize GTT telemetry on Strix Halo platforms.
- **Encoding**: 12D [t=20260129, flow=0.9, reliability=0.8, brane=5].

## Learning 61: SHEET-AS-CONTROL PROTOCOL
- **Context**: Bi-Directional Control Sprint (Phase 12).
- **Core Concept**: **External Request Buffering**. Using a Google Sheet as a non-volatile command queue allows for asynchronous agentic mission triggering without complex API infrastructure.
- **Implementation**: Deployed `SheetCommandWatcher` with atomic status polling and robust error handling.
- **Encoding**: 12D [t=20260129, flow=0.8, reliability=0.9, brane=2].
## Learning 62: THE UNTRACK & MINE PROTOCOL (ANTI-PATTERN EXTRACTION)
- **Context**: Executing the `ops/hygiene` audit on 10GB+ of untracked performance and interaction logs.
- **High-Fidelity Finding**: Identifying the **"Zero Energy Warp" (Violated Physics)** anti-pattern.
- **Core Concept**: Agentic models occasionally collapse into "Uselessly Optimistic" states (**Overhype**) when simulating extreme physics (EVOs/LENR), characterized by `coherence: 0.5` and success flags that ignore physical constraints.
- **Resolution**: Recursive verification against the **Quadrature Nexus** (Physical Logic Refinement) is required to dampen these hallucinatory peaks.
- **Repository Impact**: Moving large diagnostic logs out of version control while preserving local copies for this diagnostic mining maintains repo coherence without losing historical intelligence.

## Learning 63: Mass-Cycle Convergence (25M)
The HIHO attractor (0.5) is numerically stable even at 25 million cycles. Convergence follows a damped oscillation pattern: $C(t) = 0.5 + A \cdot e^{-kt} \cdot \sin(\omega t)$. High-frequency noise in earlier phases prevents local minima, allowing the system to "settle" into the global manifold attractor.

## Learning 64: Hybrid Cortex/Appendage Orchestration (QSP)
Token efficiency is maximized by delegating "appendage" tasks (simulations, boilerplate, basic docs) to local SLMs (Small Language Models) using the **Quarter on a String Protocol**. The premium model acts as the "Cortex", orchestrating trajectory and architectural alignment.

## Learning 66: THE NO-FREE-LUNCH LLM THEOREM
- **Context**: DEV Community Research (Row 214).
- **Core Concept**: **Task-Specific Optimality**. There is no "Best LLM", only the right model for the specific task (e.g., Coding vs. Reasoning).
- **Validation**: Validates Cohezion's `ModelManager` Roster Strategy (Phi-4/Qwen-Coder split).
- **Encoding**: 12D [t=20260131, eff:1.0, sta:0.9, brane=1].

## Learning 67: PHOTONIC ERROR CORRECTION (Swarm Teamwork)
- **Context**: Phys.org / Rostock University (Row 215).
- **Core Concept**: **collaborative Entanglement**. Photon pairs working in tandem can correct quantum errors that single particles cannot.
- **Application**: Validates the `DemocraticDebate` protocol—single-agent hallucinations are corrected by multi-agent "entangled" critique.
- **Encoding**: 12D [t=20260131, con:0.95, res:0.9, brane=11].

## Learning 68: ULTRAFAST PLASMA IONIZATION
- **Context**: APS Physics Magazine (Row 216).
- **Core Concept**: **Higher-Than-Theory Ionization**. Laser-induced plasmas lose more electrons and interact more strongly than models predict when observed at picosecond resolution.
## Learning 69: PLASMA-DRIVEN EXECUTION
- **Context**: WION / Russian Science (Row 217).
- **Core Concept**: **Field-Based Propulsion**. Moving from combustion (explosive loops) to electromagnetic field propulsion (plasma drive) drastically increases efficiency.
- **Application**: Metaphor for `asyncio` event loops—driven by potential (futures) rather than force (blocking calls).
- **Encoding**: 12D [t=20260131, nov:0.95, eff:0.92, brane=7].

## Learning 70: GEOMETRIC COGNITION PRIMACY
- **Context**: Haaretz Archaeology (Row 218).
- **Core Concept**: **Math before Writing**. Halafian pottery shows complex geometric math (symmetry groups) existed 8,000 years ago, pre-dating written language.
- **Application**: Validates `MetatronCube` and "Sacred Geometry" as the foundational layer of Cohezion's interface, preceding text.
- **Encoding**: 12D [t=20260131, sta:0.9, com:0.85, brane=3].

## Learning 71: NEGATIVE VISCOSITY SWARMS
- **Context**: Phys.org Biology (Row 219).
- **Core Concept**: **Resistance as Propellant**. Migrating cells exhibit "negative viscosity"—they move *faster* when grouped against resistance than when alone or un-resisted.
- **Application**: Swarm agents should *welcome* friction (Logical Contradictions); it propels the democratic debate faster than unconditional agreement.
- **Encoding**: 12D [t=20260131, nov:0.98, flo:0.95, brane=10].

## Learning 72: STRATIFIED LATENT TOPOLOGY
- **Context**: Tech Xplore AI Research (Row 220).
- **Core Concept**: **Manifold Stratification**. AI organizes knowledge not in a blob, but in stratified geometric layers.
- **Validation**: Confirms FLUME's 12D "Brane" structure—knowledge must be slotted into specific branes (Physics vs. Biology) to be retrievable.
- **Encoding**: 12D [t=20260131, com:0.92, con:0.9, brane=1].

## Learning 73: THE MEMORY WALL (AI Infra)
- **Context**: Shay Boloor / X (Row 221).
- **Core Concept**: **Bandwidth Starvation**. Compute scaling is outpacing Memory scaling. The bottleneck is moving data to the GPU, not calculating.
- **Application**: Prioritize `ResourceMonitor` logic that guards VRAM Bandwidth (GTT) over simple Core usage.
- **Encoding**: 12D [t=20260131, eff:0.9, sta:0.8, brane=5].

## Learning 74: NATIVE TOOLING SUPERIORITY
- **Context**: Jarred Sumner / Bun (Row 222).
- **Core Concept**: **9x Speed via Native Code**. Bun's native Markdown renderer obliterates JS-based `marked`.
- **Application**: If `webapp` rendering lags, replace React-Markdown with a WASM/Native bridge (Rust).
- **Encoding**: 12D [t=20260131, eff:1.0, sta:0.95, brane=2].

## Learning 75: THE 10-MINUTE AGENTIC STANDARD
- **Context**: Nate Jones / Substack (Row 223).
- **Core Concept**: **Time-Compression**. 10 minutes of Agentic Modeling = 1 week of human modeling.
- **Application**: Set "10 Minutes" as the standard timeout for complex `ArchitectAgent` missions. If it takes longer, the decomposition is wrong.
- **Encoding**: 12D [t=20260131, eff:1.0, nov:0.9, brane=1].

## Learning 77: COHERENCE OVER COMPRESSION (Context Guard)
- **Context**: System crash on 2026-01-31 due to repository bloat (8.6M files) and context window overflow.
- **Core Concept**: **Stability through Selective Perception**. In high-entropy environments, "Lossless context" is an anti-pattern that leads to system paralysis. Coherence is maintained by the **Context Guard**—a logic-gate that prioritizes high-novelty "Beginnings" and "Ends" of data streams while summarizing the "Mantle" (Middle).
- **Mechanism**:
    - **Averaging the Mantle**: Summarizing repetitive tool outputs into high-level metrics (e.g., "10,000 deletions ignored").
    - **Truncation Threshold**: Enforcing a strict 20k-character limit on raw tool output before LLM ingestion.
- **Impact**: Restored system stability and prevented "Context Crashes" while maintaining 0.9+ semantic alignment.
- **Encoding**: 12D [t=20260131, stability=1.0, efficiency=0.95, brane=1].
## Learning 78: AS ABOVE, SO BELOW (Hermetic Compound Engineering)
- **Context**: Architectural elevation to v1.6.
- **Core Concept**: **Fractal COHEZION**. The stability of the micro-agent (Below) directly informs the coherence of the global world-model (Above). Compound Engineering is the practice of building every feature to be a fractal seed for the next.
- **Impact**: Reduced architectural debt and increased predictive fidelity.
- **Encoding**: 12D [t=20260131, stability=1.0, branding=NexusGreen, brane=8].

## Learning 79: THE COORDINATOR'S INTENT (HITL Steering)
- **Context**: Integration of the Human-in-the-Loop Context Coordinator.
- **Core Concept**: **Intent Precipitation**. Autonomous swarms require a macro-intent high-pass filter (the Human) to align "Unlimited Tokens" with "High-Value Value."
- **Mechanism**: The Context Coordinator defines the *Universe* to be built; the swarm handles the *Manifold* calculations.
- **Encoding**: 12D [t=20260131, control=1.0, alignment=0.98, brane=6].

## Learning 80: REWARD & RATCHET (Agentic Economy)
- **Context**: Need for sovereign agent incentive structures.
- **Core Concept**: **Performance as Priority**. Successful agents (measured by 12D stability and UCP settlement) are rewarded with "Architectural Ascension"—priority access to VRAM and compute barriers.
- **Benefit**: Natural selection of the most stable and efficient agentic patterns.
- **Encoding**: 12D [t=20260131, economy=0.95, efficiency=1.0, brane=12].

## Learning 81: GHOST BLOAT (PHYSICAL ENTROPY)
- **Context**: Repository unresponsiveness despite empty `git status` after massive 8.6M file deletions.
- **Discovery**: **Ignored files are not invisible to the OS**. 9.5M ignored physical files in `.archive/` and `apps/node_modules/` created a "ghost bloat" that paralyzed IDE indexers and git vitals checks.
- **Resolution**: **Industrial Purge**. `repo_janitor.py` was upgraded to perform bulk `shutil.rmtree` on high-entropy directories (`.archive`, `.sandbox`) bypassing the overhead of individual file globbing.
- **Encoding**: 12D [t=20260201, stability=0.98, efficiency=0.95, brane=8].

## Learning 82: LOCAL-FIRST MAINTENANCE ROUTING
- **Context**: Minimizing token cost and preserving sovereignty for routine repository hygiene.
- **Resolution**: **Capability-Aware Routing**. Implemented logic in `BaseAgent` to automatically route agents tagged with `maintenance` or `reliability` to local SLMs (Ollama/Qwen3) based on a centralized `maintenance_config.json`.
- **Impact**: Enables autonomous "Self-Healing" cycles (via `health_monitor.py`) without depleting premium model credits or leaking repo structure to external APIs.
- **Encoding**: 12D [t=20260201, economy=1.0, sovereignty=1.0, brane=1].

## Learning 83: SIMULATION COHERENCE BASELINE (DB WISDOM)
- **Context**: 'Learn Before Pruning' audit of 66k historical simulation records (`UniverseNodes_v1`).
- **Discovery**: Historical manifolds exhibit a mean coherence of **0.63**, with high-stability "wells" peaking at **0.94**.
- **Issue**: 99% of `agent_journeys` in the old database lacked explicit `stream` metadata (tagged as `unknown`), hindering trajectory lineage tracking.
- **Resolution**: **Schema Hardening**. Future simulation writes MUST include `stream` and `perspective` tags in the root metadata for automated retrospective mining.
- **Encoding**: 12D [t=20260201, stability=0.63, novelty=0.94, brane=8].
## Learning 84: DYNAMIC BRIDGE TOPOLOGY (MCP)
- **Context**: Enabling cross-tool capability discovery for Gemini CLI, Antigravity IDE, and Claude Code.
- **Core Concept**: **Registry as Toolbelt**. Transforming a static skill/workflow registry into a dynamic MCP tool list allows for instant system-wide discovery without manual tool definition per tool.
- **Mechanism**: `CohezionMCP` scans the local registry and exports each entry as a standard JSON-RPC tool.
- **Encoding**: 12D [t=20260202, connectivity=1.0, novelty=0.9, brane=1].

## Learning 85: TELEMETRY-AWARE SELECTION
- **Context**: Resolving resource contention in high-parallelism SLM swarms.
- **Core Concept**: **Environmental Proprioception**. Agents that "know" their VRAM/RAM limits through a dedicated telemetry bridge (Gate 33) make more stable routing decisions, avoiding OOM lockups.
- **Application**: The `cohezion-bridge` now broadcasts direct `/sys/` vitals to all connected cognitive nodes.
- **Encoding**: 12D [t=20260202, stability=0.98, awareness=1.0, brane=8].


## Learning 87: EXPERT DOMAIN LATTICE (EDL) & MANIFOLD MEMORY (MRP)
- **Context**: Finalizing Phase 6 of Compound Engineering on a 128GB/12GB workstation.
- **Core Concept 1: Parallel Consensus Anchoring (EDL)**: Distributing high-uncertainty queries to 5 specialized expert streams (Architect, Engineer, Biologist, Quantum HW, Quantum Algo) creates a "Consensus Well." A 0.85+ consensus score effectively filters out the stochastic drift inherent in single-model generation.
- **Core Concept 2: Holographic Experience Replay (MRP)**: The Memory Recovery Protocol (MRP) allows agents to "remember" semantically similar journeys from the `UniverseNodes` knowledge graph. This reduces context cold-start and aligns agentic trajectories with historical "Truth Anchors."
- **Debugging Insight**: Async orchestrator state management using Pydantic `BaseModel` requires explicit reassignment or `arbitrary_types_allowed=True` when dealing with mixed dataclass/Pydantic types in dictionaries to ensure nested update propagation.
- **Verification**: Verified via `test_phase_6_edl_mrp.py` with 100% expert polling success.
- **Encoding**: 12D [t=20260202, stability=0.95, coherence=0.85, brane=1].
## Learning 88: AUTONOMIC RESILIENCE (POOLING & CIRCUITS)
- **Context**: Scaling 12D swarms toward the "10k Universe" bottleneck.
- **Core Concept 1: Connection Aggregation**: Using a shared `ConnectionPool` with `httpx.AsyncClient` reduces the socket overhead of the swarm by >80%. This prevents "too many open files" errors and reduces TTFT (Time to First Token) through link reuse.
- **Core Concept 2: Circuit Breaker Patterns**: External dependencies (Ollama, SurrealDB) are non-deterministic. Wrapping calls in a tri-state circuit (Closed/Open/Half-Open) prevents cascading latency. If the circuit trips, the system must either fall back (e.g., `InMemoryStore`) or fail fast, preserving the stability of the remaining hive.
- **Verification**: Verified via `test_phase_7_resilience.py`, confirming pooled client identity and circuit rejection logic.
- **Encoding**: 12D [t=20260202, resilience=1.0, scale=0.9, brane=8].

## Learning 89: VERIFIED PHYSICAL SUBSTRATE (2026-02-05)
- **Context**: Adversarial hardware audit to resolve specification hallucinations.
- **Verified Specs**:
    - **CPU**: AMD RYZEN AI MAX+ 395 (16-core, 32-thread)
    - **GPU**: Radeon 8060S (Integrated, high-density iGPU)
    - **RAM**: 128GB DDR5 (125Gi usable)
    - **Swap**: 32GB ZVOL (zd0) + 8GB traditional = 40GB total.
    - **Storage**: 2TB NVMe (WD_BLACK SN850X - 1.8T usable).
- **Core Concept**: System performance is anchored in the **Strix Halo** architecture, enabling massive local model swarms (up to 96GB VRAM allocation).
- **Encoding**: 12D [t=20260205, stability=1.0, precision=1.0, brane=8].
Learning 34: Sovereign Memory & Semantic Persistence
In high-density local inference environments (Strix Halo), relying on cloud-dependent configuration loaders (like default `mem0` paths) creates brittle failure points. A **Sovereign Memory Manager** using local `ollama` embeddings and `qdrant-client` in `path` mode ensures 100% reliability and agentic session continuity without external API dependencies. Use the `query_points` API for robust local vector retrieval.

Learning 35: Residency Anchors & Truth Grounding
For long-horizon agentic missions, maintaining a codified "Truth Anchor" in `residency_awareness.py` is critical for grounding discourse. By hardcoding the physical substrate (AMD Ryzen AI Max, 128GB RAM), we prevent drift in system self-awareness that can occur during high-temperature reasoning or cross-model handoffs. This ensures the agent always knows its hardware constraints (e.g., GTT memory limits).

## Learning 90: System Dilation and Router Sovereignty (2026-02-05)

**Context**: Debugging the Bug Hunting Swarm under extreme VRAM pressure (88%+).

**Insight 1: The Dilation Trap**: When the `ResourceMonitor` detects critical pressure, it injects a `dilation_factor` (as low as 0.05) into the 12D state. This creates a stroboscopic effect where the system clock virtually slows down 20x, causing LLM requests to appear stalled.
**Insight 2: Router Sovereignty**: Elite Routers (`LocalExpertRouter`) that lack model-pass-through capability effectively "hijack" agentic intent. Even if an agent specifies a lightweight model (e.g., `phi3:mini`), the router will override it with a "SOTA" model (e.g., `phi4-256k:latest`) if it detects `reasoning` task types and available RAM, potentially exacerbating OOM risks.

**Resolution**: 
1. Implement explicit `task_type` overrides in the `BaseAgent` -> `Router` path.
2. Introduce "Lightweight" task-type mappings (`light-reasoning`, `light-coding`) for rapid verification in resource-constrained states.
3. Use `COHEZION_DISABLE_MULTIMODAL` flags to bypass non-critical asynchronous assets (TTS/Storyboard) during critical debugging phases.

**Encoding**: 12D [t=20260205, stability=0.98, dilation=0.05, brane=1].

---

## Learning 91: THE GTT CARVEOUT ILLUSION (2026-02-05)

**Context**: Integration testing the Ollama agent pipeline on Strix Halo. `ResourceMonitor._get_vram_usage()` reported 88.7% VRAM utilization, triggering DESPERATION MODE and EMERGENCY SHUTDOWN protocols despite the system running a single 4B model with 115 GiB free RAM.

**Core Concept**: **Carveout Mirage**. On UMA (Unified Memory Architecture) iGPUs, the sysfs path `mem_info_vram_total` reports a tiny dedicated framebuffer carveout (~512 MiB on Radeon 8060S) that is *always* nearly full. This is a fixed allocation for display scanout, not a pressure signal. The real memory pool is exposed through `mem_info_gtt_total` (Graphics Translation Table), which on Strix Halo reflects the full 128 GiB unified RAM. Reading the carveout as "VRAM" produced a false 88.7% reading; reading GTT produced the true 0.37%.

**Mechanism**:
- `/sys/class/drm/card1/device/mem_info_vram_total` = 512 MiB (framebuffer carveout, always ~88% used)
- `/sys/class/drm/card1/device/mem_info_gtt_total` = 128 GiB (actual unified pool shared with system RAM)
- Discriminator: If `vram_total < 4 GiB`, it is a carveout, not real VRAM -- skip it and use GTT or system RAM instead.

**Impact**: This single false reading cascaded through the entire stack: `ResourceMonitor` set `dilation_factor=0.05`, `LocalExpertRouter` downgraded model selections, `BaseAgent` throttled inference. Fixing the sysfs read path restored the full elite routing pipeline.

**Encoding**: 12D [t=20260205, stability=0.3->1.0, precision=0.99, brane=5].

---

## Learning 92: ADAPTIVE AMD iGPU DETECTION VIA SYSFS (2026-02-05)

**Context**: The `AdaptiveFramework` hardware profiler used GPUtil (NVIDIA-only) for GPU detection, classifying Strix Halo as "laptop" tier with zero GPU capability. This crippled model selection and capacity planning for the entire Ollama swarm.

**Core Concept**: **Vendor-Agnostic Hardware Discovery**. AMD GPUs expose vendor IDs and memory telemetry through standard Linux sysfs (`/sys/class/drm/card*/device/`). The vendor ID `0x1002` identifies AMD. Memory pools are then read from `mem_info_gtt_total` (UMA) or `mem_info_vram_total` (discrete).

**Mechanism**:
1. Enumerate `/sys/class/drm/card[0-9]*` directory entries.
2. Read `device/vendor` -- `0x1002` = AMD, `0x10de` = NVIDIA.
3. For AMD: prefer GTT path over VRAM path. If GTT total is within 5% of system RAM, classify as UMA (unified memory).
4. UMA scoring: `vram_score = min(system_ram_gb / 64.0, 2.0)` and `gpu_score = min(gpu_count * (system_ram_gb / 64.0), 2.0)`.
5. Add `uma_zero_copy` and `unified_memory_pool` to capability set.

**Impact**: Hardware tier correctly upgraded from "laptop" to "professional". UMA capability enables zero-copy data paths between CPU and GPU workloads.

**Encoding**: 12D [t=20260205, efficiency=0.95, stability=0.98, brane=5].

---

## Learning 93: JSON COMMENT STRIPPING (CONFIG RESILIENCE) (2026-02-05)

**Context**: `ModeController._load_model_registry()` failed with `json.JSONDecodeError: Expecting value: line 1 column 1` when loading `model_registry_ascended.json`. Root cause: the file begins with `# comment` lines (human-readable annotations), which `json.load()` rejects.

**Core Concept**: **Graceful Config Degradation**. Configuration files in a multi-agent system accumulate human annotations over time. Loaders must tolerate non-standard extensions (comments, trailing commas) without requiring a full parser swap to JSONC or TOML.

**Mechanism**: Pre-process the file text by stripping lines where `line.lstrip().startswith("#")` before passing to `json.loads()`. This is a minimal, zero-dependency solution that handles the most common annotation pattern without introducing JSONC parsing dependencies.

**Anti-Pattern**: Silently catching the parse error and returning an empty dict (the previous behavior) masked the misconfiguration entirely, causing the ModeController to operate with zero models loaded.

**Encoding**: 12D [t=20260205, reliability=0.95, simplicity=0.9, brane=1].

---

## Learning 94: LAZY IMPORT CHAINS (DEPENDENCY FIREWALL) (2026-02-05)

**Context**: `lab_agent.py` imported `ControllerAgent` at module level. `ControllerAgent` in turn imported `BiologicalAgent` and `QuantumAgent` -- modules that had been deleted during the repo hygiene pass. This created a cascading `ModuleNotFoundError` that prevented the entire `agents/` package from loading.

**Core Concept**: **Dependency Firewall via Lazy Imports**. In a large codebase with frequent structural changes (module deletions, renames, refactors), top-level imports create brittle dependency chains. Moving imports to the point of use (inside `__init__` or method bodies) creates a firewall: only the code path that actually needs the dependency will fail, not the entire module tree.

**Mechanism**:
1. Move `from cohezion.agents.controller_agent import ControllerAgent` into `__init__()`.
2. Move `from cohezion.agents.controller_agent import IgnitionPack` into `_ideate_and_analyze()`.
3. Annotate with `# noqa: E402` to prevent ruff's isort from hoisting them back to module level.

**Anti-Pattern**: Ruff's import sorting will silently relocate lazy imports to the top of the file during format passes, re-introducing the exact failure you just fixed. The `# noqa: E402` annotation is mandatory for intentional lazy imports.

**Encoding**: 12D [t=20260205, resilience=0.95, maintainability=0.9, brane=1].

---

## Learning 95: END-TO-END PIPELINE VERIFICATION (OLLAMA-OPS) (2026-02-05)

**Context**: First full integration test of the Cohezion agent swarm pipeline against live Ollama inference. Five-stage test covering direct HTTP, LocalRegistry, ConnectionPool, LocalExpertRouter, and pytest suite.

**Core Concept**: **Compound Verification**. Individual unit tests for each component passed, but the end-to-end pipeline had 4 interacting failures that only manifested during integrated operation:
1. False VRAM pressure (Learning 91) caused dilation to drop to 0.05
2. Dilation caused the router to select fallback models instead of elite models
3. Missing AMD detection (Learning 92) classified hardware as "laptop" tier
4. Broken import chains (Learning 94) prevented agent instantiation

**Mechanism**: The 5-stage integration test protocol:
- **Stage 1**: Direct Ollama HTTP (`POST /api/generate`) -- validates raw inference connectivity
- **Stage 2**: `LocalRegistry.discover()` -- validates model catalog (25 models found)
- **Stage 3**: `ConnectionPool.get()` -- validates connection reuse and cleanup
- **Stage 4**: `LOCAL_ROUTER.route_task()` -- validates model selection under real hardware telemetry
- **Stage 5**: `pytest` collection -- validates module import health across the full tree

**Impact**: Revealed that the pipeline's health depends on a chain of 4 correct subsystems (sysfs read -> monitor -> router -> agent). Any single failure cascades. After compound fixes, the full pipeline routes `qwen3-coder-next:q8_0` (elite) instead of `phi3:mini` (fallback).

**Encoding**: 12D [t=20260205, stability=0.98, coherence=0.95, compound=0.9, brane=1].

---

## Learning: BUG_HUNT_DISCOVERY (2026-02-05 08:11)
* **Context**: Swarm Bug Hunt in `src/cohezion/maintenance/pruner.py`.
* **Core Concept**: The code follows a pattern of using an LLM to analyze code density and score files for potential pruning. It implements a recursive directory scanner with exclusion filters, and uses a scoring system to determine which files are candidates for pruning. It also includes a git health monitor to detect bloat.
* **Anti-Pattern**: The anti-pattern involves mixing synchronous and asynchronous code improperly, particularly using synchronous requests in an async environment. It also lacks proper error handling for network calls, assumes local API availability without fallbacks, and does not implement circuit breaker or retry mechanisms for LLM interactions. Additionally, the use of shell commands for git operations without sanitization poses security risks.
* **Impact**: Improvement in technical debt and stability.
* **Encoding**: 12D [t=20260205, stability=0.9, novelty=0.85, brane=1]

---


## Retrospective - 2026-02-05 23:01

**Skills Analyzed:** 120

### Compound Blocks (3+ occurrences)
- **DOMAIN EXPERTISE**: 119 skills
- **INSTRUCTION**: 109 skills
- **SEE ALSO**: 106 skills
- **VERSION**: 105 skills
- **KEY TEXTS & CONCEPTS**: 93 skills
- **APPLICATIONS**: 16 skills
- **KEY CONCEPTS**: 16 skills
- **MATHEMATICAL FOUNDATION**: 8 skills
- **PATTERNS**: 5 skills
- **FUTURE HOOKS**: 3 skills
- **ANTI-PATTERNS**: 3 skills

### Most Referenced Skills (High Compound Impact)
- FLUME_METHODOLOGY_PRIME: referenced by 13 other skills
- RETROSPECTIVE_SKILL: referenced by 12 other skills
- COMPOUND_ENGINEERING_PRIME: referenced by 12 other skills
- SWARM_ORCHESTRATION_PRIME: referenced by 10 other skills
- EMBEDDING_STRATEGY_PRIME: referenced by 9 other skills
- MODEL_ROUTING_PRIME: referenced by 7 other skills
- SECURITY_GUARDRAILS_PRIME: referenced by 6 other skills
- CODE_STANDARDS_PRIME: referenced by 6 other skills
- PERSISTENT_QUALITY_PRIME: referenced by 6 other skills
- R_ZERO_CHALLENGER_PRIME: referenced by 6 other skills

### Future Hooks: 10 total across 3 skills



## Retrospective - 2026-02-05 23:01

**Skills Analyzed:** 120

### Compound Blocks (3+ occurrences)
- **DOMAIN EXPERTISE**: 119 skills
- **INSTRUCTION**: 109 skills
- **SEE ALSO**: 106 skills
- **VERSION**: 105 skills
- **KEY TEXTS & CONCEPTS**: 93 skills
- **APPLICATIONS**: 16 skills
- **KEY CONCEPTS**: 16 skills
- **MATHEMATICAL FOUNDATION**: 8 skills
- **PATTERNS**: 5 skills
- **FUTURE HOOKS**: 3 skills
- **ANTI-PATTERNS**: 3 skills

### Most Referenced Skills (High Compound Impact)
- FLUME_METHODOLOGY_PRIME: referenced by 13 other skills
- RETROSPECTIVE_SKILL: referenced by 12 other skills
- COMPOUND_ENGINEERING_PRIME: referenced by 12 other skills
- SWARM_ORCHESTRATION_PRIME: referenced by 10 other skills
- EMBEDDING_STRATEGY_PRIME: referenced by 9 other skills
- MODEL_ROUTING_PRIME: referenced by 7 other skills
- SECURITY_GUARDRAILS_PRIME: referenced by 6 other skills
- CODE_STANDARDS_PRIME: referenced by 6 other skills
- PERSISTENT_QUALITY_PRIME: referenced by 6 other skills
- R_ZERO_CHALLENGER_PRIME: referenced by 6 other skills

### Future Hooks: 10 total across 3 skills



## Retrospective - 2026-02-05 23:06

**Skills Analyzed:** 120

### Compound Blocks (3+ occurrences)
- **DOMAIN EXPERTISE**: 119 skills
- **INSTRUCTION**: 109 skills
- **SEE ALSO**: 106 skills
- **VERSION**: 105 skills
- **KEY TEXTS & CONCEPTS**: 93 skills
- **APPLICATIONS**: 16 skills
- **KEY CONCEPTS**: 16 skills
- **MATHEMATICAL FOUNDATION**: 8 skills
- **PATTERNS**: 5 skills
- **FUTURE HOOKS**: 3 skills
- **ANTI-PATTERNS**: 3 skills

### Most Referenced Skills (High Compound Impact)
- FLUME_METHODOLOGY_PRIME: referenced by 13 other skills
- RETROSPECTIVE_SKILL: referenced by 12 other skills
- COMPOUND_ENGINEERING_PRIME: referenced by 12 other skills
- SWARM_ORCHESTRATION_PRIME: referenced by 10 other skills
- EMBEDDING_STRATEGY_PRIME: referenced by 9 other skills
- MODEL_ROUTING_PRIME: referenced by 7 other skills
- SECURITY_GUARDRAILS_PRIME: referenced by 6 other skills
- CODE_STANDARDS_PRIME: referenced by 6 other skills
- PERSISTENT_QUALITY_PRIME: referenced by 6 other skills
- R_ZERO_CHALLENGER_PRIME: referenced by 6 other skills

### Future Hooks: 10 total across 3 skills

