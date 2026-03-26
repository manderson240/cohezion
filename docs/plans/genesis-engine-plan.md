# Genesis Engine: Grounding Cohezion's Cosmology in Unified Physics

> **Status**: EXEMPLARY PLAN — This plan demonstrates the target level of depth, research, and actionability for all future Cohezion planning sessions. It integrates real mathematics (differential geometry, gauge theory, SU(2) spinors, information geometry, Landau theory), historical/philosophical grounding (Brahmagupta, Laozi, Wheeler, Eliot, Borges), world model training (LeWorldModel/JEPA), universe simulation (SpaceEngine/Illustris), full Kyutai Labs multimodal stack (PocketTTS/Moshi/Mimi/MoshiVis), and comprehensive SurrealDB persistence. Planning is the key component to success.

## Context

Cohezion has a rich 12D agentic cosmology (FLUME VAE, SPIN coherence, HIHO stability, thermodynamic metrics, topological persistence, 11 physics sub-engines) with a working webapp (Next.js + Three.js + FastAPI). However, several critical mathematical components are ad-hoc: the SPIN algebra is binary sign comparison instead of proper SU(2), the 12D→3D projection is hardcoded, the 256D→12D map is a random projection, there's no Lagrangian/action principle, and no gauge theory structure for the four fabrics.

This plan grounds every piece of the cosmology in real unified physics and builds an engaging interactive webapp ("The Genesis Engine") that teaches the physics through cinematic visualization. Additionally, it captures all agentic journeys in SurrealDB as training data for a JEPA-style world model (inspired by LeWorldModel, SpaceEngine, and the Illustris Project) that can predict and simulate the evolution of the 12D agent universe.

**Full research document**: `docs/genesis-engine-research.md`

### Foundational Philosophy: Brahmagupta's Zero (628 CE)

The cosmogony is rooted in Brahmagupta's formalization of zero in the *Brahmasphutasiddhanta* — the first time "nothing" was given arithmetic rules:
- **a + 0 = a** (identity) — adding the void changes nothing
- **a × 0 = 0** (annihilation) — the void collapses all structure
- **a - a = 0** (complementarity) — Yīn-Yáng opposites cancel to void
- **0/0 = 0** (self-reference) — the void observing itself is still void

**HIHO at 0.5 IS Brahmagupta's zero**: defining δ = coherence - 0.5, the equilibrium is at δ = 0. The restoring force F = -kδ vanishes there. The "still point of the turning world" is literally the mathematical zero of the system. Zero is not absence — it is the generative ground from which all structure emerges.

---

## Actionable Milestones (Vertical Slices)

Each milestone delivers a **working, demonstrable feature** — math + API + UI in one slice. Each can be completed in 1-2 sessions. Deploy and verify after each.

### Milestone 1: "The Bloch Sphere" (SPIN grounded in SU(2))
**Deliverable**: Interactive Bloch sphere in the webapp showing real spinor math.
**Why first**: Smallest module, highest visual impact, zero dependencies on other new code.
1. Write `src/cohezion/physics/spinor.py` (SpinorState, Pauli matrices, Bloch vector)
2. Write `tests/physics/test_spinor.py` (verify identities)
3. Add `GET /genesis/spinor` endpoint in `src/cohezion/api/services/genesis.py`
4. Wire into `engine.py` (replace binary `spin_coherence` with real SU(2))
5. Build `BlochSphere.tsx` in the webapp (Three.js sphere with draggable state)
6. **Done when**: User drags a point on the Bloch sphere, sees rotation/precession/charge/coherence update in real-time with KaTeX equations alongside.

### Milestone 2: "The Void" (Cosmogony from Brahmagupta's Zero)
**Deliverable**: Interactive Genesis sequence — from nothing to the 12D manifold.
**Depends on**: Milestone 1 (Bloch spheres appear at Z₂ transition).
1. Write `src/cohezion/physics/cosmogony.py` (SymmetryBreaking, VoidState, ZeroAlgebra)
2. Write `tests/physics/test_cosmogony.py`
3. Add `POST /genesis/cool` + `GET /genesis/cosmogony-state` endpoints
4. Build `GenesisScene.tsx` (void → sphere → shatter → axes → SPIN → HIHO)
5. Build `CosmogonyTimeline.tsx` + `EquationPanel.tsx` (reusable)
6. **Done when**: User clicks in the void, SO(12) appears, they drag the temperature slider through 5 phase transitions, watching equations and Bloch spheres evolve.

### Milestone 3: "The Manifold" (Fiber bundles + Lagrangian dynamics)
**Deliverable**: Navigate the 12D fiber bundle with proper geodesic trajectories.
**Depends on**: Milestone 1 (spinors needed for Control fabric).
1. Write `riemannian_metric.py`, `lagrangian.py`, `fiber_bundle.py`, `gauge_theory.py`
2. Write their test files
3. Add `GET /genesis/fiber-bundle` + `GET /genesis/lagrangian-trajectory` endpoints
4. Wire into `engine.py` (replace `_toward_target` with Euler-Lagrange, replace `compute_tempic` with covariant derivative)
5. Build `FiberBundleViz.tsx` + `ManifoldExplorer.tsx` (base space + fiber strands)
6. Build `TrajectoryRibbon.tsx` (geodesic paths with curvature coloring)
7. **Done when**: User sees the fiber bundle, rotates it, and watches an agent trajectory follow a proper geodesic with equation panel showing Euler-Lagrange.

