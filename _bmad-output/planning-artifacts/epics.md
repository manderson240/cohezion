---
stepsCompleted: ['step-01-validate-prerequisites', 'step-02-design-epics', 'step-03-create-stories-epic-1', 'step-03-create-stories_epic-2', 'step-03-create-stories_epic-3', 'step-03-create-stories_epic-4', 'step-03-create-stories_epic-5', 'traceability-audit-complete', 'readiness-remediation-2026-02-27', 'tdd-qa-standards-2026-02-27', 'step-03-create-stories-epic-7_semver']
inputDocuments: ['_bmad-output/planning-artifacts/prd.md', '_bmad-output/planning-artifacts/architecture.md', '_bmad-output/planning-artifacts/ux-design-specification.md']
---

# cohezion - Epic Breakdown (Bidirectional Architecture)

## Overview

This document provides the complete epic and story breakdown for cohezion, decomposing the requirements from the PRD, UX Design, and Architecture requirements into implementable stories.

## Requirements Inventory

### Functional Requirements

FR1: [12D State Tracking] The system shall record and persist agent thought trajectories as 12D coordinate arrays in SurrealDB at <10ms latency.
FR2: [512D Projection] The `FlumeEncoder` shall compress 512D semantic vectors into 12D axiomatic vectors for physics engine processing.
FR3: [VLIW Alignment] The Rust bridge (`flume_physics.rs`) shall execute latent instruction packets using barrier-locked, VLEN=8 SIMD alignment.
FR4: [Multilingual Audio Bridge] The system shall stream real-time audio representations of agent state using the Kyutai `mimi` codec and `moshi-v1` / `hibiki-v1` models.
FR5: [Vanguard Scouting] The Daily Vanguard Agent shall scrape ArXiv, HuggingFace, GitHub, Reddit, and Ollama to extract SLM fine-tuning scripts and SOTA abstractions, executing automated integration tests with strict attribution and license compliance.
FR6: [Metacognitive Auditing] The system shall require every agent to log a JSON payload explaining its 512D intent prior to executing a 12D physical state change.
FR7: [Autonomous Test Generation] The `ShadowScripter` agent shall autonomously generate and commit new test specifications in response to VAE fine-tuning events or Vanguard Scout discoveries.
FR8: [Semantic Memory Pruning] The system shall implement semantic decay and vector pruning for the 512D latent space, ensuring that low-relevance agentic experiences are archived to SurrealDB.
FR9: [Hallucination Truth Anchors] The system shall utilize hardware-native telemetry (Physical Truth Anchors) to ground 512D reasoning, triggering an automatic "Reality Check" if agentic output contradicts the physical substrate state.
FR10: [Token Optimization] The system shall employ a `CostAwareRouter` achieving a 96.25% MoE optimization, prioritizing local SLMs for 90% of tasks and routing only high-complexity synthesis to elite models.
FR11: [Compound Skill Extraction] The system shall perform a daily "Mycelium Audit" of the `MISSION_JOURNAL` and `KEY_LEARNINGS`, autonomously synthesizing and registering new reusable skills in the `src/cohezion/registry/`.
FR12: [Triune Navigation] The system shall implement three distinct cognitive modes: KNOWER (Observatory), THINKER (Vault), and DOER (Cockpit) with embodied transitions (400ms-800ms).
FR13: [Re-Entry Narrative] The system shall present a first-person "Re-Entry Narrative" on session arrival, orienting the user to recent compound growth and system state.
FR14: [HIHO-Reactive UI] The interface shall dynamically respond to the HIHO coherence value, shifting color (Biolume to Orbital) and particle density via a live CSS bridge.
FR15: [Anima Sigil] The system shall feature an edge-native multimodal voice (Gemma 3n) for real-time narration, orientation, and reflection.
FR16: [Provenance-First UX] Every live data point and vault result shall carry a hover-accessible `ProvenanceTag` tracing it to its physical or semantic source.
FR17: [Semantic Vault Search] The THINKER mode shall provide natural language semantic search across the Three Pillars (Decisions, Experiments, Patterns) with visible match reasoning.
FR18: [Loop Visualization] The DOER mode shall provide high-fidelity visualization of the compound cycle, including retrospection summaries and before/after skill diffs.
FR19: [Lifecycle Pre-Simulation] The system shall support "Pre-Precipitation Simulation" where agents model the 12D trajectory of a proposed implementation lifecycle to detect architectural collisions.
FR20: [Adversarial Grounding] The system shall perform periodic "Adversarial Reality Checks" by injecting external, non-agentic "Truth Anchors" to detect and pop "Coherence Bubbles."
FR22: [Persistent Homology Validation] The system shall use Persistent Homology to validate the topological persistence of semantic intent during 12D projection.
FR23: [Hardware-Isolated Trust] All cryptographic signing keys shall be stored in a hardware-isolated environment (TEE/Secure Enclave).
FR24: [Heterogeneous Sharding] The sharding protocol shall support heterogeneous local compute nodes (CPU/GPU/TPU).

### NonFunctional Requirements

NFR1: [Hardware Bounds] The system shall execute entirely within a local environment: AMD Ryzen AI MAX+, 128GB RAM, and a 32GB ZVOL swap buffer to prevent OOM.
NFR2: [Latency & Audio] Kyutai audio interactions shall maintain a full-duplex latency of <200ms.
NFR3: [Persistence Reliability] The `JourneyPersistenceManager` shall dual-write to SurrealDB and the local `.cache` with a 99.9% success rate under high CPU load.
NFR4: [Experiment Tracking] All AI model training and RL loops shall be tracked, logged, and hash-signed using the Kyutai `dora` and `flashy` frameworks.
NFR5: [Dynamic Temporal Dilation] The system shall implement autonomous **Temporal Dilation** (slowing agentic reasoning cycles) when local hardware pressure (VRAM/GTT) exceeds 90%.
NFR6: [Token-Frugal Execution] The system shall maintain a "Token-Frugal" operational state, ensuring that 90% of agentic cycles occur on local hardware.
NFR7: [Semantic Fidelity] The FLUME Autoencoder maintains a KL Divergence score of <0.05 when projecting 512D Latent States to the 12D Axiomatic Manifold.
NFR8: [Recursive Healing Rate] 100% of TDD failures in the "Gallery of Red" trigger an automatic VAE fine-tuning iteration (Ouroboros loop).
NFR9: [Hardware-Native Performance] The VLIW-accelerated physics engine achieves a sustained 424x speedup (vs. Python) on Anthropic's VLIW challenge.
NFR10: [Vanguard Alignment] The Daily Vanguard pipeline achieves a 1-1 "Constitutional Alignment Score" against Anthropic's published safety criteria.
NFR11: [Viewport Gate] The system shall enforce a minimum viewport of 1280px, optimizing for desktop-native research engineering workflows.
NFR12: [Transition Rituals] Mode transitions shall use specific timing (400ms-800ms) to create a ritualized cognitive shift between observation and action.
NFR13: [Archive Mode] The system shall switch to a functional "Archive Mode" if the backend disconnects, allowing historical vault and trajectory traversal.
NFR14: [Ironwood Scaling] The system shall scale to TPU v7 Superpods with 9.6 Tb/s interconnects.
NFR15: [Axion Orchestration] The orchestration layer shall be optimized for Arm Neoverse V2 (Axion VMs).

### FR Coverage Map (Bidirectional)

FR1: Epic 2 (Story 2.2, 2.5)
FR2: Epic 2 (Story 2.2, 2.5)
FR3: Epic 1 (Story 1.2, 1.4)
FR4: Epic 2 (Story 2.6)
FR5: Epic 4 (Story 4.1, 4.1b, 4.1c, 4.7)
FR6: Epic 3 (Story 3.3, 3.7)
FR7: Epic 5 (Story 5.2)
FR8: Epic 3 (Story 3.6)
FR9: Epic 1 (Story 1.1, 1.3)
FR10: Epic 1 (Story 1.1, 1.3)
FR11: Epic 4 (Story 4.6)
FR12: Epic 2 (Story 2.1)
FR13: Epic 2 (Story 2.3)
FR14: Epic 2 (Story 2.4)
FR15: Epic 4 (Story 4.4, 4.5)
FR16: Epic 3 (Story 3.5)
FR17: Epic 3 (Story 3.2)
FR18: Epic 5 (Story 5.3, 5.5)
FR19: Epic 5 (Story 5.8)
FR20: Epic 5 (Story 5.9)
FR22: Epic 1 (Story 1-0-6)
FR23: Epic 1 (Story 1-0-5)
FR24: Epic 1 (Story 1-0-8)

