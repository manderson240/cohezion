# Fable 5 Run — 2026-07-07 — Genesis Unification (wiring job)

Branch: `worktree-imperative-wondering-kettle`. Started 20:52 UTC.

## Scope
1. Wire `components/vacuum/*` into Genesis with real API data + Zod
2. Wire `genesis-cosmogony.json` via A2UIRenderer, real GAIA-tier agents
3. Measure + improve FPS (numbers)
4. Optional: embedded Lemonade (real-prompt-verified) + static generated assets
5. Optional: :13305 hang diagnosis + genesis walkthrough doc

## Infra status
- Vault check: `vault_find_relevant_context` on EVO/vacuum/A2UI/GAIA/genesis → **no prior context found** (verified 20:52 UTC).
- SurrealDB watcher: `surrealdb_start_watching` returned success; wrote test note
  `cerebellum/fable5-run-20260707-watcher-check.md`; **NOT yet visible in SurrealDB**
  (queried `neuron`, `vault_neuron`, `vault_memory` for 'fable5' — 0 rows at 20:54 UTC).
  Will re-query later; until then, claims of "saved to SurrealDB" are NOT justified — vault
  markdown file writes are confirmed, SurrealDB indexing is unconfirmed.
- Pre-existing worktree churn: many staged/unstaged files not mine (incl. staged `.mypy_cache`,
  `htmlcov`). All commits this run enumerate paths explicitly.

## Item status
| Item | Status | Evidence |
|---|---|---|
| 1 vacuum wiring | DONE (env-limited pixels) — verifier: PASS-WITH-CAVEATS | see Item 1 section |
| 2 A2UI cosmogony | DONE | see Item 2 section |
| 3 FPS | PARTIAL: real leak fixes committed; numbers env-blocked | see Item 3 section |
| 4 lemonade embed/assets | SKIPPED (budget; user flagged 81% usage) — punch list | — |
| 5a :13305 hang diagnosis | PARTIAL (evidence, no root cause) | see Item 5 section |
| 5b walkthrough doc | DONE | docs/genesis-walkthrough.md |

## Item 1 verifier verdict (fresh-context subagent)
PASS-WITH-CAVEATS. All 6 checks independently re-run and confirmed (19/19 tests;
live tick 31→32; exactly the 2 allowed pre-existing tsc errors; 5/5 Zod rejections;
screenshots visually inspected and consistent with PROGRESS claims; genesis wiring
present). Caveats: no 3D pixels ever rendered (GPU-less container, disclosed);
:8082 provenance inferred from contract, not proven.

## Item 2 — A2UI cosmogony driven by real GAIA agents (DONE)
Backend: /api/gaia/status + /api/gaia/narrate (routes/gaia.py) — first API exposure of
gaia_adapter; narration by build_gaia_llm_tier(llama3.2-1b-FLM) via :13305, 30s timeout,
honest `source: gaia-local | fallback` field. Frontend: new Genesis "A2UI" tab renders
genesis-cosmogony.json via A2UIRenderer with additive liveDataModel prop; bindings
upgraded from placeholders to live renderers; CosmogonyExperience polls the REAL
cosmogony engine and the slider POSTs set-temperature (note: the pre-existing
useCosmogony.setTemperature computed CLIENT-SIDE Landau math — that decorative path is
bypassed, not used). Verified (a2ui-verify.mjs, headless chromium, all output observed):
ENGINE LIVE badge; GAIA TIER READY; narration source=gaia-local (real model output,
~6.6s latency); scene progression void→hiho; slider round-trip → engine returned
T=42.00 · SO(12) · stage 1; all API calls 200; console errors after tab click: 0.
Bug found+fixed during verification: unguarded liveDataModel merge looped through
onInspect (1927 update-depth errors → 0). Also fixed 2 pre-existing tsc errors —
`npx tsc --noEmit` is now completely clean.

## Item 3 — FPS (PARTIAL, env-blocked numbers, real fixes shipped)
This container has no /dev/dri → WebGL impossible in any browser config (exhaustively
tried; see Item 1). Real perf work shipped instead: JourneyRibbon allocated 8
geometries+materials per 2s poll with no disposal (leak) — now shared unit sphere +
memoized materials + disposal; HopfManifold/LatentParticles/VacuumFog now dispose GPU
resources on unmount (tab switches remount → every visit previously leaked the scene).
PUNCH LIST (human, real GPU): `node scripts/vacuum-verify.mjs` → true FPS + visuals.
rAF baseline in GL-less env: 60.0-60.1 (UI thread unloaded — NOT a render measurement).

## Item 5a — :13305 "hang" RESOLVED + full-fleet parallel recipe (user directive)
Root cause found and verified: the "real prompts hang" is COLD MODEL LOAD exceeding
client timeouts, not a hang. Evidence: E4B real prompt via MCP timed out at 60s; after
explicit `lemonade_load_model(Gemma-4-E4B, vulkan, ctx 16384)` the same class of prompt
answered in ~12s (13 tps). Second trap confirmed: thinking models return EMPTY content
when max_tokens is small (150 tokens all spent on reasoning_content, finish_reason=
length) — use ≥512-600 (harness N5).

**Full-net parallelism verified live (zero config changes)**: one model per backend lane
loaded simultaneously — llama3.2-1b (FLM/NPU) + Gemma-4-E4B (llamacpp/vulkan iGPU) +
Bonsai-8B (llamacpp/cpu) — then 3 concurrent chat requests through :13305:
NPU 3.8s · CPU 15.0s · iGPU 35.8s · TOTAL WALL 35.8s = max, not the 54.6s sum.
All three returned distinct real completions. Recipe persisted to vault decision
`2026-07-08-multi-lane-parallel-local-inference...`. Rule of thumb: NPU=fast/short
tasks, CPU=medium, iGPU=heavy/thinking (with big token budgets); pre-load each lane
once (save_options=true), then fan out concurrently.