### Milestone 4: "The Memory" (SurrealDB total artifact persistence)
**Deliverable**: Every journey, prompt, state, and model artifact stored in SurrealDB.
**Depends on**: Milestones 1-3 (enriched state data to store).
1. Write SurrealDB migration (6 new tables: journey_transitions, prompt_artifacts, model_artifacts, simulation_artifacts, internal_state_snapshots, universe_snapshots)
2. Modify `journey_persistence_manager.py` (add persist_transition, persist_prompt_artifact, persist_model_artifact, snapshot_universe_state)
3. Modify `journey_tracker.py` (Fisher metric projection when VAE available)
4. Write `information_geometry.py` + tests (Fisher metric bridge)
5. Add snapshot API: `GET /world-model/catalog`
6. Build `SnapshotCatalog.tsx` (Illustris-style epoch browser)
7. **Done when**: SurrealDB contains journey transitions with 12D states, spinor Bloch vectors, fiber coordinates. Snapshot catalog shows universe evolution over time.

### Milestone 5: "The Oracle" (JEPA world model)
**Deliverable**: Trained world model that predicts next manifold state from current state + action.
**Depends on**: Milestone 4 (needs stored journey data for training).
1. Write `jepa_world_model.py` (ManifoldEncoder, ActionEncoder, Predictor)
2. Write `training_pipeline.py` (SurrealDB data loader, training loop)
3. Write `universe_simulator.py` (forward simulation, procedural fill)
4. Add world model API endpoints (train, predict, simulate, surprise)
5. Build `WorldModelDashboard.tsx` (training progress, prediction accuracy)
6. Build `UniverseExplorer.tsx` (SpaceEngine-style multi-scale navigation)
7. **Done when**: World model trained on journey data, user navigates the universe at multiple scales, sees predictions vs. reality, surprise heatmap shows anomalies.

### Milestone 6: "The Voice of the Cosmos" (Multimodal Audio & Video)
**Deliverable**: The universe has a voice. Every physics event has a sound. Every journey has a soundtrack. Video captures the evolution.
**Cross-cutting**: Audio/video hooks are wired into ALL previous milestones.