### NFR Coverage Map (Bidirectional)

NFR1: Epic 1 (Story 1.4, 1.6, 1.8)
NFR2: Epic 2 (Story 2.6)
NFR3: Epic 1 (Story 1.5), Epic 3 (Story 3.1, 3.6)
NFR4: Epic 5 (Story 5.1, 5.4)
NFR5: Epic 1 (Story 1.3, 1.8)
NFR6: Epic 1 (Story 1.1, 1.3)
NFR7: Epic 2 (Story 2.2, 2.7)
NFR8: Epic 3 (Story 3.4), Epic 5 (Story 5.1)
NFR9: Epic 1 (Story 1.2), Epic 2 (Story 2.2)
NFR10: Epic 4 (Story 4.1, 4.3)
NFR11: Epic 2 (Story 2.1)
NFR12: Epic 2 (Story 2.1)
NFR13: Epic 2 (Story 2.1)
NFR14: Epic 6 (Story 6.1, 6.2)
NFR15: Epic 6 (Story 6.1)
NFR-AUTO_VERSION_HEALTH: Epic 7 (Story 7.1, 7.2, 7.6)
NFR-COMPOUND_VERSION_REGISTRY: Epic 7 (Story 7.3)
NFR-OUROBOROS_VERSION_HEALING: Epic 7 (Story 7.5)
NFR-VERSION_TELEMETRY: Epic 7 (Story 7.4)

## Epic List

### Epic 1: Hardware-Accelerated 12D Simulation at 60fps
The Research Engineer can execute deterministic 12D simulations with hardware-native acceleration, achieving 60fps state synchronization and autonomous OOM prevention — establishing the substrate that every subsequent epic builds upon.
**FRs covered:** FR3, FR9, FR10
**Compounds into:** Epic 2 (Observatory reads 12D state via Substrate Loom), Epic 3 (Vault persists state via JourneyPersistenceManager), Epic 4 (Sandbox uses Memory-Mapped Barriers), Epic 5 (Ouroboros writes training pairs via SHM)

### Epic 2: The Multi-Sensory Observatory (KNOWER)
Real-time 12D/512D projection using SurrealDB Live Queries as the Master Clock. Features the Re-Entry Narrative, HIHO-Reactive UI, synchronized Neural Audio, Triune Consensus Visualization, and Persistent Homology Validation.
**FRs covered:** FR1, FR2, FR4, FR12, FR13, FR14
**Compounds into:** Epic 3 (Vault reuses Master Clock and HIHO CSS bridge), Epic 4 (Anima Sigil shares audio infrastructure), Epic 5 (Loop Visualization extends the Observatory canvas)

### Epic 3: The Sovereign Vault (THINKER)
Persistent intent recording and Semantic Vault Search across the Three Pillars (Decisions, Experiments, Patterns). Features Provenance-First UX tags, Freeze-Frame Reality Capture, and an asynchronous Vector Pruning & Compaction Engine.
**FRs covered:** FR6, FR8, FR16, FR17
**Compounds into:** Epic 4 (Vanguard stores discoveries in Vault; Anima queries Vault for grounded narration), Epic 5 (Ouroboros reads Freeze-Frames as training data; skill evolution is Vault-searchable)

### Epic 4: Vanguard Pipeline & The Anima (DOER)
Autonomous scouting and pattern integration within a Substrate Sandbox. Features the Anima Sigil (Gemma 3n voice) for narration and orientation, Behavioral Alignment Suites, and the Auto-Incinerator for safety.
**FRs covered:** FR5, FR11, FR15
**Compounds into:** Epic 5 (Vanguard discoveries trigger ShadowScripter test generation; new skills feed the Ouroboros refinement loop)

### Epic 5: Ouroboros Evolution & Loop Theater
Recursive self-healing with high-fidelity Loop Visualization (retrospection summaries + skill diffs). Implements Agentic Mitosis & Apoptosis to biologically balance workloads and Autonomous Skill Registration.
**FRs covered:** FR7, FR18
**Compounds into:** This is the apex compound loop — every cycle refines skills, generates tests, and stores learnings. The system literally becomes better at building itself after each iteration.

### Epic 6: [ASPIRATIONAL] Cloud Substrate Expansion (Ironwood)
*Note: This epic represents the post-hiring strategic horizon and is dependent on access to Google Cloud TPU v7 infrastructure.*

The system transcends local hardware limits by migrating the 2048D sharded latent space to a Google Cloud TPU v7 (Ironwood) Pod, enabling high-density, multi-agent cosmogenesis simulations at planetary scale.
**FRs covered:** FR21, FR24
**Compounds into:** This epic leverages all previous work on Soul-Body Decoupling (Story 1.9) and Distributed Pulse protocols. It provides the "Endgame" substrate for the project's long-term research mission.

### Epic 7: Automated Version Health & Compound Registry
Automated semver compliance, dependency security scanning, and version telemetry within the 12D manifold. Features the Compound Version Registry for full traceability and Ouroboros-style self-healing for version conflicts.
**NFRs covered:** NFR-AUTO_VERSION_HEALTH, NFR-COMPOUND_VERSION_REGISTRY, NFR-OUROBOROS_VERSION_HEALING, NFR-VERSION_TELEMETRY
**Compounds into:** Epic 1 (version health gates hardware deployments), Epic 3 (version registry is Vault-searchable), Epic 5 (version healing integrates with Ouroboros loop)

## Epic 1: Hardware-Accelerated 12D Simulation at 60fps

The Research Engineer can execute deterministic 12D simulations with hardware-native acceleration, achieving 60fps state synchronization and autonomous OOM prevention. This epic establishes the substrate that every subsequent epic compounds upon — the Loom, Governor, and Persistence Manager become shared infrastructure for Observatory, Vault, Vanguard, and Ouroboros.

**Compound Value:** Every component built here (Substrate Loom, Governor, SHM protocol, JourneyPersistenceManager) is reused by 4+ downstream epics. The 60fps SHM protocol becomes the real-time data bus for the Observatory. The Governor's Temporal Dilation becomes the system-wide OOM safety net. The Persistence Manager becomes the write layer for Vault, Ouroboros training pairs, and Vanguard artifacts.

### Story 1.1: Sovereign Workspace Convergence
As a Research Engineer,
I want to migrate the existing TDD-hardened `overload_coordinator.py` and `kv_cache_tracker.py` into the new `src/cohezion/` monorepo structure,
So that I have a clean, governed substrate that preserves our Phase 1 momentum.

**Traces:** [FR-9, FR-10, NFR-1, NFR-6]

... [TRUNCATED] ...

### Story 1-0-5: TEE Key Management (Hardware Trust)
As a Security Architect,
I want to implement hardware-isolated key storage using a Trusted Execution Environment (TEE),
So that intent-action signing keys are protected from host OS compromise.

**Traces:** [FR23]

**Acceptance Criteria:**

**Given** the Ryzen AI MAX+ platform with AMD Memory Guard or software TPM support
**When** the system generates or retrieves intent-action signing keys
**Then** the keys are stored in a hardware-isolated environment (TEE/Secure Enclave or software-emulated equivalent)
**And** the keys are never exposed in plaintext to userspace memory outside the TEE boundary.

