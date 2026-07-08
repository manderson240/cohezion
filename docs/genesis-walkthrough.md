# Genesis Walkthrough — Vacuum & A2UI

How to explore the two agent-driven Genesis experiences added 2026-07-07, as a
human and as an agent. (Drafted with the local llama3.2-1b lane, corrected by
the orchestrating model.)

## Setup

Backend: `uv run uvicorn cohezion.api:app --port 8080`. CORS allows
`localhost:3000` by default; other frontend ports need
`COHEZION_CORS_ORIGINS=http://localhost:<port>` in the environment.

Frontend: `cd src/web/anima_dashboard && npm run dev`, then open
`http://localhost:3000/genesis`.

## The Vacuum Tab — Latent Mind Theater

Five Three.js components share one canvas: **HopfManifold** (300 Hopf-fibration
fiber loops, iridescence peaks at HIHO coherence 0.5), **JourneyRibbon** (a
spline threading the agent positions), **LatentParticles** (a 50k-particle
thought field centered on the 12D cosmogony state), **QuadratureNexus** (the
I/Q saddle with the HIHO equilibrium ring), and **VacuumFog** (raymarched
16×16×16 density volume).

Every 2 seconds the page advances the live simulation (`POST
/api/universe/tick`) and fetches two payloads: `GET /api/journey-nexus/frame`
— a VizFrame carrying all 8 EVO agents' evolving 12D latent vectors projected
to 3D, their vacuum-topology winding numbers (instanton = +1, trivial = 0,
soliton = −1), the 16³ vacuum density field, the nexus I/Q quadrature
(I = mean coherence, Q = topological diversity), and the MHD ripple phase —
and `GET /api/genesis/cosmogony/12d-state` for the particle-field center.

Both payloads are Zod-validated at the fetch boundary. The badge in the top
left is honest: **LIVE** (tick and poll counters advancing), **SCHEMA
REJECTED** (payload failed validation; last good frame kept), or **API
OFFLINE**. The right-hand HUD shows the exact values driving the scene. In a
browser without WebGL you get a clean fallback panel and the HUD stays live.

## The A2UI Tab — Agent-Driven Cosmogony

This tab renders the declarative experience script
`src/a2ui/experiences/genesis-cosmogony.json` through `A2UIRenderer` — the
same JSON an agent could generate or rewrite. Nothing in it is decorative:

- The state panel polls the real cosmogony engine
  (`GET /api/genesis/cosmogony/state`).
- The temperature slider commands that engine
  (`POST /api/genesis/cosmogony/set-temperature` replays symmetry transitions;
  the next poll reflects the result).
- Each symmetry transition is narrated on the fly by a local GAIA-tier agent
  (`POST /api/gaia/narrate`, llama3.2-1b-FLM on the NPU lane through the
  :13305 Lemonade router). The badge under the narration says whether you are
  reading real agent output (`gaia-local`) or the canned fallback.
- `GET /api/gaia/status` reports tier readiness honestly (probes, not
  assumptions).

Tour: click the pulsing void sphere; the scene machine advances through
explosion → fabric-differentiation → settling → hiho on its scripted timings.
The slider appears in the hiho scene.

## For Agents

The "A2UI inspection state" panel exposes exactly what an agent consumes:
`currentScene`, `activeComponents` (with resolved props), and the live
`dataModel`. Server-side streams:

- `GET /api/journey-nexus/stream/viz?max_frames=N` — SSE VizFrames; each frame
  advances the simulation one tick.
- `GET /api/agui/stream` — typed AG-UI events (state snapshots/deltas,
  narration text, symmetry-breaking tool calls).

## Verifying

From `src/web/anima_dashboard`:

- `node scripts/vacuum-verify.mjs` — drives the Vacuum tab in a real browser,
  saves screenshots, samples real FPS for 10 s (needs a machine with working
  WebGL — GPU-less containers show the fallback).
- `node scripts/a2ui-verify.mjs` — proves the A2UI loop end to end: badges,
  gaia-local narration, scene progression, slider → engine → poll round-trip.
- `npx tsx scripts/zod-reject-check.mts` — proves the fetch boundary rejects
  malformed VizFrames (5 mutation cases) and accepts the live payload.
