# Anima Dashboard — Local Context

TypeScript / Next.js 16 / Three.js / Tone.js frontend. Root `CLAUDE.md` applies for architecture
and design principles, but most Python-specific content (pytest, uv, SurrealDB, inference ports)
does not apply here.

## Stack at a Glance

- **Framework**: Next.js 16 (App Router)
- **3D / canvas**: Three.js via `@react-three/fiber` + `@react-three/drei`
- **Audio**: Tone.js
- **State**: React hooks; server state via SSE (AG-UI events from :8080)
- **Entry**: `src/web/anima_dashboard/`; dev server: `npm run dev` (inside this dir)

## NEVER Run Here

```bash
# WRONG — Python tooling does not apply inside src/web/
uv run ...
pytest ...
python ...
```

```bash
# RIGHT — use npm / next
cd src/web/anima_dashboard
npm run dev        # dev server
npm run build      # production build
npm run lint       # eslint
npm run type-check # tsc --noEmit
```

## A2UI Component Catalog (9 declared)

| Component | File | Purpose |
|-----------|------|---------|
| `BlochSphere` | `a2ui/BlochSphere.tsx` | SU(2) spinor state visualization |
| `GenesisScene` | `a2ui/GenesisScene.tsx` | 3D cosmogony chain |
| `FlumeLatentViz` | `a2ui/FlumeLatentViz.tsx` | 256D FLUME VAE trajectory |
| `SwarmTopologyViz` | `a2ui/SwarmTopologyViz.tsx` | Multi-agent graph |
| `SkillMatrix` | `a2ui/SkillMatrix.tsx` | 235-skill heatmap |
| `JourneyPlayer` | `a2ui/JourneyPlayer.tsx` | Compound loop replay |
| `CostDashboard` | `a2ui/CostDashboard.tsx` | Token budget / tier usage |
| `DegradationPanel` | `a2ui/DegradationPanel.tsx` | Health alerts timeline |
| `WorldviewExplorer` | `a2ui/WorldviewExplorer.tsx` | 16-tradition cosmogony grid |

## AG-UI SSE Event Types (:8080/api/agui/stream)

15+ typed events — key ones for new components:

| Event type | Payload fields | When fired |
|------------|---------------|------------|
| `SKILL_REFINED` | `skill_name, confidence, tier_used` | After SkillRefiner writes |
| `DEGRADATION_ALERT` | `metric, severity, suggested_tier` | DegradationDetector fires |
| `JOURNEY_STEP` | `position_12d, vacuum_label, potential` | Each TrajectoryPoint |
| `JEPA_COHERENCE` | `coherence, verdict` | JepaGate.check() |
| `TIER_ESCALATION` | `from_tier, to_tier, reason` | TieredOrchestrator escalates |

Consume via: `EventSource('/api/agui/stream')` — `onmessage` receives `{type, data, timestamp}`.

## Route Layout

- `/genesis` — primary 8-tab dashboard (BlochSphere, GenesisScene, …)
- `/api/agui/stream` — SSE feed (read-only, never POST here from the frontend)
- `/api/compound/health` — JSON health endpoint for DegradationPanel

## TypeScript Rules

- Strict mode is on (`tsconfig.json` strict: true)
- No `any` without a `// allow-any: <reason>` comment
- Three.js objects: always dispose in `useEffect` cleanup to prevent GPU leak
- AG-UI event handlers must be typed against `AgUiEvent` union type in `src/cohezion/api/agui_events.py` (keep in sync)