**Given** the host OS is compromised (simulated via a test that attempts direct memory reads)
**When** an attacker attempts to extract signing keys from process memory
**Then** the keys remain inaccessible and the attempted access is logged as a security event.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1-0-6: Persistent Homology Implementation [DONE]
As a Research Engineer,
I want to use Persistent Homology to validate semantic intent projection,
So that I have a mathematical proof the 512D "Soul" shape survives the 12D "Body" bottleneck.

**Traces:** [FR22]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `TopologicalPersistence` class: Vietoris-Rips filtration, self-contained (no external TDA library), O(n^2 log n)
- Computes H0 (connected components/clusters) and H1 (loops/cycles) persistence diagrams
- `PersistenceDiagram.tsx`: SVG scatter plot showing birth vs death for H0 (green) and H1 (purple)
- Points sized by persistence, diagonal reference line (birth=death)
- Shows entropy, cluster count, loop count in header
- Backend: `_compute_topology()` builds point cloud from EVO coherence history, feeds to TopologicalPersistence
- Integrated into SynthesisReport via `TopologyData` Pydantic model
- 92 persistence pairs detected from 15 ticks of 8 EVOs in testing
- **Key files:** `src/cohezion/compound/topological_persistence.py`, `src/web/anima_dashboard/src/components/PersistenceDiagram.tsx`, `src/cohezion/api/services/universe.py`

**Development Protocol:**
- [x] TDD: Red→Green cycle for topology API endpoint (`tests/api/test_topology_overlay.py`)
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Execution verification: 92 persistence pairs, entropy computed, H0/H1 features validated

### Story 1-0-7: Adversarial Reality Check Bridge
As a Safety Engineer,
I want a non-agentic mechanism to inject immutable physics constants into the manifold,
So that we can detect and pop "Coherence Bubbles" (shared agentic hallucinations).

**Traces:** [FR20]

**Acceptance Criteria:**

**Given** the SubstrateGovernor is monitoring swarm coherence
**When** a periodic Adversarial Reality Check is triggered (configurable interval, default 60s)
**Then** external, non-agentic Truth Anchors (immutable physics constants or pre-verified safety proofs) are injected into the 12D manifold
**And** the swarm's response to these anchors is compared against expected physical behavior.

**Given** the swarm has achieved internal stability through shared hallucination (Coherence Bubble)
**When** the injected Truth Anchor contradicts the swarm's consensus state
**Then** the system flags the bubble, logs the divergence metrics, and triggers a forced re-grounding via the Ouroboros loop.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1-0-8: Heterogeneous Sharding Protocol
As a Systems Engineer,
I want the sharding protocol to support diverse local hardware nodes,
So that we can prove the distributed latent pulse on heterogeneous machines before cloud scaling.

**Traces:** [FR24]

**Acceptance Criteria:**

**Given** a 2048D latent state and two or more heterogeneous compute nodes (e.g., CPU + iGPU)
**When** the sharding protocol distributes latent reasoning across nodes
**Then** each shard is assigned based on hardware capability (memory bandwidth, SIMD width)
**And** the Holographic Pulse synchronization protocol maintains coherence across shard boundaries via Atomic Pointer-Flipping.

**Given** one shard node becomes unavailable (simulated failure)
**When** the synchronization protocol detects a missing heartbeat
**Then** the remaining nodes redistribute the orphaned shard within 2 heartbeat cycles
**And** no latent state is lost (verified by comparing pre- and post-failure checksums).

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1-0-9: Type-Safe Zero-Copy Hardening
As a High-Performance Engineer,
I want strict type-width enforcement on the Rust-Python boundary,
So that zero-copy SHM handoffs are guaranteed against segfaults from type mismatches.

**Traces:** [NFR-9, Security]

**Acceptance Criteria:**

**Given** the Rust-Python SHM boundary using PyO3 and mmap
**When** a 12D state vector is passed from Python to Rust (or vice versa)
**Then** the type-width (Float64, 8 bytes per dimension) is validated at both ends before the pointer flip
**And** a type mismatch causes a hard rejection with a descriptive error (not a segfault).

**Given** a corrupted or truncated SHM buffer (simulated via fault injection)
**When** the Rust side attempts to read the buffer
**Then** the checksum validation fails, the read is rejected, and the system falls back to the last known-good snapshot
**And** the corruption event is logged for Ouroboros training.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.2: VLIW-Aligned Steel Thread (Rust Integration)
As a Research Engineer,
I want to implement the `flume_physics.rs` bridge with VLEN=8 SIMD kernels,
So that I can execute latent instruction packets with hardware-native acceleration for 12D state transitions.

**Traces:** [FR-3, NFR-9]

**Acceptance Criteria:**

**Given** a Rust 2024 edition workspace in `src/cohezion/physics/`
**When** I compile the `flume_vliw.rs` bridge using `cargo build`
**Then** the bridge successfully exposes SIMD-accelerated kernels to Python via PyO3
**And** a benchmark test proves that 12D state transitions occur with <10ms checkpoint latency.

**Given** the Rust toolchain or PyO3 bridge fails to compile
**When** the build process encounters an error
**Then** the system falls back to a pure-Python physics path with degraded performance and logs a structured warning including the exact compilation error
**And** all 12D state tracking continues at reduced throughput (>10ms but functional).

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.3: Substrate Governor & Temporal Dilation
As a Research Engineer,
I want to link the `OverloadCoordinator` signals to the system-wide **Temporal Dilation** protocol,
So that the swarm autonomously slows its reasoning cycles when hardware pressure exceeds 90%.

**Traces:** [FR-9, FR-10, NFR-5, NFR-6]

**Acceptance Criteria:**

**Given** a high-pressure scenario (>90% VRAM/GTT) detected by the `KVCacheTracker`
**When** the `OverloadCoordinator` triggers a graduated response
**Then** the `Substrate Governor` successfully injects a `temporal_dilation` factor into the 12D state stream
**And** the reasoning frequency (pulse) slows deterministically to prevent an OOM crash.

**Given** Temporal Dilation has reached maximum slowdown and pressure continues rising
**When** VRAM/GTT exceeds 95%
**Then** the Governor triggers emergency context eviction (Pre-emptive ZVOL Swap) and logs a "critical pressure" event to SurrealDB
**And** the system recovers to <85% pressure within 30 seconds without losing 12D state integrity.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.4: Substrate Loom Zero-Copy SHM
As a High-Performance Systems Engineer,
I want to implement the `substrate_loom.rs` zero-copy shared memory protocol,
So that 12D state vectors can pass between the Python swarm and the Rust physics engine at 60fps without PCIe bottlenecking or GC pauses.

**Traces:** [FR-3, NFR-1]

**Acceptance Criteria:**

**Given** the VLIW-aligned Steel Thread (Story 1.2)
**When** 512D latent intents are projected to 12D physical states
**Then** `mmap` is used to create a shared memory space bypassing the Python GIL
**And** Atomic Pointer-Flipping is used to synchronize reads/writes between Python and Rust
**And** a performance test proves 60fps bidirectional state synchronization under load.

**Given** the Rust physics engine crashes or becomes unresponsive
**When** the SHM watchdog detects a stale pointer (no flip within 2 heartbeats)
**Then** the Python swarm switches to a degraded single-process mode and logs the crash context for Ouroboros training
**And** in-flight 12D state is preserved via the last committed SHM snapshot.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.5: JourneyPersistenceManager Migration
As a Data Architect,
I want to upgrade the existing `journey_persistence.py` to utilize SurrealDB 3.0 Live Queries and HNSW indexing,
So that 12D trajectories and 512D intents are persisted reliably with <10ms latency.

**Traces:** [NFR-3]

**Acceptance Criteria:**

**Given** the existing TDD-backed `journey_persistence.py` and a running SurrealDB 3.0 instance
**When** the swarm persists a new trajectory node
**Then** the data is dual-written to SurrealDB and the local `.cache` fallback
**And** the persistence latency is benchmarked at <10ms per 12D checkpoint.