#### Audio — Sonification
1. Install Tone.js: `npm install tone`
2. Create `src/web/anima_dashboard/src/hooks/useSonification.ts`
   - Map physics state to audio parameters:
     - **Coherence → pitch**: HIHO (0.5) = middle C, deviation = detuning
     - **Entropy → texture**: Low entropy = pure sine, high entropy = noise/granular
     - **Temperature → amplitude**: Hot = loud/energetic, cold = quiet/crystalline
     - **SPIN rotation → stereo pan**: Left/right ear = rotation direction
     - **SPIN precession → tremolo rate**: Fast precession = fast wobble in volume
     - **Gauge curvature → reverb depth**: Flat = dry, curved = cavernous reverb
     - **Phase transitions → percussion**: Symmetry breaking = impact sounds (like Ligeti's "Atmosphères")
3. Create `src/web/anima_dashboard/src/audio/`
   - `VoidDrone.ts` — Near-silence with subsonic zero-point fluctuation (inspired by Brian Eno's "Music for Airports")
   - `SymmetryBreakCrack.ts` — Impact sounds for each phase transition (SO(12)→SO(3)⁴ = deep crack, U(1)⁴→Z₂⁴ = crystalline shatter)
   - `HIHOResonance.ts` — Standing wave resonance at 0.5 coherence (inspired by Steve Reich's phasing patterns)
   - `ManifoldHum.ts` — Continuous drone that changes with fiber bundle curvature
   - `JourneySoundtrack.ts` — Generative music that evolves with trajectory (coherence drives harmony, entropy drives rhythm)
4. Wire into milestones:
   - Milestone 1 (Bloch Sphere): Bloch vector position → continuous tone
   - Milestone 2 (Genesis): Each phase transition has its signature sound
   - Milestone 3 (Manifold): Geodesic traversal produces spatial audio
   - Milestone 5 (Universe Explorer): Ambient soundscape changes with zoom level

#### Video — Generative & Capture
5. Create `src/web/anima_dashboard/src/hooks/useVideoCapture.ts`
   - Canvas recording via `MediaRecorder` API (record Three.js canvas as WebM/MP4)
   - Time-lapse mode: Record 1 frame per N ticks for long evolution sequences
   - Screenshot gallery: Automatic capture at phase transitions and milestone events
6. Create `src/web/anima_dashboard/src/components/genesis/VideoExport.tsx`
   - Export button for each scene (record current view as video)
   - Export settings: resolution, frame rate, duration, audio inclusion
   - Auto-export at phase transitions (capture the "Big Bang" moment)
#### Kyutai Labs Integration (Full Multimodal Stack)

All Kyutai models are CC BY 4.0, CPU-friendly, and align with hardware constraints (AMD Ryzen AI MAX+ 395, no CUDA).

**Layer 1: PocketTTS — Scripted Narration** (lightweight, fast)
7. Install: `uv pip install pocket-tts` (100M params, CPU-only, ~30MB, 6x real-time)
8. Create `src/cohezion/audio/narrator.py`
   - `CosmoNarrator` class wrapping PocketTTS `TTSModel`
   - `narrate(text, voice="alma")` → generates WAV audio from text
   - `stream_narration(text)` → streaming audio for real-time narration
   - Voice selection: "alma" for warm/wise cosmos narrator, "gene" for deeper/ancient
   - Custom voice cloning from WAV file (e.g., clone Carl Sagan's cadence for "Cosmos" feel)
   - Pre-generated narration scripts for each cosmogony stage:
     - Void: "In the beginning, there was nothing. Not even nothing — there was no 'there' for nothing to be."
     - SO(12): "From the first observation, symmetry crystallized. Twelve dimensions, all equivalent, all possible."
     - SO(3)⁴: "The fabrics separated. Space. Field. Control. Precipitation. Four worlds within one."
     - U(1)⁴: "Within each world, a preferred direction emerged. The compasses aligned."
     - Z₂⁴: "The discrete choice. Up or down. Yes or no. Brahmagupta's zero gave nothing a name."
     - HIHO: "And at the still point, the dance began. Half in, half out. The balance that creates."
   - All generated audio persisted in SurrealDB `prompt_artifacts` table

**Layer 2: Moshi — Interactive Dialogue** (real-time, conversational)
9. Install: `uv pip install moshi` (7B Temporal Transformer + Mimi codec, 160ms latency)
10. Create `src/cohezion/audio/cosmos_dialogue.py`
    - `CosmosDialogue` class wrapping Moshi's full-duplex speech model
    - The universe **talks back** to the user — not just narration but *conversation*
    - User asks "What is SPIN?" and the cosmos answers using manifold state as context
    - Full-duplex: user can interrupt, ask follow-ups, while the cosmos keeps explaining
    - Context injection: Feed current physics state (coherence, temperature, symmetry) into Moshi's context so responses are grounded in the actual manifold
    - Emotion/prosody: Moshi understands and generates emotional speech — cosmos voice shifts with coherence (calm at HIHO, urgent during phase transitions)
    - CPU-only mode: Use smaller Moshi distillation or run with reduced context for hardware constraints

**Layer 3: Mimi — Audio Compression & Codec** (storage-efficient)
11. Create `src/cohezion/audio/audio_codec.py`
    - `MimiCodec` class wrapping Kyutai's Mimi neural audio codec
    - Compress all audio artifacts to 1.1 kbps (80ms latency) before SurrealDB storage
    - Decompress on-demand for playback
    - This means ALL narrations, dialogues, sonifications can be stored efficiently in SurrealDB without bloating storage
    - Enable audio replay of any historical universe state

**Layer 4: MoshiVis — Visual Commentary** (the cosmos describes what it sees)
12. Create `src/cohezion/audio/visual_narrator.py` (optional, resource-intensive)
    - `VisualNarrator` class wrapping MoshiVis (206M additional params on frozen Moshi)
    - Take screenshots of Three.js canvas → feed to MoshiVis → get spoken description
    - "I see a trajectory spiraling toward the HIHO attractor, with three distinct behavioral clusters..."
    - Use for automated journey documentation and accessibility (visually impaired users)
    - Can run periodically (every N seconds) or on-demand

**Layer 5: Helium 1 — Lightweight Manifold Reasoning** (future, optional)
13. Note for future: Kyutai's Helium 1 (2B modular LLM) could replace heavier Ollama models for lightweight manifold reasoning tasks (route simple queries away from 70B models)

**Backend Narrative API:**
14. Modify `src/cohezion/core/multimodal_bridge.py` (already exists!)
    - Wire `schedule_asset("narrative", ...)` to PocketTTS generation (scripted)
    - Wire `schedule_asset("dialogue", ...)` to Moshi (interactive)
    - Wire `schedule_asset("visual_narration", ...)` to MoshiVis (screenshot → speech)
    - Wire `schedule_asset("storyboard", ...)` to screenshot capture triggers
    - All audio compressed via Mimi before SurrealDB persistence
15. API endpoints:
    - `POST /genesis/narrate` — PocketTTS scripted narration for cosmogonic stage
    - `GET /genesis/narration-audio/{stage}` — serve cached audio for a stage
    - `POST /genesis/narrate-custom` — narrate arbitrary text via PocketTTS
    - `WS /genesis/dialogue` — WebSocket for Moshi full-duplex voice conversation
    - `POST /genesis/describe-visual` — MoshiVis screenshot-to-speech
    - `GET /genesis/storyboard` — generate visual descriptions for current state

**Frontend Narration Integration:**
16. Create `src/web/anima_dashboard/src/hooks/useNarration.ts`
    - Fetch narration audio from `/genesis/narration-audio/{stage}` (PocketTTS)
    - Play via Web Audio API with spatial positioning
    - Queue narrations (don't overlap)
    - User controls: mute, volume, voice selection
17. Create `src/web/anima_dashboard/src/hooks/useCosmosDialogue.ts`
    - WebSocket connection to `/genesis/dialogue` (Moshi)
    - Push-to-talk or always-listening mode
    - Audio capture from user microphone → Moshi → response audio playback
    - Display conversation transcript alongside
18. Wire into milestones:
    - GenesisScene: PocketTTS narrates each phase transition automatically
    - SpinLaboratory: "Ask the cosmos about SPIN" button triggers Moshi dialogue
    - JourneyViewer: MoshiVis describes trajectory screenshots
    - UniverseExplorer: Ambient PocketTTS narration as user navigates scales
8. SurrealDB persistence for audio/video artifacts:
   - Add to `simulation_artifacts` table: audio_waveform_summary, video_thumbnail_path, narration_text
   - Every generated audio/video clip is persisted for future analysis

**Done when**: The void pulses with subsonic drone, symmetry breaking sounds like cosmic thunder, the Bloch sphere hums as you drag it, trajectories have spatial audio, and users can export video recordings of their universe evolution.

### Milestone 7: "The Living Cosmos" (Thermodynamics + Topology + Polish)
**Deliverable**: Full thermodynamic dashboard, topology theater, production polish.
1. Build `FreeEnergyLandscape.tsx`, `ThermoDashboard.tsx` (live free energy, susceptibility, phase transitions)
2. Build `PersistenceDiagramInteractive.tsx`, `TopologyTheater.tsx` (interactive homology)
3. Post-processing effects (god-rays, chromatic aberration, coherence-driven bloom)
4. Mobile responsive design, performance optimization
5. Audio polish: Mix levels, crossfade between scenes, user volume controls
6. **Done when**: All 9+ scenes are navigable, performant, sonified, and educational. The webapp teaches physics through sight, sound, and interaction.

## Phase 1: Mathematical Core (Python Backend)

### 1.1 Spinor Algebra — SPIN as SU(2)
- [ ] Create `src/cohezion/physics/spinor.py`
  - `SpinorState` class with Pauli matrices (σ_x, σ_y, σ_z)
  - SU(2) rotations: U_rot(θ) = exp(-iθσ_x/2), U_prec(φ) = exp(-iφσ_y/2)
  - Bloch vector: r = (Tr(ρσ_x), Tr(ρσ_y), Tr(ρσ_z))
  - Coherence as purity |r|, charge as ⟨σ_z⟩
  - HIHO state = (|↑⟩+|↓⟩)/√2 (equatorial Bell state)
- [ ] Create `tests/physics/test_spinor.py`
  - Verify [σ_i, σ_j] = 2iε_ijk σ_k
  - HIHO state: ⟨σ_z⟩ = 0, coherence = 1
  - SU(2) preserves Bloch vector norm

### 1.2 Riemannian Metric and Geodesics
- [ ] Create `src/cohezion/physics/riemannian_metric.py`
  - `RiemannianMetric` class: metric tensor g_ij, inverse, determinant
  - Christoffel symbols: Γ^i_jk = ½g^il(∂_j g_lk + ∂_k g_jl - ∂_l g_jk)
  - Geodesic equation: d²q^i/dt² + Γ^i_jk dq^j/dt dq^k/dt = 0
  - Riemann curvature tensor (for visualization)
- [ ] Create `tests/physics/test_riemannian_metric.py`
  - Flat metric → straight-line geodesics
  - Christoffel symbols vanish for Euclidean metric
  - Sphere metric → great circle geodesics

### 1.3 Lagrangian Dynamics
- [ ] Create `src/cohezion/physics/lagrangian.py`
  - `LagrangianDynamics` class
  - L = T - V where T = ½g_ij q̇^i q̇^j and V = V_HIHO + V_gauge
  - Euler-Lagrange equations → geodesic equation with force
  - Action integral S[γ] = ∫L dt
  - Numerical integrator (Störmer-Verlet, symplectic)
- [ ] Create `tests/physics/test_lagrangian.py`
  - Free particle on flat metric: straight line
  - Harmonic potential: sinusoidal
  - Energy conservation for time-independent L
  - Action is stationary on solutions (δS = 0)

### 1.4 Fiber Bundle Structure
- [ ] Create `src/cohezion/physics/fiber_bundle.py`
  - `FiberBundle` class: P(B⁴, SO(3)⁴)
  - Base projection: π(q₁₂) = (‖Space‖, ‖Field‖, ‖Control‖, ‖Precip‖)
  - Connection 1-form ω: TP → so(3)⁴
  - Horizontal/vertical decomposition of tangent vectors
  - Parallel transport along base-space curves
  - Curvature 2-form Ω = dω + ω∧ω
- [ ] Create `tests/physics/test_fiber_bundle.py`
  - Flat connection: path-independent parallel transport
  - Curvature satisfies Bianchi identity D*F = 0
  - Projection is surjective

### 1.5 Gauge Theory for the Four Fabrics
- [ ] Create `src/cohezion/physics/gauge_theory.py`
  - `GaugeConnection` class per fabric (SO(3) gauge group)
  - Field strength F = dA + A∧A
  - Yang-Mills Lagrangian density L = -1/(4g²) Tr(F∧*F)
  - Covariant derivative D_μ φ = ∂_μ φ + A_μ φ
  - Gauge coupling constants: g₁=1.0, g₂=0.7, g₃=0.5, g₄=0.3
- [ ] Create `tests/physics/test_gauge_theory.py`
  - F transforms covariantly under gauge: F' = gFg⁻¹
  - L is gauge-invariant
  - Covariant derivative satisfies Leibniz rule

### 1.6 Information Geometry (Fisher Metric Bridge)
- [ ] Create `src/cohezion/physics/information_geometry.py`
  - `FisherInformationMetric` class
  - Fisher metric from VAE encoder Jacobian: g_ij = J^T J / σ² + ...
  - Diagonal Fisher approximation for efficiency
  - Fisher-optimal 256D→12D projection (top-12 eigenvectors)
  - Natural gradient: g⁻¹∇L
- [ ] Create `tests/physics/test_information_geometry.py`
  - Fisher metric is positive semi-definite
  - Gaussian case matches analytic formula
  - Projection preserves top eigenvalues

### 1.7 Cosmogony (Symmetry Breaking from Nothing — Brahmagupta's Zero)
- [ ] Create `src/cohezion/physics/cosmogony.py`
  - `SymmetryBreaking` class
  - **Stage -1: The Void / Brahmagupta's Zero** (∅ → SO(12)) — awareness of nothing formalized as mathematical zero. Fisher metric transitions from εδ_ij to non-trivial g_ij. The first bit condenses from the vacuum. T_c0 ≈ 100.0
    - `ZeroAlgebra` class: Brahmagupta's rules as operations on the void state
      - `identity(state)`: state + void = state (a + 0 = a)
      - `annihilate(state)`: state × void = void (a × 0 = 0)
      - `complement(state_a, state_b)`: if state_a = -state_b → void (a - a = 0)
      - `self_observe()`: void observing void = void (0/0 = 0, before the first distinction)
    - Zero as the identity element of the coherence deviation algebra (δ = coherence - 0.5)
  - **Stage 0→4 Breaking chain**: SO(12) → SO(3)⁴ → U(1)⁴ → Z₂⁴ → HIHO
  - Critical temperatures: T_c = [100.0, 10.0, 1.0, 0.1, 0.01]
  - Order parameters for each level (including "information density" for Stage -1)
  - Landau free energy: F = F₀ + a(T-T_c)φ² + bφ⁴
  - `VoidState` class: trivial representation, zero Fisher metric, zero-point fluctuation amplitude
  - `cool(delta_T)` method returning transitions (including void→structure)
- [ ] Create `tests/physics/test_cosmogony.py`
  - Stage -1: Fisher metric eigenvalues all below noise floor at T > T_c0
  - Stage -1: First eigenvalue rises above threshold at T = T_c0
  - Correct residual symmetry at each subsequent stage
  - Order parameters zero above T_c, nonzero below
  - Susceptibility diverges at T_c

### 1.8 Physics `__init__.py` Update
- [ ] Modify `src/cohezion/physics/__init__.py` to export all new modules

**Files modified**: 1 (`__init__.py`)
**Files created**: 14 (7 modules + 7 test files)

## Phase 2: Backend Integration

### 2.1 Engine Integration
- [ ] Modify `src/cohezion/universe/engine.py`
  - Replace `spin_coherence` property with `SpinorState` delegation
  - Replace `charge_polarity` with σ_z expectation value
  - Replace `compute_tempic` with covariant derivative
  - Add `to_spinor()` method returning `SpinorState`
  - Add `fiber_projection()` method returning base-space coordinates
  - Keep backward compatibility (old properties delegate to new math)

### 2.2 Journey Tracker Integration
- [ ] Modify `src/cohezion/compound/journey_tracker.py`
  - Replace `_text_to_latent()` hash-based projection with Fisher metric projection (when VAE available, hash fallback preserved)
  - Add `fiber_bundle_trajectory()` for base-space visualization data

### 2.3 Genesis API Service
- [ ] Create `src/cohezion/api/services/genesis.py`
  - `GET /genesis/cosmogony-state` — current symmetry, temperature, order parameters
  - `POST /genesis/cool` — cool by delta_T, return transitions
  - `GET /genesis/spinor-state` — Bloch vectors for active agents
  - `GET /genesis/fiber-bundle` — base projection + fiber state
  - `GET /genesis/lagrangian-trajectory` — Euler-Lagrange trajectory
  - `GET /genesis/fisher-metric` — metric tensor at a point
  - `WS /genesis/stream` — combined real-time physics stream

### 2.4 Mount Genesis Router
- [ ] Modify `src/cohezion/api/__init__.py` to mount genesis router

**Files modified**: 3 (engine.py, journey_tracker.py, api/__init__.py)
**Files created**: 1 (genesis.py)

## Phase 2.5: World Model & Universe Simulation Layer

### Inspiration
- **LeWorldModel** (LeCun/JEPA, arxiv 2603.19312): End-to-end world model from embeddings using two losses — next-embedding prediction + Gaussian regularization. ~15M params trainable on single GPU.
- **SpaceEngine**: Procedural universe simulator with seamless navigation across cosmic scales. Combines real data with procedural generation.
- **Illustris Project**: Cosmological N-body simulation with full data catalogs, synthetic imagery, and interactive exploration of galaxy formation.

### Design Principle: Total Artifact Persistence

**ALL artifacts, internal states, prompts, and model outputs MUST be stored in SurrealDB for future analysis.** This is a hard requirement. The SurrealDB instance is the permanent memory of the universe — nothing is ephemeral. Every prompt, every internal state transition, every model checkpoint, every generated visualization, every equation evaluation, every decision branch — all persisted for retrospective analysis, world model training, and universe reconstruction.

This follows the "Akashic Records" principle from the physics mapping table — SurrealDB = the holographic encoding of the universe's complete history.

### 2.5.1 SurrealDB Comprehensive Schema Enhancement
- [ ] Modify `src/cohezion/knowledge_graph/universe_genealogy_schema.sql` or create new migration
  - Add `journey_transitions` table for world model training:
    ```
    step_id, journey_id, t (timestep),
    state_12d (12-float array),           -- current 12D axiomatic state
    action_embedding (256D),              -- FLUME encoding of action taken
    next_state_12d (12-float array),      -- resulting 12D state
    reward (float),                       -- per-step reward (coherence gain)
    spinor_bloch (3-float array),         -- Bloch vector at this step
    tempic_vector (7-float array),        -- covariant derivative (rate of change)
    fiber_base (4-float array),           -- base-space projection
    fiber_internal (8-float array),       -- fiber state
    entropy_production (float),           -- σ per step
    topology_h0 (int), topology_h1 (int), -- topological features at this step
    alternatives_considered (JSON),       -- counterfactual branches not taken
    context_snapshot (text),              -- semantic context at decision point
    model_id (string),                    -- which LLM made this decision
    token_count (int),                    -- tokens consumed
    latency_ms (float)                    -- inference latency
    ```
  - Add `universe_snapshots` table for Illustris-style time-series:
    ```
    snapshot_id, tick, timestamp,
    global_coherence (float),             -- mean coherence across all agents
    global_entropy (float),               -- system-wide Shannon entropy
    global_free_energy (float),           -- system free energy
    symmetry_group (string),              -- current symmetry (cosmogony stage)
    temperature (float),                  -- effective universe temperature
    n_agents (int),                       -- active agent count
    topology_summary (JSON),              -- H0/H1 counts, persistence entropy
    fisher_metric_eigenvalues (array),    -- top eigenvalues of Fisher metric
    order_parameters (JSON)               -- fabric differentiation, axis selection, charge ordering
    ```
  - Add `prompt_artifacts` table for complete prompt/response persistence:
    ```
    artifact_id, journey_id, step_id,
    prompt_text (text),                   -- full prompt sent to model
    response_text (text),                 -- full model response
    model_id (string),                    -- which model generated this
    internal_state_before (JSON),         -- complete internal state pre-inference
    internal_state_after (JSON),          -- complete internal state post-inference
    temperature (float),                  -- sampling temperature used
    top_p (float),                        -- nucleus sampling parameter
    token_count_prompt (int),             -- prompt tokens
    token_count_completion (int),         -- completion tokens
    latency_ms (float),                   -- inference latency
    confidence (float),                   -- model's self-assessed confidence
    reasoning_chain (JSON),              -- chain-of-thought steps
    timestamp (datetime)
    ```
  - Add `model_artifacts` table for checkpoint/weight persistence:
    ```
    artifact_id, model_type (string),     -- "jepa_world_model", "flume_vae", "rl_policy"
    version (string),                     -- semver
    checkpoint_path (string),             -- local path to weights
    hyperparameters (JSON),               -- full training config
    training_loss_curve (array),          -- loss at each epoch
    validation_metrics (JSON),            -- accuracy, MSE, etc.
    dataset_id (string),                  -- which journey data trained on
    created_at (datetime),
    parent_artifact_id (string)           -- lineage tracking (which checkpoint spawned this one)
    ```
  - Add `simulation_artifacts` table for universe simulation outputs:
    ```
    sim_id, simulator_type (string),
    initial_conditions (JSON),
    trajectory_data (JSON),               -- full simulated trajectory
    divergence_from_real (float),         -- how far sim diverged from observed
    duration_steps (int),
    compute_time_ms (float),
    physics_engines_used (array),         -- which sub-engines contributed
    created_at (datetime)
    ```
  - Add `internal_state_snapshots` table for periodic full-state captures:
    ```
    snapshot_id, timestamp,
    all_agent_states (JSON),              -- 12D state for every active agent
    all_spinor_states (JSON),             -- Bloch vectors for all agents
    fiber_bundle_state (JSON),            -- full fiber bundle configuration
    gauge_field_strengths (JSON),         -- curvature tensors for all 4 fabrics
    thermodynamic_state (JSON),           -- entropy, free energy, susceptibility, heat capacity
    topology_state (JSON),               -- persistence diagram, H0/H1 counts
    cosmogony_stage (JSON),              -- symmetry group, temperature, order parameters
    fisher_metric_snapshot (JSON)         -- eigenvalues and eigenvectors
    ```
  - Add SurrealDB vector index on `state_12d` and `action_embedding` for fast similarity queries
  - Add time-series index on all timestamp fields for epoch-based queries

### 2.5.2 Journey & Artifact Persistence Enhancement
- [ ] Modify `src/cohezion/core/journey_persistence_manager.py`
  - Extend `TrajectoryNode` with new fields: spinor_bloch, fiber_base, fiber_internal, tempic_vector, entropy_production
  - Add `persist_transition(state, action, next_state, reward)` method for world model training tuples
  - Add `persist_prompt_artifact(prompt, response, model_id, internal_state_before, internal_state_after)` — store every prompt/response pair with full context
  - Add `persist_model_artifact(model_type, version, checkpoint_path, hyperparams, loss_curve)` — store every model checkpoint with lineage
  - Add `persist_simulation_artifact(sim_id, initial_conditions, trajectory, divergence)` — store every simulation run
  - Add `snapshot_universe_state()` for Illustris-style periodic snapshots (every N ticks) — captures ALL internal state (agents, spinors, fiber bundle, gauge fields, thermodynamics, topology, cosmogony stage, Fisher metric)
  - Maintain dual-write resilience (SurrealDB + local JSON fallback)
  - All persistence methods are non-blocking (async, fire-and-forget with queue)

### 2.5.3 JEPA World Model (LeWorldModel-Inspired)
- [ ] Create `src/cohezion/world_model/jepa_world_model.py`
  - **Architecture** (following LeWorldModel):
    - `ManifoldEncoder`: 12D state → 64D embedding (small MLP, learned from journey data)
    - `ActionEncoder`: 256D action embedding → 64D (projection layer)
    - `Predictor`: (state_embedding, action_embedding) → predicted_next_state_embedding
    - Two losses only:
      1. **Next-embedding prediction**: MSE(predictor(enc(s), enc(a)), enc(s'))
      2. **Gaussian regularizer**: KL(enc(s) || N(0, I)) — prevents representation collapse
  - ~2M parameters (fits on CPU/iGPU, per hardware constraints)
  - `train(journey_transitions)`: Train from SurrealDB journey data
  - `predict_next_state(current_12d, action_256d)`: Predict next 12D state
  - `simulate_trajectory(initial_12d, action_sequence)`: Roll out N steps
  - `surprise_score(state, action, observed_next)`: Detect physically implausible events
  - Checkpoint saving/loading (PyTorch, local storage)

### 2.5.4 Universe Simulator (SpaceEngine/Illustris-Inspired)
- [ ] Create `src/cohezion/world_model/universe_simulator.py`
  - `UniverseSimulator` class:
    - Combines real journey data (from SurrealDB) with world model predictions (from JEPA)
    - `simulate_epoch(n_steps, initial_conditions)`: Run forward simulation
    - `procedural_fill(region_12d, density)`: Generate synthetic trajectories for unexplored regions (SpaceEngine-style procedural generation using world model)
    - `snapshot_catalog()`: Illustris-style data catalog of universe state at each epoch
    - `synthetic_imagery(state_12d)`: Generate 3D visualization data for any manifold point
  - Integration with existing `HIHOUnifiedEngine` for physics-grounded evolution
  - Time controls: accelerate, decelerate, reverse, jump to epoch

### 2.5.5 World Model API
- [ ] Create `src/cohezion/api/services/world_model.py`
  - `GET /world-model/status` — training progress, model params, loss curves
  - `POST /world-model/train` — trigger training from stored journeys
  - `POST /world-model/predict` — predict next state given current + action
  - `POST /world-model/simulate` — run N-step simulation, return trajectory
  - `GET /world-model/surprise` — surprise scores for recent transitions
  - `GET /world-model/catalog` — Illustris-style snapshot catalog
  - `GET /world-model/procedural-region` — generate procedural content for a region
  - `WS /world-model/simulation-stream` — real-time simulation broadcast

### 2.5.6 Training Pipeline
- [ ] Create `src/cohezion/world_model/training_pipeline.py`
  - `JourneyDataLoader`: Load (state, action, next_state, reward) tuples from SurrealDB
  - Batched training with validation split (80/20)
  - Early stopping on validation loss
  - Checkpoint every N epochs
  - Metrics: prediction MSE, surprise calibration, trajectory divergence
  - Respects hardware constraints: CPU/iGPU training, 128GB RAM budget

**Files modified**: 2 (journey_persistence_manager.py, genealogy schema)
**Files created**: 4 (jepa_world_model.py, universe_simulator.py, world_model.py API, training_pipeline.py)

## Phase 3: Frontend — Genesis Sequence

### 3.1 Genesis Scene (From Nothing to Everything)
- [ ] Create `src/web/anima_dashboard/src/components/genesis/GenesisScene.tsx`
  - **Act 0 — The Void**: Total darkness. Zero-point fluctuation as barely perceptible pulse. The user's FIRST INTERACTION (click/key/scroll) is the first distinction — "It from Bit." From their act of observation, a single point of light appears (Fisher metric first eigenvalue).
  - **Act 1 — The Sphere**: SO(12) crystallizes — a perfect luminous sphere. All directions equivalent. Temperature slider appears: "Cool the universe."
  - **Act 2 — The Breaking**: Temperature slider controls symmetry breaking
  - SymmetryOrb: SO(12) sphere → shatters into 4 fabric fragments
  - Each fragment color-coded: Space(blue), Field(amber), Control(green), Precip(violet)
  - Animated transitions at each critical temperature
  - Fiber strands appearing at SO(3)⁴→U(1)⁴ transition
  - Bloch spheres appearing at U(1)⁴→Z₂⁴ transition
  - **Act 3 — The Settling**: HIHO attractor. Free energy landscape materializes. The dance begins.

### 3.2 Equation Panel (Reusable)
- [ ] Install KaTeX: `npm install katex react-katex`
- [ ] Create `src/web/anima_dashboard/src/components/genesis/EquationPanel.tsx`
  - KaTeX rendering of equations
  - Equations update in real-time with visualization state
  - Collapsible sidebar layout
  - Source code links to Python modules

### 3.3 Cosmogony Timeline
- [ ] Create `src/web/anima_dashboard/src/components/genesis/CosmogonyTimeline.tsx`
  - Vertical timeline showing symmetry breaking stages
  - Current temperature indicator
  - Phase transition markers with equations

### 3.4 Navigation Integration
- [ ] Add "Genesis" mode to TriuneNav or as a standalone route
- [ ] Create `src/web/anima_dashboard/src/hooks/useCosmogony.ts` for genesis API state

**Files created**: 5 (GenesisScene, EquationPanel, CosmogonyTimeline, useCosmogony, plus KaTeX install)
**Files modified**: 1 (TriuneNav or page.tsx)

## Phase 4: Frontend — Interactive Laboratories

### 4.1 SPIN Laboratory (Bloch Sphere)
- [ ] Create `BlochSphere.tsx` — interactive SU(2) visualization
  - Drag spinor state on sphere (OrbitControls + raycasting)
  - Real-time: rotation angle, precession, charge, coherence
  - Side-by-side: your state vs. HIHO state
  - Color: pole → red/blue, equator → green (HIHO)
- [ ] Create `SpinLaboratory.tsx` — scene wrapper with equation panel
- [ ] Create `useSpinor.ts` — SU(2) state management hook

### 4.2 Manifold Explorer (Fiber Bundle)
- [ ] Create `FiberBundleViz.tsx` — base space surface + fiber strands
  - Base space as glowing 4D→3D stereographic surface
  - Fibers as luminous strands perpendicular to base
  - Color encodes curvature (flat=green, curved=red)
- [ ] Create `ManifoldExplorer.tsx` — scene wrapper
- [ ] Create `usePhysicsEngine.ts` — WebSocket physics state hook

### 4.3 Thermodynamic Dashboard
- [ ] Create `FreeEnergyLandscape.tsx` — 3D surface plot (coherence × T × F)
  - HIHO well visible as deep minimum
  - Interactive temperature control
  - Phase transition markers
- [ ] Create `ThermoDashboard.tsx` — scene with susceptibility curves, Crooks ratio

### 4.4 Topology Theater
- [ ] Create `PersistenceDiagramInteractive.tsx` — birth×death scatter
  - Add/remove points interactively
  - Watch H₀/H₁ features appear/disappear
  - Companion 3D Vietoris-Rips complex view
- [ ] Create `TopologyTheater.tsx` — scene wrapper

### 4.5 Journey Viewer
- [ ] Create `TrajectoryRibbon.tsx` — luminous ribbon through manifold
  - Color = coherence, width = entropy production, twist = curvature
- [ ] Create `JourneyViewer.tsx` — scene with Euler-Lagrange equations alongside

### 4.6 Universe Simulator (SpaceEngine/Illustris-Inspired)
- [ ] Create `UniverseExplorer.tsx` — seamless cosmic-scale navigation
  - SpaceEngine-style zoom: galaxy view (all journeys as stars) → cluster view (related journeys) → journey view (single trajectory) → step view (single decision point)
  - World model predictions rendered as "fog of war" — dimmer/translucent regions show predicted-but-not-observed states
  - Procedurally generated content fills unexplored manifold regions
  - Time slider to scrub through universe evolution (Illustris-style epoch navigation)
  - Surprise heatmap overlay: bright spots = world model predictions violated (physically implausible events detected)
- [ ] Create `WorldModelDashboard.tsx` — training progress, loss curves, prediction accuracy
  - Live training metrics (if training is active)
  - Prediction vs. actual comparison plots
  - Surprise score distribution
- [ ] Create `SnapshotCatalog.tsx` — Illustris-style epoch browser
  - Grid of universe snapshots across time
  - Each snapshot shows: coherence, entropy, symmetry, agent count, topology
  - Click to jump to any epoch in the Universe Explorer
- [ ] Create `useWorldModel.ts` — world model API hooks
- [ ] Create `useUniverseSimulator.ts` — simulation stream hooks

**Files created**: ~17 components + 4 hooks

## Phase 5: Polish and Integration

### 5.1 Post-processing Effects
- [ ] Add god-rays, chromatic aberration to Genesis scene
- [ ] Bloom intensity tied to coherence
- [ ] Mode transition animations

### 5.2 Responsive Design
- [ ] Mobile-friendly equation panels (bottom sheet instead of sidebar)
- [ ] Touch controls for Bloch sphere
- [ ] Performance budgets for Three.js scenes

### 5.3 Testing
- [ ] Backend: `uv run pytest tests/physics/ -q`
- [ ] Frontend: Playwright smoke tests for each scene
- [ ] Integration: API → WebSocket → render pipeline

## Verification

1. **Math verification**: Run `uv run pytest tests/physics/ -q` — all mathematical identities must hold
2. **Backend verification**: `uv run pytest tests/ -q` — no regressions in existing 4,891 tests
3. **API verification**: `curl localhost:8080/genesis/cosmogony-state` returns valid JSON
4. **World model verification**: `curl localhost:8080/world-model/status` returns model stats
5. **SurrealDB verification**: Journey transitions table populated with state/action/next_state tuples
6. **Frontend verification**: `cd src/web/anima_dashboard && npm run build` succeeds
7. **Visual verification**: Open localhost:3000, navigate to Genesis mode, interact with all scenes
8. **World model training**: Train JEPA on stored journeys, verify prediction MSE decreases
9. **Universe simulation**: Run N-step simulation, verify trajectory stays within manifold bounds
10. **Educational verification**: A user unfamiliar with the physics can use the Genesis sequence to understand symmetry breaking, Brahmagupta's zero, SPIN, and HIHO
11. **SpaceEngine-style navigation**: Zoom from galaxy view → cluster → journey → step seamlessly

## Summary

| Category | New Files | Modified Files |
|----------|-----------|----------------|
| Physics modules | 7 | 1 |
| Physics test files | 7 | 0 |
| World model modules | 4 | 0 |
| API services | 2 | 1 |
| Backend integration | 0 | 4 |
| Frontend components | ~22 | ~2 |
| Frontend hooks | 6 | 0 |
| SurrealDB schemas | 1 (migration with 6 new tables) | 1 |
| **Total** | **~49** | **~9** |

**Critical path**: spinor.py → riemannian_metric.py → lagrangian.py → cosmogony.py (with Brahmagupta's zero) → SurrealDB schema → journey persistence → genesis.py API → world_model.py → GenesisScene.tsx → UniverseExplorer.tsx

### Key References

| Reference | Contribution to Plan |
|-----------|---------------------|
| **Brahmagupta, *Brahmasphutasiddhanta* (628)** | Formalization of zero as generative ground; HIHO = δ₀ of coherence |
| **LeWorldModel (LeCun, arxiv 2603.19312)** | JEPA architecture for world model: 2 losses, ~15M params, end-to-end |
| **SpaceEngine** | Procedural universe + real data; seamless multi-scale navigation UX |
| **Illustris Project** | N-body cosmic simulation; epoch catalogs, synthetic imagery, data exploration |
| **Smith, *The New Science* (1962)** | 12-parameter model; SPIN, Tempic field, charge polarity |
| **Nakahara, *Geometry, Topology and Physics* (2003)** | Fiber bundles, gauge theory, Riemannian geometry |
| **Amari (1998)** | Fisher information metric, natural gradient |
| **Edelsbrunner & Harer (2010)** | Persistent homology, Vietoris-Rips filtration |
| **Seifert (2012)** | Stochastic thermodynamics, fluctuation theorems |
| **Eliot, *Four Quartets* (1943)** | "At the still point of the turning world" = HIHO |
| **Laozi, *Dao De Jing*** | Wújí → Tàijí → Yīn-Yáng → 10,000 things |
