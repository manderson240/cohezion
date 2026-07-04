# Latent Mind Theater — Implementation Plan

Created: 2026-06-27
Status: COMPLETE
Approved: Yes
Iterations: 0
Worktree: No

## Summary

**Goal:** Build "Latent Mind Theater" — a dual agent/human interface for visualizing agentic journeys as exotic vacuum object analogues (vortex strings / Hopf fibration fiber circles) through the FLUME VAE and Quadrature Nexus, developed with V-model rigor and tested with end-user agents.

**Architecture:** Three-layer V-model:
1. System requirements → FastAPI data contracts (`VizFrame`, `VizPoint`, `NexusState`) + `/frame` + `/stream/viz` endpoints
2. Module spec → 5 Three.js React components (`HopfManifold`, `QuadratureNexus`, `JourneyRibbon`, `LatentParticles`, `VacuumFog`)
3. Agent acceptance test → Python agent that calls `/frame` and validates routing_tier + nexus metrics

**Physics rationale:** Vortex strings (φ = f(r)·e^{iℓθ}) decompose into I/Q quadrature exactly matching the Quadrature Nexus. BKT transition at 50% coherence = HIHO operating point. Hopf fiber circles are cross-sections of vortex strings — same math, dual visual.

**Tech Stack:** FastAPI + Pydantic v2, Three.js R3F + Drei, SSE streaming, Lemonade local inference for agent test

## Scope

### In Scope
- FastAPI: VizPoint, NexusState, VizFrame Pydantic models
- FastAPI: GET /journey-nexus/frame → VizFrame
- FastAPI: GET /journey-nexus/stream/viz → SSE VizFrame stream
- Unit tests for the three new models and two new endpoints
- 5 React Three.js components (HopfManifold, QuadratureNexus, JourneyRibbon, LatentParticles, VacuumFog)
- Agent acceptance test that validates the /frame endpoint programmatically
- Vault decision logging

### Out of Scope
- Changes to existing routes (evo, quadrature, narrate, omni)
- Integration into /genesis page routing (separate PR)
- Production FLUME VAE embedding (uses stub that returns fixed 12D coords)
- Robinhood / live trading (always excluded)

## Context for Implementer

- **Existing router**: `src/cohezion/api/routes/journey_nexus.py` — follow exact pattern: `_get_nexus()` lazy singleton, `_nexus_instance` module-level var monkeypatched in tests
- **Existing service**: `src/cohezion/api/services/journey_nexus.py` — `EVOEvent` uses dataclass; new Pydantic models go in the ROUTER module (not service), following the OmniChatRequest pattern
- **Existing tests**: `tests/api/test_journey_nexus_router.py` — tests use `_async_stub_nexus()` factory and `monkeypatch.setattr(router_mod, "_get_nexus", ...)` pattern
- **Semantic projection**: x = mean(dims[0:3]), y = mean(dims[3:6]), z = mean(dims[6:12]), scaled [-1,1]
- **Nexus I/Q**: I = `cache_stats["overall_hit_rate"] / 100`, Q = `detector_baselines["coherence"].mean` if established else 0.5
- **Vacuum field**: flat list of 4096 floats (16³), zero in stub mode
- **Web component dir**: `src/web/anima_dashboard/src/components/` — new components go in `vacuum/` subdir
- **Existing nexus components**: `components/nexus/{AskOmni,EVOField,NarratePanel,QuadraturePanel}.tsx`

## Progress Tracking

- [x] Task 1: FastAPI — VizPoint, NexusState, VizFrame Pydantic models + /frame + /stream/viz endpoints
- [x] Task 2: Tests — discriminating unit tests for VizFrame endpoint and SSE stream
- [x] Task 3: HopfManifold.tsx — Hopf fibration geometry with thin-film iridescence shader
- [x] Task 4: QuadratureNexus.tsx — saddle geometry with Einstein ring + gravitational lens warp
- [x] Task 5: JourneyRibbon.tsx — CatmullRom ribbon wired to /frame API
- [x] Task 6: LatentParticles.tsx — 50k particle system driven by coherence
- [x] Task 7: VacuumFog.tsx — raymarched volumetric fog from density field
- [x] Task 8: Agent acceptance test — Python agent that calls /frame and validates nexus metrics
- [x] Task 9: Vault decision log

**Total Tasks:** 9 | **Completed:** 9 | **Remaining:** 0

## Implementation Tasks

### Task 1: FastAPI — VizPoint, NexusState, VizFrame + /frame + /stream/viz

**Objective:** Add three Pydantic models and two new endpoints to the existing journey_nexus router. The `/frame` endpoint returns a single `VizFrame` snapshot; `/stream/viz` streams them as SSE. This is the machine-readable API layer for agents.

**Dependencies:** None

**Files:**
- Modify: `src/cohezion/api/routes/journey_nexus.py`