**Given** SurrealDB is unavailable or unresponsive
**When** the swarm attempts to persist a trajectory node
**Then** the data is written to the local `.cache` fallback with an idempotency key
**And** a background reconciliation job replays cached writes to SurrealDB when connectivity is restored
**And** no data is lost (verified by comparing cache and DB record counts after recovery).

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.6: Memory-Mapped Barrier Isolation
As a Security Architect,
I want to implement cryptographic memory boundaries around the Vanguard Pipeline's execution space,
So that scraped SOTA models (Substrate Sandbox) cannot perform side-channel attacks on the core FLUME physics.

**Traces:** [NFR-1, Security]

**Acceptance Criteria:**

**Given** the Substrate Loom is active and handling 12D vectors
**When** an unverified SLM executes code within the Substrate Sandbox
**Then** the Memory-Mapped Barrier strictly isolates its VRAM allocation
**And** a test verifying that memory reads outside the allocated GTT bounds are blocked at the barrier level.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.7: Substrate Sandbox Security Verification
As a Security Architect,
I want to red-team the Memory-Mapped Barrier Isolation with adversarial memory access patterns,
So that I have verified proof the Substrate Sandbox cannot perform side-channel attacks on core FLUME physics.

**Traces:** [NFR-1, Security]

**Acceptance Criteria:**

**Given** the Memory-Mapped Barrier is active (Story 1.6)
**When** a penetration test script attempts to read memory outside the allocated GTT bounds
**Then** every read is blocked and logged with the attacker's allocation ID
**And** the core physics substrate continues operating without corruption or latency impact.

**Given** a malicious SLM attempts to allocate memory beyond its sandbox quota
**When** the allocation request exceeds the GTT bounds
**Then** the request is denied and the SLM process is terminated with a structured audit event.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.8: Pre-emptive ZVOL Swap Pipeline
As a Systems Reliability Engineer,
I want to implement an autonomous memory paging pipeline linked to the Substrate Governor,
So that the system dynamically prevents OOM crashes during massive context spikes.

**Traces:** [NFR-1, NFR-5]

**Acceptance Criteria:**

**Given** the `KVCacheTracker` monitoring hardware pressure on the Ryzen AI MAX+
**When** VRAM/GTT pressure spikes rapidly toward the 90% Temporal Dilation threshold
**Then** the Pre-emptive ZVOL Swap Pipeline pages low-priority semantic context to the 32GB NVMe ZVOL buffer.

**Given** the NVMe ZVOL buffer itself is full (32GB exhausted)
**When** additional paging is requested
**Then** the system triggers an ordered agent Apoptosis (lowest-priority agents terminated first) and logs the event chain for Ouroboros analysis
**And** the system never reaches a hard OOM kill — graceful degradation is guaranteed.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 1.9: Distributed Manifold Sharding (Soul-Body Decoupling)
As a High-Performance Systems Engineer,
I want to architect the 2048D latent space for horizontal sharding,
So that complex reasoning (Soul) can be distributed across nodes while the physical projection (Body) remains localized to VLIW hardware.

**Traces:** [Winston Decoupling]

**Acceptance Criteria:**

**Given** the 2048D latent state model
**When** the "Distributed Pulse" flag is enabled
**Then** the latent space is partitioned into addressable shards
**And** a synchronization protocol maintains holographic coherence across the shard boundaries via Atomic Pointer-Flipping.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

## Epic 2: The Multi-Sensory Observatory (KNOWER)

Real-time 12D/512D projection using SurrealDB Live Queries as the Master Clock. Features the Re-Entry Narrative, HIHO-Reactive UI, synchronized Neural Audio, Triune Consensus Visualization, and Persistent Homology Validation.

**Compound Value:** The Master Clock (SurrealDB Live Queries), HIHO CSS Bridge, and WebGL canvas established here become the shared visualization and synchronization layer for all subsequent epics. The Vault inherits the design system. The Cockpit extends the Observatory canvas. The Anima reuses the audio WebSocket infrastructure.

### Story 2.1: Observatory HUD & Viewport Gate [DONE]
As a Research Engineer,
I want to scaffold the React/Vite webapp with a strict desktop-native layout,
So that the high-fidelity 12D visualizations are always presented with sufficient screen real estate and resolution.

**Traces:** [FR-12, NFR-11, NFR-12, NFR-13]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- Built with **Next.js 16** (App Router, Turbopack) instead of React/Vite — superior SSR, dynamic imports for R3F
- `TriuneNav` component: three cognitive modes (KNOWER/THINKER/DOER) with 400-800ms ritualized transitions (NFR12)
- `ObservatoryMode`, `VaultMode`, `CockpitMode` as mode-specific page components
- Viewport gate enforced via Tailwind responsive breakpoints (xl:col-span-8/4 grid)
- WebGL fallback: `dynamic(() => import(...), { ssr: false })` prevents Canvas crash; loading skeleton shown
- **Key files:** `src/web/anima_dashboard/src/app/page.tsx`, `src/web/anima_dashboard/src/components/TriuneNav.tsx`, `src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx`

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [x] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Playwright E2E verification (browser_evaluate workaround for Three.js Canvas)
- [x] Toolchain: Next.js 16, Tailwind v4, TypeScript strict

### Story 2.2: 12D Toroidal Manifold (Three.js/WebGL) [DONE]
As a Research Engineer,
I want to implement a hardware-accelerated 3D manifold,
So that I can observe the projection of 512D latent intents into a 12D axiomatic body.

**Traces:** [FR-1, FR-2, NFR-7, NFR-9]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `TensorBeamVisualizer` renders Clifford Torus approximation (12D→3D stereographic projection)
- 5,000 instanced particles (ParticleSwarm) + 12 ExoticVacuumObjects (EVO charge clusters)
- Kordylewski Clouds (2×2,000 points at L4/L5 Lagrange), WallOfRed plasma containment cylinder
- React Three Fiber (R3F) + drei + postprocessing (Bloom effect)
- HUD overlay shows live coherence, CA density, charge clusters from SSE stream
- **Critical pattern:** Must use `dynamic(() => import(...), { ssr: false })` in parent — see `.claude/rules/frontend.md`
- **Key file:** `src/web/anima_dashboard/src/components/TensorBeamVisualizer.tsx`

**Development Protocol:**
- [x] TDD: Backend universe API (7 endpoints) + frontend integration
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Playwright screenshot verification (browser_snapshot crashes on Canvas — see skill)
- [x] Toolchain: R3F, drei, Three.js, @react-three/postprocessing

### Story 2.3: Re-Entry Narrative (System Voice) [DONE]
As a Practitioner,
I want to be oriented by a first-person system summary upon session arrival,
So that I immediately understand the progress made by the compound cycles during my absence.

**Traces:** [FR-13]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `ReEntryNarrative` component: shows once per session on first Observatory visit (sessionStorage flag)
- Fetches narrative from `/api/universe/report` synthesis endpoint
- Styled with italic serif font, fade-in animation, coherence-aware coloring
- Graceful fallback when backend unavailable (shows "Welcome back" placeholder)
- **Key file:** `src/web/anima_dashboard/src/components/ReEntryNarrative.tsx`

**Development Protocol:**
- [x] TDD: Backend report endpoint tested, frontend verified via Playwright
- [x] Full suite: 56 tests passing, 0 regressions

### Story 2.4: HIHO-Reactive Design System (CSS Bridge) [DONE]
As a Research Engineer,
I want the interface to dynamically shift its visual state based on system coherence,
So that I have instant emotional awareness of the swarm's health.

**Traces:** [FR-14]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `HIHOBridge` headless component sets CSS custom properties on `document.documentElement`
- CSS variables: `--hiho-hue` (0=red to 200=blue), `--hiho-glow-color`, `--hiho-pulse-speed`, `--hiho-particle-density`
- Three zones: CRITICAL (<0.3, red, 2s pulse), WARNING (0.3-0.7, amber, 6s), STABLE (>0.7, green, 12s)
- All components inherit mood via CSS inheritance — no prop drilling needed
- Ambient background glows driven by `var(--hiho-glow-color)`
- **Key file:** `src/web/anima_dashboard/src/components/HIHOBridge.tsx`

