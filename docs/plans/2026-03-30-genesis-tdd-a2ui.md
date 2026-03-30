# Session Continuation: Genesis TDD Fix + A2UI Protocol Integration

**Date:** 2026-03-30
**Branch:** main
**Active Plan:** ~/.claude/plans/zazzy-snuggling-corbato.md

## What Was Done This Session

### Completed
- [x] Genesis Engine merged to main (2,367 files)
- [x] Application materials (resume, cover letter, tech summary, interview prep)
- [x] Demo quickstart scripts (verified: 50 episodes, 6 metrics, DPO export)
- [x] Webapp hosting via Tailscale Funnel (live)
- [x] SurrealDB plan traceability schema + PlanGraph client
- [x] 3 plan lifecycle hooks (archive, track-files, track-commits)
- [x] Webapp backend fix (port config, router mounts, fallback physics)
- [x] All Genesis tabs populated (thermo, FLUME, swarm, compound, about)
- [x] Cinematic Genesis cosmogony (void, explosion, particles, settling)
- [x] Narration overlay + browser TTS fallback
- [x] Void click target enlarged with ring affordance

### Still Broken (Verified via Playwright)
1. **"CLICK TO BEGIN" overlaps quote text** — both positioned at bottom of void scene
2. **Cosmogony sidebar visible during void** — should be hidden until animation starts
3. **API 404 spam** — `/api/genesis/cosmogony/set-temperature` called repeatedly but endpoint doesn't exist. FIX: remove the API call, local Landau math handles everything
4. **Sound unpleasant** — Tone.js synth parameters too loud/harsh. Need: reduce volumes 10dB, soften attacks, warmer waveforms (sine not sawtooth)
5. **Narration may not display** — overlay has correct code but user reports it's broken. Debug: add console.log to verify narration.currentText is set

### Files to Fix
| File | Issue |
|------|-------|
| `src/web/anima_dashboard/src/components/genesis/GenesisScene.tsx` | VoidQuote overlaps "click to begin" Html; sidebar should hide during void |
| `src/web/anima_dashboard/src/hooks/useCosmogony.ts` | Remove set-temperature API call (causes 404 spam) |
| `src/web/anima_dashboard/src/hooks/useSonification.ts` | Reduce volumes, soften parameters |
| `src/web/anima_dashboard/src/app/genesis/page.tsx` | Verify narration overlay renders |

## Strategic Direction: A2UI + AG-UI Protocol Stack

Full plan at ~/.claude/plans/zazzy-snuggling-corbato.md. Key points:

1. **A2UI**: Define Genesis components as declarative catalog (JSON), making the experience testable by agents
2. **AG-UI**: Replace ad-hoc SSE with typed event streaming
3. **Result**: Cohezion becomes one of first projects implementing MCP + A2A + A2UI + AG-UI (4 of 6 Google agent protocols)

### A2UI Research Needed
- Clone https://github.com/google/A2UI.git
- Study the 18 component primitives
- Map existing React components to A2UI catalog format
- Build renderer bridging A2UI JSON to React Three Fiber

## Services Running
- `cohezion-genesis.service` — Next.js on port 3000 (systemd, enabled)
- `cohezion-api.service` — FastAPI on port 8080 (systemd, enabled)
- Tailscale Funnel — proxying / and /api to the above
- SurrealDB — ports 8000/8001

## Live URLs
- https://frameworkdesktop.tail54eb71.ts.net/
- https://frameworkdesktop.tail54eb71.ts.net/genesis
- https://frameworkdesktop.tail54eb71.ts.net/portfolio