**Key Decisions:**
- VizPoint derives from JourneyTracker `trajectory_point` data; in stub mode generates 3 deterministic fake points
- NexusState I/Q computed from cache stats + detector baselines (both stubbed as 0.5 when unavailable)
- VizFrame.vacuum_field is 4096 zeros in stub mode (16³ KDE would require FLUME + cache data)
- `mhd_ripple_phase` = `(timestamp * 0.3) % (2 * math.pi)` — drives MHD standing wave visualization
- All new models use Pydantic BaseModel (not dataclass) for OpenAPI schema exposure
- `/stream/viz` yields one frame per 2s, frame_id increments each tick

**Definition of Done:**
- [ ] `from cohezion.api.routes.journey_nexus import VizPoint, NexusState, VizFrame` works
- [ ] GET /journey-nexus/frame returns 200 with a VizFrame-shaped JSON body
- [ ] GET /journey-nexus/stream/viz returns 200 with content-type text/event-stream
- [ ] All existing tests in test_journey_nexus_router.py still pass

**Verify:**
- `uv run pytest tests/api/test_journey_nexus_router.py -q` — all existing tests pass

---

### Task 2: Discriminating unit tests for VizFrame endpoint

**Objective:** Write discriminating tests that prove the VizFrame structure is correct, not merely that the endpoint fires. Tests must fail for a trivially wrong VizFrame (e.g., wrong nexus I/Q range, missing vacuum_field shape).

**Dependencies:** Task 1

**Files:**
- Modify: `tests/api/test_journey_nexus_router.py`

**Key Decisions:**
- Stub nexus must add `viz_frame()` method returning a deterministic VizFrame
- Tests check: nexus I/Q in [0,1], vacuum_field length == 4096, points list is non-empty, each VizPoint has all required fields
- Discriminating test: nexus.distance == sqrt((I-0.5)^2 + (Q-0.5)^2), not just "is a float"
- SSE test: first data: line parses as valid VizFrame JSON with correct frame_id == 0

**Definition of Done:**
- [ ] test_viz_frame_returns_correct_structure passes
- [ ] test_viz_frame_nexus_iq_in_range passes (discriminating)
- [ ] test_viz_frame_vacuum_field_shape passes
- [ ] test_stream_viz_sse_format passes
- [ ] test_stream_viz_frame_id_starts_at_zero passes

**Verify:**
- `uv run pytest tests/api/test_journey_nexus_router.py -q`

---

### Task 3: HopfManifold.tsx

**Objective:** ~300 Hopf fiber loop instances using InstancedMesh + TubeGeometry, with thin-film iridescence GLSL shader that glows at HIHO 50% coherence.

**Dependencies:** None (pure geometry, no data dependency)

**Files:**
- Create: `src/web/anima_dashboard/src/components/vacuum/HopfManifold.tsx`

**Key Decisions:**
- Hopf parametric: η = θ/2; x = cos(η)cos(φ+t)/(√2 - sin(η)sin(φ+t)); etc.
- 300 fibers: θ ∈ [0, 2π] uniformly sampled, each fiber has 64 tube segments
- GLSL thin-film shader: thinFilm = RGB from phase-shifted sin(), hihoGlow peaks at coherenceScore=0.5
- InstancedMesh with per-instance color based on winding number (warm=NPU, cool=CPU, neutral=iGPU)
- Props: coherenceScore (float), tier_used (string), time (float from useFrame)

**Definition of Done:**
- [ ] Component renders without TypeScript errors (`npx tsc --noEmit`)
- [ ] Uses ShaderMaterial with vertexShader + fragmentShader (thin-film iridescence)
- [ ] Exports `HopfManifold` as named export

**Verify:**
- `cd src/web/anima_dashboard && npx tsc --noEmit 2>&1 | grep -c error || echo "0 errors"`

---

### Task 4: QuadratureNexus.tsx

**Objective:** Saddle surface geometry representing the I/Q phase space with Einstein ring (torus) and gravitational lens warp post-effect driven by nexus distance.

**Dependencies:** None

**Files:**
- Create: `src/web/anima_dashboard/src/components/vacuum/QuadratureNexus.tsx`

**Key Decisions:**
- Saddle: z = I² - Q² geometry on 32×32 grid mesh
- Einstein ring: TorusGeometry centered at (0.5, 0.5, 0) in IQ space
- Lens warp: vertex shader distorts UV by nexus_distance * 0.3 toward center
- HIHO equilibrium point (0.5, 0.5) marked with emissive sphere
- Props: nexusI (float), nexusQ (float), nexusPower (float)

**Definition of Done:**
- [ ] Component renders without TypeScript errors
- [ ] Exports `QuadratureNexus` as named export
- [ ] nexusPower prop drives ring emissive intensity

**Verify:**
- `cd src/web/anima_dashboard && npx tsc --noEmit 2>&1 | grep -c error || echo "0 errors"`

---

### Task 5: JourneyRibbon.tsx

**Objective:** CatmullRom spline ribbon through journey points fetched from /api/journey-nexus/frame, colored by coherence gradient, with winding number rotation speed.

**Dependencies:** Tasks 1 (needs /frame endpoint shape)