**Development Protocol:**
- [x] TDD: Backend HIHO coherence tested, CSS bridge verified via Playwright evaluate
- [x] Full suite: 56 tests passing, 0 regressions

### Story 2.5: Master Clock (SurrealDB Live Queries) [DONE]
As a Systems Architect,
I want to use SurrealDB Live Queries as the master synchronization clock for the UI,
So that visual, auditory, and state updates are perfectly aligned.

**Traces:** [FR-1, FR-2]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- Implemented as **SSE (Server-Sent Events)** at 10Hz instead of SurrealDB Live Queries — simpler, browser-native, no WebSocket dependency
- `UniverseProvider` React Context holds single `EventSource` connection, reconnects with exponential backoff
- `useUniverse()` hook provides `state`, `report`, `connected`, `perturb()`, `fetchReport()` to all components
- FastAPI `/api/universe/stream` endpoint pushes tick data as JSON SSE events
- **Critical pattern:** One SSE connection shared via Context — never per-component polling (see `.claude/rules/frontend.md`)
- **Key files:** `src/web/anima_dashboard/src/context/UniverseProvider.tsx`, `src/cohezion/api/services/universe.py`

**Deviation from spec:** Used SSE instead of SurrealDB Live Queries. SSE is simpler, more reliable for browser clients, and avoids a SurrealDB WebSocket dependency in the frontend. The master clock semantics are preserved — all components update from the same event stream.

**Development Protocol:**
- [x] TDD: 7 API endpoints tested (state, stream, tick, perturb, report, health, config)
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Execution verification: SSE stream confirmed at 10Hz via curl and browser

### Story 2.6: Neural Audio Streaming (Kyutai mimi)
As a Research Engineer,
I want to stream real-time audio representations of agent state,
So that I can "hear" the coherence and drift of the swarm.

**Traces:** [FR-4, NFR-2]

**Acceptance Criteria:**

**Given** the Kyutai `mimi` codec and a binary WebSocket stream
**When** agent thought trajectories are projected to 12D
**Then** base64-encoded audio chunks are streamed and decoded with <200ms latency.

**Given** the Kyutai audio codec fails or the WebSocket stream drops
**When** audio decoding encounters an error
**Then** the Observatory continues rendering visuals without audio (graceful degradation)
**And** a subtle "Audio Offline" indicator appears in the HUD with reconnection status
**And** audio reconnects automatically when the stream recovers.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 2.7: Triune Consensus & Homology Visualization
As a Research Engineer,
I want to see the geometric equilibrium of the Triune agents and the live KL Divergence,
So that I can validate the mathematical rigor of the 512D to 12D projection.

**Traces:** [NFR-7, FR-14]

**Acceptance Criteria:**

**Given** active Architect, Engineer, and Biologist agents
**When** a critical state alteration is proposed
**Then** the UI visualizes the "Geometric Equilibrium" and live KL Divergence score.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

## Epic 3: The Sovereign Vault (THINKER)

Persistent intent recording and Semantic Vault Search across the Three Pillars (Decisions, Experiments, Patterns). Features Provenance-First UX tags, Freeze-Frame Reality Capture, and an asynchronous Vector Pruning & Compaction Engine.

**Compound Value:** The Vault's Three Pillars schema, semantic search, and Freeze-Frame capture become the institutional memory for the entire system. Vanguard discoveries are stored as Patterns. Ouroboros failures are stored as Experiments. Triune decisions are stored as Decisions. The ProvenanceTag convention established here applies system-wide.

### Story 3.1: Vault Infrastructure & Three Pillars Schema [DONE]
As a Research Engineer,
I want to implement the SurrealDB 3.0 schema for Decisions, Experiments, and Patterns,
So that the swarm has a structured institutional memory.

**Traces:** [NFR-3]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `VaultMode` component with tabbed interface for Decisions, Experiments, and Patterns
- Backend vault infrastructure already existed (`~/vaults/cohezion-vault/` with 150+ decisions)
- Frontend now exposes the Three Pillars through the THINKER mode UI
- Each pillar has dedicated search, filtering, and display components
- **Key file:** `src/web/anima_dashboard/src/components/modes/VaultMode.tsx`

**Development Protocol:**
- [x] TDD: VaultMode rendering and tab switching tested
- [x] Full suite: 56 tests passing, 0 regressions

### Story 3.2: Semantic Search Engine (HNSW) [DONE]
As a Researcher,
I want to query the Vault using natural language,
So that I can retrieve relevant historical wisdom with visible match reasoning.

**Traces:** [FR-17]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `VaultMode` component provides search interface across Three Pillars (Decisions/Experiments/Patterns)
- Search routes through backend API to vault search infrastructure
- Results display with match reasoning and ProvenanceTag source tracing
- Empty state handled with "No matches found" UI
- **Key file:** `src/web/anima_dashboard/src/components/modes/VaultMode.tsx`

**Development Protocol:**
- [x] TDD: Backend search endpoints tested
- [x] Full suite: 56 tests passing, 0 regressions

### Story 3.3: Metacognitive Intent Capture (Black Box)
As a Research Engineer,
I want every agent to log a JSON payload explaining its 512D intent,
So that every physical state change is grounded in semantic reasoning.

**Traces:** [FR-6]

**Acceptance Criteria:**

**Given** an active agent in the swarm
**When** the agent proposes a 12D physical state change
**Then** it must log a JSON payload including the 512D latent vector and human-readable intent.

**Given** an agent fails to produce a valid intent payload (malformed JSON or missing 512D vector)
**When** the intent capture middleware intercepts the request
**Then** the state change is blocked and the event is logged as a "Silent Intent Violation" for Ouroboros training
**And** the blocking agent is flagged for Triune review before its next action.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 3.4: Freeze-Frame Reality Capture
As a Research Engineer,
I want the system to capture a full-state snapshot during TDD failures,
So that I have high-fidelity training data for the Ouroboros loop.

**Traces:** [NFR-8]

**Acceptance Criteria:**

**Given** a TDD "Red" state
**When** the failure occurs
**Then** the system captures a "Freeze-Frame" including the 512D latent state and local hash.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 3.5: Provenance-First UX (Data Tags) [DONE]
As a Reviewer,
I want to trace every data point to its exact source,
So that I can trust the integrity of the sovereign engine.

**Traces:** [FR-16]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `ProvenanceTag` component wraps any data value with hover-accessible source tooltip
- Shows exact source function path (e.g., `HIHOStabilizationEngine.apply_hiho_loop()`)
- Used in Mycelium Telemetry panel for coherence, CA density, EVO count, tick
- Design: subtle underline indicator, tooltip appears on hover with full source chain
- **Key file:** `src/web/anima_dashboard/src/components/ProvenanceTag.tsx`

**Development Protocol:**
- [x] TDD: ProvenanceTag rendering tested
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Playwright verification: hover tooltips confirmed via browser_evaluate

### Story 3.6: Vector Pruning & Compaction Engine
As a Systems Architect,
I want an asynchronous engine to manage vector density,
So that SurrealDB performance remains constant across long research horizons.

**Traces:** [FR-8, NFR-3]

**Acceptance Criteria:**

**Given** a session history exceeding 50 compound cycles
**When** the database background worker initializes
**Then** low-relevance 512D vectors are archived/compacted to maintain HNSW resonance.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 3.7: Intent-Action Synchronization
As a Security Architect,
I want to cryptographically sign the relationship between intent and action,
So that "Middle-Man Drift" or substrate tampering is detected immediately.

**Traces:** [FR-6, Security]

**Acceptance Criteria:**

**Given** a 512D intent and its projected 12D state
**When** the update is committed
**Then** the 12D coordinate is cryptographically signed against the intent payload.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

## Epic 4: Vanguard Pipeline & The Anima (DOER)

Autonomous scouting and pattern integration within a Substrate Sandbox. Features the Anima Sigil (Gemma 3n voice) for narration and orientation, Behavioral Alignment Suites, and the Auto-Incinerator for safety.