## Full API test suite (quality gate, run at end of run)
`uv run pytest tests/api/ -q` → **160 passed, 7 failed, 2 xpassed**. All 7 failures are
in tests/api/test_journey_nexus.py (SERVICE-level tests: JourneyNexus lacks
stream_snapshot/_omni_tier etc.) — PRE-EXISTING: `git diff 3b9cd2bb2 HEAD` shows zero
changes to that service or test file in this run's commits. It is the service-side half
of the same designed-but-unimplemented contract whose router half this run implemented.
Strong candidate for a $0 local-inference session (see punch list).

## Persistence status (honest)
- Vault markdown: 2 decision notes written (2026-07-08-check-the-test-suite-...,
  2026-07-08-a2ui-livedatamodel-...) + watcher-check note + this file. CONFIRMED on disk.
- SurrealDB: NOT synced. Watcher reported "started" at 20:52 UTC but the test note is
  still absent ~3.5h later (vault_neuron count()=1 total). Do NOT claim SurrealDB
  persistence for this run. Punch list: debug the vault MCP file-watcher indexing.
- Memory: quarter-on-a-string-protocol saved to auto-memory + MEMORY.md index.

## Item 1 — vacuum wiring (DONE, commits 3db821e59 + frontend commit)
**Backend**: tests/api/test_journey_nexus_router.py already contained a full designed
contract for /frame ("Latent Mind Theater") that had never been implemented (all /frame
tests 404ing). Implemented it: VizFrame from live UniverseStateService (per-EVO 12D latent
vectors → 3D, vacuum_topology winding numbers, 16³ density field, nexus I/Q = coherence ×
topological diversity, BKT distance, MHD phase, real cache/detector snapshots). Also
/stream/viz + /stream/evo SSE, /omni/{id} (matches AskOmni.tsx), quadrature validation.
Mounted router under /api (was never mounted). **19/19 router tests pass** (was 9/19).
Verified live: positions change after /api/universe/tick → data is real simulation state.

**Frontend**: zod@4.4.3 added; `lib/vacuumSchemas.ts` (VizFrame/12d-state schemas),
`hooks/useVacuumScene.ts` (tick+fetch+validate poll loop), `components/vacuum/VacuumScene.tsx`
(all 5 orphan components composed, WebGL gate, live HUD), JourneyRibbon got additive
`points` prop, new "Vacuum" tab in genesis/page.tsx.

**Verified (headless chromium, real dev servers: API :8082 from this worktree, next :3100)**:
- LIVE badge "tick 11 · poll 2 · Zod OK" → later "tick 18 · poll 9" (live, advancing)
- 9× GET /api/journey-nexus/frame all HTTP 200 (network log)
- Zod: real payload parses; 5/5 malformed variants rejected (scripts/zod-reject-check.mts output)
- Console errors from Vacuum tab: **0** (8 errors on page load are pre-existing GenesisScene
  on the default tab in a GL-less env, verified by before/after-click attribution)
- Screenshots: item1-vacuum-tab-live.png, item1-vacuum-tab-later.png, item1-vacuum-webgl-fallback.png

**Environmental limit (honest)**: this session's container has NO /dev/dri, no Wayland/X
socket, no D-Bus → WebGL cannot initialize in ANY browser config tried (headless chromium
swiftshader/angle/in-process-gpu/single-process, full chromium channel, firefox, headed).
claude-in-chrome extension not connected. Therefore: canvas pixels in screenshots show the
WebGL-unavailable fallback (itself a new, gated, tested state), and **true rendered FPS
could not be measured here** — rAF baseline is 60.0 with UI thread unloaded. Added
`useWebGLSupport` gate so GL-less environments get a clean fallback + live data HUD instead
of console spam. PUNCH LIST: run `node scripts/vacuum-verify.mjs` from src/web/anima_dashboard
on the desktop (real GPU) for true FPS + visual check of the 3D scene.

**CORS note**: API only allowed :3000/:8080 by default; run dev server on :3000 or set
COHEZION_CORS_ORIGINS. My servers: uvicorn :8082 (this worktree code) + next dev :3100 with
NEXT_PUBLIC_API_URL=http://127.0.0.1:8082 and COHEZION_CORS_ORIGINS including :3100.

**Pre-existing issues found (not mine, punch list)**:
- FlumeLatentViz fetches /api/flume/latent-space but backend serves /flume/latent-space (404)
- SwarmTopologyViz fetches /api/swarm/metrics but backend serves /swarm/metrics (404)
- api/journey_status.py router defined but never mounted (useJourneyStatus polls it → 404)
- 2 pre-existing tsc errors: a2ui-demo/page.tsx (ReactNode), CoherenceIndicator.tsx (css prop)
- anima_dashboard CLAUDE.md documents `npm run type-check` — script doesn't exist

## Notes
- All 5 vacuum components read; props: HopfManifold{coherenceScore,tierUsed},
  JourneyRibbon{apiBase='/api/journey-nexus',refreshMs} (self-fetching, typed VizPoint),
  LatentParticles{coherenceScore,dims12d[12]}, QuadratureNexus{nexusI,nexusQ,nexusPower},
  VacuumFog{vacuumField[4096],mhdRipplePhase}.
- JourneyRibbon already expects `/api/journey-nexus/frame` → VizFrame{points:[VizPoint]}.
- Zod not in package.json yet (verified) — installing.
- Explore agent mapping backend API surface (universe/journey/vacuum/GAIA routes).