**Files:**
- Create: `src/web/anima_dashboard/src/components/vacuum/JourneyRibbon.tsx`

**Key Decisions:**
- Fetches /api/journey-nexus/frame every 2s via useEffect + fetch
- Maps VizPoint.{pos_x, pos_y, pos_z} → THREE.Vector3 for CatmullRomCurve3
- Tube radius = VizPoint.radius, color hue = VizPoint.color_hue
- Glow pulse driven by VizPoint.glow + Math.sin(time * VizPoint.rotation_speed)
- Falls back to dummy 3-point ribbon when API is unavailable

**Definition of Done:**
- [ ] Component renders without TypeScript errors
- [ ] Exports `JourneyRibbon` as named export
- [ ] Uses CatmullRomCurve3 from THREE

**Verify:**
- `cd src/web/anima_dashboard && npx tsc --noEmit 2>&1 | grep -c error || echo "0 errors"`

---

### Task 6: LatentParticles.tsx

**Objective:** 50k particle system where each particle's position/color/size is driven by coherence score and FLUME latent dimensions, creating a "thought field" effect.

**Dependencies:** None (can use static params)

**Files:**
- Create: `src/web/anima_dashboard/src/components/vacuum/LatentParticles.tsx`

**Key Decisions:**
- BufferGeometry with 50,000 particles in positions Float32Array
- Coherence drives particle dispersion radius (low coherence = tight cluster, high = expanded)
- HIHO at 0.5 = maximum particle animation speed (logistic map resonance)
- Custom PointsMaterial with size attenuation
- Props: coherenceScore (float), dims12d (number[12]) for offset vectors

**Definition of Done:**
- [ ] Component renders without TypeScript errors
- [ ] Exports `LatentParticles` as named export
- [ ] Uses BufferGeometry with position attribute

**Verify:**
- `cd src/web/anima_dashboard && npx tsc --noEmit 2>&1 | grep -c error || echo "0 errors"`

---

### Task 7: VacuumFog.tsx

**Objective:** Raymarched volumetric fog driven by the 16³ vacuum_field density array from /frame. 48 march steps, RDNA 3.5 safe (50% resolution + bilateral upscale).

**Dependencies:** Task 1 (needs vacuum_field shape)

**Files:**
- Create: `src/web/anima_dashboard/src/components/vacuum/VacuumFog.tsx`

**Key Decisions:**
- ShaderMaterial with raymarching fragment: 48 steps along view ray sampling density field
- Density field uploaded as DataTexture3D (16×16×16 RGBA)
- 50% resolution rendering via `gl.setPixelRatio(0.5)` during fog pass, reset after
- Bilateral upscale approximated in fragment shader (edge-preserving blur)
- Props: vacuumField (Float32Array | number[]), mhdRipplePhase (float)

**Definition of Done:**
- [ ] Component renders without TypeScript errors
- [ ] Exports `VacuumFog` as named export
- [ ] Uses THREE.Data3DTexture for density field

**Verify:**
- `cd src/web/anima_dashboard && npx tsc --noEmit 2>&1 | grep -c error || echo "0 errors"`

---

### Task 8: Agent acceptance test

**Objective:** Python agent that calls /frame, validates the VizFrame structure, interprets routing_tier and nexus metrics, and reports findings — testing the machine-readable API layer end-to-end.

**Dependencies:** Tasks 1, 2

**Files:**
- Create: `tests/api/test_latent_mind_theater_agent.py`

**Key Decisions:**
- Uses FastAPI TestClient (same pattern as existing tests) — no live network
- Agent stub calls /frame and checks: nexus.I in [0,1], nexus.Q in [0,1], len(points) >= 1, len(vacuum_field) == 4096
- "Agent interpretation" test: routing_tier from first VizPoint maps to winding_number (NPU→+1, CPU→-1, iGPU→0)
- Tests agent-as-consumer: verifies the endpoint returns data an autonomous agent could act on
- Include `test_agent_can_determine_hiho_equilibrium`: checks nexus distance < 0.71 (√2/2 max) with correct formula

**Definition of Done:**
- [ ] test_agent_reads_viz_frame_successfully passes
- [ ] test_agent_interprets_routing_tier passes (discriminating — checks winding number mapping)
- [ ] test_agent_can_determine_hiho_equilibrium passes (discriminating — checks nexus distance formula)
- [ ] All existing tests in test_journey_nexus_router.py still pass

**Verify:**
- `uv run pytest tests/api/test_latent_mind_theater_agent.py tests/api/test_journey_nexus_router.py -q`

---

### Task 9: Vault decision log

**Objective:** Log the Latent Mind Theater architectural decision to the vault for cross-session persistence.

**Dependencies:** Task 1 (confirms implementation approach)

**Files:**
- Create: `~/vaults/cohezion-vault/decisions/2026-06-27-latent-mind-theater-3d-agentic-journey-viz-bkt-vortex-hopf.md`

**Definition of Done:**
- [ ] Decision file exists and includes physics rationale, dual-interface design, V-model approach

**Verify:**
- File exists at the vault path