**Compound Value:** The Vanguard's source connector framework is reusable for any future external integration. The Constitutional Shielding and Auto-Incinerator patterns apply to all untrusted code, not just Vanguard discoveries. The Anima Sigil's narration engine becomes the system's voice across all modes. Every validated discovery compounds the Mycelium Registry.

### Story 4.1: Vanguard Source Connector Framework
As a Research Engineer,
I want a pluggable connector framework that can scrape and normalize content from heterogeneous sources,
So that adding new research sources in the future requires only a new connector — not new infrastructure.

**Traces:** [FR-5, NFR-10]

**Acceptance Criteria:**

**Given** a `SourceConnector` interface with methods `discover()`, `extract()`, and `normalize()`
**When** I implement an ArXiv connector as the reference implementation
**Then** the connector scrapes cs.LG, cs.AI, cs.RO, and cs.NE categories and returns normalized `DiscoveryRecord` objects
**And** each record includes: title, abstract, source URL, category, and extraction timestamp.

**Given** a source (e.g., ArXiv) is unreachable or returns errors
**When** the connector's `discover()` method fails
**Then** the failure is logged with the source name and HTTP status, the scouting cycle continues with remaining sources, and a `SourceHealthReport` is written to SurrealDB
**And** the system never blocks the entire scouting cycle due to a single source failure.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.1b: Vanguard Multi-Source Integration
As a Research Engineer,
I want connectors for all target sources (HuggingFace, GitHub trending, Reddit, Ollama, AI blogs),
So that the Vanguard casts the widest possible net across the AI ecosystem.

**Traces:** [FR-5]

**Acceptance Criteria:**

**Given** the Source Connector Framework from Story 4.1
**When** connectors for HuggingFace, GitHub, Reddit (r/LocalLLaMA, r/MachineLearning), Ollama, and major AI blogs are implemented
**Then** each connector returns normalized `DiscoveryRecord` objects
**And** the daily scouting cycle executes all connectors in parallel with independent error handling.

**Given** the daily scouting cycle completes
**When** results are aggregated
**Then** a `VanguardScoutReport` is persisted to SurrealDB with per-source counts, failure summaries, and total discovery count.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.1c: Vanguard Attribution & License Compliance Engine
As a Research Engineer,
I want every extracted pattern to carry immutable attribution metadata and license verification,
So that the system maintains strict intellectual property compliance and research integrity.

**Traces:** [FR-5, Security]

**Acceptance Criteria:**

**Given** a `DiscoveryRecord` from any source connector
**When** the Attribution Engine processes the record
**Then** it extracts and validates: origin URL, author(s), license type (MIT/Apache/CC-BY/unknown), and generates an immutable content hash
**And** records with `unknown` license are flagged for manual review before integration.

**Given** a discovery with a restrictive or incompatible license (e.g., GPL, proprietary)
**When** the license check fails
**Then** the pattern is quarantined (not integrated) and logged with the specific license violation
**And** the quarantine is visible in the Vault as a "Blocked Discovery" with full provenance.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.2: Substrate Sandbox & Behavioral Validation
As a Security Architect,
I want unverified patterns to execute within a restricted GTT memory environment,
So that new discoveries cannot destabilize the core physics substrate.

**Traces:** [NFR-1, Security]

**Acceptance Criteria:**

**Given** a newly scraped SLM script
**When** validation begins
**Then** the script is executed within the Substrate Sandbox with restricted VRAM.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.3: Constitutional Shielding & Auto-Incinerator
As a Safety Engineer,
I want to audit all scraped code against Anthropic's safety criteria,
So that unsafe patterns are permanently blacklisted.

**Traces:** [NFR-10, Security]

**Acceptance Criteria:**

**Given** code in the Substrate Sandbox
**When** the Constitutional audit triggers
**Then** unsafe code is incinerated and its hash added to a permanent blacklist.

**Given** the Constitutional audit encounters an ambiguous result (borderline safety score)
**When** the score falls between the "safe" and "unsafe" thresholds
**Then** the code is quarantined (not incinerated) and escalated to the Triune Consensus for a deliberated ruling
**And** the quarantine record includes the full audit trace for human review.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.4: The Anima Sigil (Gemma 3n Voice) [DONE]
As a Practitioner,
I want the system to narrate its state and orientation via an edge-native voice,
So that I have a spatial and auditory presence for the system's "Soul."

**Traces:** [FR-15]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `AnimaChatPanel` slide-out panel with chat interface routed through MCP infrastructure
- Supports user questions about HIHO physics, perturbations, system state
- Unmounted when closed (conditional rendering `{chatOpen && <AnimaChatPanel />}`) to prevent hook leaks
- Toggle via TriuneNav header button
- **Deviation:** Uses MCP routing instead of Gemma 3n voice (audio narration deferred to Story 2.6)
- Template-based narration always works (Tier 1, no model dependency) via AnimaNarrationBar
- **Key file:** `src/web/anima_dashboard/src/components/AnimaChatPanel.tsx`

**Development Protocol:**
- [x] TDD: Chat routing tested, unmount behavior verified
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Bug fix: Panel was rendered in DOM when closed (CSS translate) — fixed to conditional render

### Story 4.5: Context-Aware Narration (Anima Intelligence) [DONE]
As a Researcher,
I want the Anima to provide specific, sourced feedback about the system's growth,
So that I can trust its reflections are grounded in data.

**Traces:** [FR-15]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `AnimaNarrationBar` fixed footer with typewriter effect showing live universe state
- Template: `HIHO {stability}: {coherence} coherence. CA Rule 30: {active}/{total} active. {nominal}/{total} EVOs nominal. [tick {n}]`
- All values sourced from live SSE data via `useUniverse()` context — no hardcoded values
- Typewriter effect at 8ms/char with blinking cursor
- Pre-SSE placeholder: "Awaiting first universe tick..." with pulsing dot
- **Critical fix:** Hooks called unconditionally above early return (React rules of hooks compliance)
- **Key file:** `src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx`

**Development Protocol:**
- [x] TDD: Narration generation tested against live metrics
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Bug fix: Empty narration bar showing only "_" — fixed with placeholder + hooks ordering

### Story 4.6: Mycelium Registry (Skill Synthesis)
As a Systems Architect,
I want the system to autonomously register new skills extracted from the journal,
So that the swarm's intelligence compounds automatically.

**Traces:** [FR-11]

**Acceptance Criteria:**

**Given** new entries in the journal
**When** the Mycelium Audit triggers
**Then** new skills are synthesized and registered in the manifold.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 4.7: Immutable Provenance Hashing
As a Reviewer,
I want cryptographic proof of the origin of every pattern and skill,
So that the research integrity is verifiable.

**Traces:** [FR-5, Security]

**Acceptance Criteria:**

**Given** a new pattern integrated via Vanguard
**When** the pattern is persisted
**Then** an Immutable Provenance Hash is appended and signed.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

## Epic 5: Ouroboros Evolution & Loop Theater

Recursive self-healing with high-fidelity Loop Visualization (retrospection summaries + skill diffs). Implements Agentic Mitosis & Apoptosis to biologically balance workloads and Autonomous Skill Registration.

**Compound Value:** This epic closes the compound engineering loop. Every TDD failure becomes VAE training data. Every successful refinement becomes a registered skill. Every retrospection summary becomes a searchable Vault entry. The system's intelligence growth rate accelerates with each completed cycle — the defining property of compound engineering.

### Story 5.1: Ouroboros Trigger (VAE Fine-Tuning Loop)
As a Research Engineer,
I want TDD failures to automatically trigger a VAE fine-tuning iteration,
So that the system autonomously heals its own drift.

**Traces:** [NFR-4, NFR-8]

**Acceptance Criteria:**

**Given** a TDD "Red" state
**When** the Triune Consensus confirms the hash
**Then** the system initiates a VAE fine-tuning iteration.

**Given** the VAE fine-tuning iteration diverges (loss increases for 3+ consecutive epochs)
**When** the Ouroboros watchdog detects divergence
**Then** the iteration is halted, the checkpoint is rolled back to the last stable state, and the divergence event is logged as a Freeze-Frame for post-mortem analysis
**And** the system does not deploy a degraded encoder.

**Given** no Triune Consensus is reached (agents disagree on the failure hash)
**When** the consensus timeout expires (30 seconds)
**Then** the failure is escalated to the Vault as an unresolved Experiment and the fine-tuning is deferred
**And** the existing stable encoder continues operating.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.2: ShadowScripter (Autonomous Test Generation)
As a QA Engineer,
I want the system to autonomously generate new test specifications,
So that coverage expands in lockstep with growth.

**Traces:** [FR-7]

**Acceptance Criteria:**

**Given** a successful refinement
**When** ShadowScripter activates
**Then** it generates new test specs verifying the new logic.

**Given** ShadowScripter generates a test that itself fails (syntax error, incorrect assertion)
**When** the generated test is executed
**Then** the failing test is quarantined (not committed), the generation error is logged as an Experiment in the Vault, and the ShadowScripter's generation prompt is flagged for Ouroboros refinement
**And** the system never commits a broken test to the repository.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.3: Loop Visualization (Visual Theater) [DONE]
As a Practitioner,
I want to witness the internal phases of the compound cycle,
So that the process is transparent.

**Traces:** [FR-18]
**Status:** DONE (2026-03-08, Compound Identity System Sprint)

**Implementation Notes:**
- `OuroborosControlRoom` component in CockpitMode (DOER tab)
- Displays compound cycle phases with live coherence data from SSE stream
- Connected to `useUniverse()` shared context (replaced standalone polling hook)
- Shows cycle metrics: coherence, phase, skill refinement count
- **Bug fix:** Was using separate `useUniverseState()` polling hook — rewired to shared SSE context
- **Key file:** `src/web/anima_dashboard/src/components/OuroborosControlRoom.tsx`

**Development Protocol:**
- [x] TDD: OuroborosControlRoom rendering tested
- [x] Full suite: 56 tests passing, 0 regressions
- [x] Bug fix: "connecting..." stuck state fixed by switching to shared SSE context

### Story 5.4: Retrospection Summaries (Instrument Serif)
As a Researcher,
I want to read the agent's first-person post-mortem after a cycle,
So that I understand the reasoning.

**Traces:** [FR-18, NFR-4, Singular Voice Identity]

**Acceptance Criteria:**

**Given** the completion of the REFLECTING phase
**When** the summary is generated
**Then** it is rendered in Instrument Serif italic using the singular Voice Identity.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.5: Skill Evolution Diffs (Biolume/Plasma)
As a Reviewer,
I want to see the exact textual changes made to a skill definition,
So that the learning is verifiable.

**Traces:** [FR-18]

**Acceptance Criteria:**

**Given** the completion of the REFINING phase
**When** the skill is updated
**Then** a markdown diff appears with Biolume additions and Plasma removals.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.6: Agentic Mitosis & Apoptosis
As a Systems Architect,
I want the swarm to biologically balance its own workload,
So that systemic stagnation is prevented and compound cycles continue even under resource pressure.

**Traces:** [Biological Orchestration, NFR-1]

**Acceptance Criteria:**

**Given** an agent's context window exceeds 80% of its allocated quota
**When** the Governor triggers Mitosis
**Then** the agent splits into two child agents, each receiving: (a) the parent's 512D intent vector, (b) a partitioned subset of the parent's task queue, and (c) a shared reference to the parent's Vault entries
**And** the parent agent is terminated after confirming both children are active
**And** the total VRAM allocation does not exceed the parent's original quota (children share the budget).

**Given** an agent's coherence score drops below 0.3 for 3+ consecutive cycles
**When** the Governor triggers Apoptosis
**Then** the agent's remaining tasks are redistributed to the highest-coherence agent in the same epic
**And** the dying agent's final state is captured as a Freeze-Frame in the Vault for Ouroboros training
**And** VRAM is reclaimed within 5 seconds of termination.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.7: Autonomous Skill Registration (Mycelium)
As a Systems Architect,
I want newly refined skills to be registered automatically,
So that capabilities compound.

**Traces:** [FR-11, Security]

**Acceptance Criteria:**

**Given** a refined skill
**When** the Ouroboros cycle completes
**Then** the skill is registered and signed with a Provenance Hash.

**Given** a skill registration conflicts with an existing skill (same name, different definition)
**When** the registration is attempted
**Then** a version increment is created (not an overwrite), both versions are preserved in the Vault, and the diff between versions is recorded as a Decision for Triune review
**And** the system defaults to the newer version unless the Triune downgrades it.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.8: Lifecycle Pre-Simulation (Agentic OS)
As a Research Engineer,
I want agents to model the 12D trajectory of a proposed implementation lifecycle before commit,
So that architectural collisions and "Coherence Debt" are detected early.

**Traces:** [FR19]

**Acceptance Criteria:**

**Given** a proposed implementation plan (Requirement → Architecture → Code)
**When** the agent initiates "Pre-Precipitation Simulation"
**Then** the system models the 12D trajectory of the entire lifecycle across the manifold
**And** any projected coherence drops or "Topological Knots" are flagged as blocking errors.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 5.9: Adversarial Reality Grounding
As a Safety Engineer,
I want the system to periodically inject immutable "Truth Anchors" into the 12D manifold,
So that "Coherence Bubbles" (shared agentic hallucinations) are detected and popped.

**Traces:** [FR20]

**Acceptance Criteria:**

**Given** an active 12D manifold state
**When** the Adversarial Grounding trigger activates
**Then** external non-agentic data (physics constants, safety proofs) are injected as adversarial perturbations into the latent space
**And** if the manifold coherence remains stable despite conflicting truth anchors, a "Hallucination Alert" is logged and the swarm is forced into a resynchronization cycle.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

## Epic 6: [ASPIRATIONAL] Cloud Substrate Expansion (Ironwood)
*Note: This epic represents the post-hiring strategic horizon and is dependent on access to Google Cloud TPU v7 infrastructure.*

The system transcends local hardware limits by migrating the 2048D sharded latent space to a Google Cloud TPU v7 (Ironwood) Pod, enabling high-density, multi-agent cosmogenesis simulations at planetary scale.

**Compound Value:** This epic leverages all previous work on Soul-Body Decoupling (Story 1.9) and Distributed Pulse protocols. It provides the "Endgame" substrate for the project's long-term research mission.

### Story 6.1: Ironwood TPU-VM Provisioning (UCP/MCP)
As a Systems Architect,
I want to automate the procurement and provisioning of a TPU v7 Ironwood pod via the UCP/MCP protocol,
So that the system can autonomously scale its compute substrate based on research demand.

**Acceptance Criteria:**
**Given** a qualified collateral asset in the Sovereign Vault
**When** compute demand exceeds local Ryzen thresholds
**Then** the system initiates a UCP/MCP procurement request for a TPU v7 Ironwood pod.

### Story 6.2: XLA-Accelerated Latent Sharding
As a High-Performance Systems Engineer,
I want to port the sharded latent kernels to XLA (Accelerated Linear Algebra),
So that 2048D manifold computations can leverage the TPU's matrix processing units (MXU).

### Story 6.3: Planetary Scale Cosmogenesis Simulation
As a Research Engineer,
I want to execute a simulation involving 10,000+ agents across a unified Ironwood-backed manifold,
So that I can observe emergent macro-sociological patterns in agentic reasoning.

## Epic 7: Automated Version Health & Compound Registry

Automated semver compliance, dependency security scanning, and version telemetry within the 12D manifold. This epic implements the critical infrastructure for version governance that compounds with every other epic — ensuring that the system's own evolution remains traceable, secure, and self-healing.

**Compound Value:** Version health gates protect all downstream deployments. The Compound Version Registry becomes the institutional memory for every epic's dependency evolution. The Ouroboros-style version healing extends the self-healing paradigm from code logic to dependency management. Version telemetry provides real-time observability into the system's own "health" at the manifest level.

### Story 7.1: Semver CI Pipeline Setup
As a DevOps Engineer,
I want automated version detection using git tags and changelog analysis with semantic-release or changesets workflow,
So that every release enforces semantic versioning compliance.

**Traces:** [NFR-AUTO_VERSION_HEALTH]

**Acceptance Criteria:**

**Given** a git repository with annotated tags following semver (vMAJOR.MINOR.PATCH)
**When** the CI pipeline triggers on the main branch
**Then** the version is automatically detected from the latest tag, compared against the changelog, and validated for correct bump type (major/minor/patch)
**And** the release is published with correct version metadata.

**Given** a Pull Request that proposes an incorrect version bump (e.g., patch bump when a breaking change is detected)
**When** the PR check validates semver compliance
**Then** the PR is blocked with a clear error message indicating: expected bump type, reason for rejection, and suggested fix
**And** the commit history is analyzed to provide context for the rejection.

**Given** the changelog is missing required sections for the proposed version bump
**When** the semantic-release validation runs
**Then** the release is blocked and a structured error lists the missing changelog entries
**And** the PR author receives actionable guidance on required documentation.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 7.2: Dependency Security Scanner
As a Security Engineer,
I want integrated dependabot/renovate for automated dependency updates with CVE vulnerability scanning,
So that the team is notified within 24 hours of security vulnerabilities.

**Traces:** [NFR-AUTO_VERSION_HEALTH]

**Acceptance Criteria:**

**Given** the repository is configured with dependabot or renovate
**When** a new vulnerability is published in a direct or transitive dependency
**Then** a security alert is generated within 24 hours of CVE publication
**And** the alert includes: affected package, severity (CVSS score), vulnerable version range, and remediation steps.

**Given** a security vulnerability with severity >= 7.0 (High or Critical)
**When** the scanner detects the vulnerability
**Then** an automatic PR is created with the minimal version bump to resolve the vulnerability
**And** the PR includes the CVE reference, CVSS score, and changelog entry.

**Given** an outdated dependency that has known security issues but no immediate CVE
**When** the dependency scanning runs
**Then** a deprecation warning is logged with: current version, latest stable version, known issues summary, and recommended upgrade path
**And** the warning is surfaced in the Observatory version telemetry dashboard.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 7.3: Compound Version Registry
As a Data Architect,
I want a version registry in `src/cohezion/registry/version_registry.md` that logs all version changes with full diff context,
So that every version bump is traceable to its originating epic/story.

**Traces:** [NFR-COMPOUND_VERSION_REGISTRY]

**Acceptance Criteria:**

**Given** a version bump is merged to main
**When** the release pipeline completes
**Then** a new entry is appended to `src/cohezion/registry/version_registry.md` containing: version, release date, full changelog diff, and linked epic/story IDs
**And** the entry includes a semantic link to the PRD requirement that triggered the version change.

**Given** the version registry is queried for a specific epic
**When** a stakeholder wants to understand the version history related to Epic X
**Then** the registry returns all version bumps linked to that epic, sorted by release date
**And** each entry includes the complete diff between the previous and current version.

**Given** a version change requires rollback
**When** the registry is searched for the previous stable version
**Then** the full context of the change (epic, story, PR, author) is retrieved in <1 second
**And** the rollback can be executed with full traceability.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 7.4: Version Telemetry Dashboard
As a Research Engineer,
I want real-time version state visualization in the 12D manifold Observatory,
So that I can monitor version coherence metrics analogous to HIHO stability.

**Traces:** [NFR-VERSION_TELEMETRY]

**Acceptance Criteria:**

**Given** the Observatory Dashboard is active
**When** the version telemetry module initializes
**Then** a new "Version Health" panel is rendered alongside the 12D manifold
**And** the panel displays: current versions of all dependencies, version drift indicators, and coherence score (0.0-1.0).

**Given** a dependency version drifts beyond the acceptable threshold (configurable, default: 2 minor versions behind latest)
**When** the telemetry scanner runs (configurable interval, default: hourly)
**Then** the drift is visualized as an amber/red indicator in the Version Health panel
**And** an alert is logged with: drifted package, current vs latest version, and recommended action.

**Given** multiple dependencies have conflicting version requirements (e.g., Package A requires X>=1.0 while Package B requires X<1.5)
**When** the version conflict detector runs
Then a "Version Coherence Collapse" alert is triggered (analogous to HIHO < 0.3)
**And** the specific conflict is visualized in the manifold with a topological knot indicator
**And** the Ouroboros Version Healing (Story 7.5) is automatically triggered.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 7.5: Ouroboros Version Healing
As a Systems Engineer,
I want automatic version conflict detection and resolution proposals between compound agent dependencies,
So that 80% of version conflicts self-heal without human intervention.

**Traces:** [NFR-OUROBOROS_VERSION_HEALING]

**Acceptance Criteria:**

**Given** a version conflict between two or more dependencies (detected in Story 7.4)
**When** the Ouroboros Version Healing module activates
**Then** it analyzes the dependency graph to identify the minimal set of version changes that resolve all conflicts
**And** a resolution proposal is generated with: changed packages, old version -> new version, and compatibility rationale.

**Given** a simple version conflict (single package, compatible upgrade path)
**When** the healing module analyzes the conflict
**Then** the resolution is applied automatically within 5 minutes of detection
**And** the change is logged to the version registry with an "auto-healed" flag.

**Given** a complex version conflict requiring VAE fine-tuning (multiple packages, breaking changes, no compatible resolution)
**When** the automatic resolution fails
**Then** a detailed conflict report is generated including: all conflicting constraints, attempted resolutions, and manual intervention required
**And** the VAE is triggered to model potential resolution paths as a compound reasoning problem
**And** a human operator is notified with the conflict report and VAE-generated proposals.

**Given** a version healing iteration introduces a regression (test failure, runtime error)
**When** the regression is detected
**Then** the healing system automatically rolls back to the previous state
**And** the regression is logged as a Freeze-Frame for Ouroboros training
**And** the healing algorithm is refined to avoid the failed path in future iterations.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)

### Story 7.6: Version Traceability Gate
As a Release Engineer,
I want every story's dependencies linked to semver contracts with epic completion blocking,
So that 100% of stories have version traceability and version impact reports are generated for each release.

**Traces:** [NFR-AUTO_VERSION_HEALTH]

**Acceptance Criteria:**

**Given** a story is marked as "Done" in the epic tracking system
**When** the story closure is processed
**Then** all dependencies introduced or updated by that story are logged with their semver contract (exact version or range)
**And** the contract is stored in the Compound Version Registry linked to the epic/story ID.

**Given** an epic attempts to complete while version contracts are violated (e.g., missing version traceability for dependencies)
**When** the epic completion gate runs
**Then** the completion is blocked with a detailed report listing: missing contracts, affected stories, and remediation steps
**And** the block persists until all version contracts are resolved.

**Given** a release is about to be published
**When** the version impact report is generated
**Then** the report includes: all stories included in the release, their version changes, breaking change analysis, and security impact summary
**And** the report is automatically attached to the release notes.

**Given** a security vulnerability is discovered in a previously released version
**When** the incident response queries the version traceability system
**Then** the system returns: all epics/stories affected by the vulnerable dependency, the release versions impacted, and recommended patch versions
**And** the response time is <30 seconds for any query.

**Development Protocol** (see [development-standards.md](development-standards.md)):
- [ ] TDD: Red (failing test per AC) -> Green (minimal code) -> Refactor
- [ ] Coverage: >= 90% line, >= 80% branch (business logic); contract tests for boundaries
- [ ] Failure ACs: Explicit failure injection with `pytest.raises(match=...)`
- [ ] Full suite: `uv run pytest tests/ -q` — 0 regressions
- [ ] CI gate: ruff check + ruff format + mypy + `--cov-fail-under=90` + execution verification
- [ ] Toolchain: uv, pyproject.toml, Ruff — no bare pip/pytest/black
- [ ] Frameworks: per section 0.2 matrix (pytest-benchmark for perf, Playwright for UI, GE for batch data)
