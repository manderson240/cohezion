# Wave D2 Dashboard Mockups

Bloomberg-terminal aesthetic: dark `#07080a` ground, JetBrains Mono numerics, Major Mono Display
wordmarks, hairline borders, no rounded corners, no shadows except on live numerics, scanline
overlay, tier accent cyan/amber/magenta, marquee sub-bar, blinking cursor, panel tags `X.NN`.

All five files are self-contained: React 18 + Recharts + Tailwind via CDN, single inline `<style>`
block, single Babel-transformed React component tree. No external API calls, no build step
required — open in a browser to view.

## Mockup Catalog

| File | Description | Suggested Integration Target | Priority |
|---|---|---|---|
| `cost-router-status.html` | Cost-aware-router status: tier distribution, budget enforcer MTD, NPU hit-rate trend, model fleet table, live route log. | `src/web/anima_dashboard/src/app/router/page.tsx` (new route) | P0 — strongest ops surface, replaces ad-hoc terminal `cz` polling |
| `journey-tracker-12d.html` | JourneyTracker 12D agent state: SVG radar chart, dimension residuals vs target, SurrealDB connection card, 200-tick coherence trace with HIHO 0.50 reference, checkpoint table with rollback buttons, last-50 state-transition log. | `src/web/anima_dashboard/src/app/genesis/page.tsx` (extend existing) — add as fifth Genesis tab | P1 — exposes the 12D state vector that JourneyTracker writes to SurrealDB |
| `swarm-topology.html` | Multi-agent swarm: 1280×600 SVG canvas with 17 agent nodes across 5 cluster groups (vault/platform/mcp/data/coord), animated dashed edges for active inter-agent messages, queue-depth pip on each node, click-to-inspect side panel showing last 5 messages, agent metrics table. | `src/web/anima_dashboard/src/app/swarm/page.tsx` (new route) | P1 — visualizes the 7 specialist agents the platform-coordinator routes through |
| `flume-latent-explorer.html` | FLUME VAE 256D latent space: 320-point SVG t-SNE scatter with cyan→magenta loss colormap, encode/decode mode toggle, round-trip inspector showing input text + 16-dim latent bars + reconstructed text + loss percentile, 30-bucket loss histogram with cluster breakdown, top-k=5 cosine-neighbor table. | `src/web/anima_dashboard/src/app/genesis/page.tsx` — replace/extend the existing FlumeLatentViz component | P2 — research-facing, depends on FLUME VAE encode/decode endpoint being exposed |
| `compound-loop-traces.html` | CompoundExecutor trace viewer: header KPIs (today's exec count, avg latency, success rate, P95), filter chips (success/error/by-tier), 30-row trace log table with expandable per-row 11-step waterfall (QV → ET → LT → EP → SR → QC → PS → AC → MT → DD → JT), per-step pipeline-health side panel with sparkline + avg + p95. | `src/web/anima_dashboard/src/app/compound/page.tsx` (new route) | P0 — exposes the CompoundExecutor pipeline that runs every Cohezion request; debugging gold |

## Design Token Inheritance (all 5 files)

```
--bg-0: #07080a    --ink:   #e7ecf3    --cyan:    #5cf2e8   (tier simple)
--bg-1: #0b0d10    --ink-2: #aab3c2    --amber:   #f5b53c   (tier medium / warn)
--bg-2: #0f1216    --ink-3: #6e7787    --magenta: #ff4fbf   (tier hard)
--bg-3: #131822    --ink-4: #4a5260    --green:   #5cff9e   (healthy)
--rule: #20283a                        --red:     #ff5d5d   (error)
--rule-soft: #141a25                   --violet:  #9f7bff   (coord cluster)
```

Fonts: `JetBrains Mono` (body, numerics, code), `Major Mono Display` (wordmark only).

## Local Preview

```bash
cd research/mockups && python3 -m http.server 8765
# then http://localhost:8765/cost-router-status.html  etc.
```

No build step. No npm install. No backend.

## Integration Notes

- **Stack alignment**: Mockups use plain React 18 + Recharts via UMD. The dashboard is Next.js
  16 with TypeScript + Tailwind. To port: extract the JSX from each mockup's `App()` and Recharts
  components, replace inline `var(--*)` with Tailwind theme tokens (or keep CSS variables in
  `globals.css`), promote the per-mockup `MOCK DATA` block to a typed module under
  `src/lib/mockData/` until the live API endpoint exists.
- **Live data sources** (when wiring real data):
  - `cost-router-status.html` → `CostAwareRouter.get_metrics_snapshot()`
  - `journey-tracker-12d.html` → `JourneyTracker.get_journey(agent_id)` + SurrealDB live query
  - `swarm-topology.html` → `TeamOrchestrator.get_topology()` + `SendMessage` event stream
  - `flume-latent-explorer.html` → `/api/flume/embed` + a 2D-projection cache
  - `compound-loop-traces.html` → `CompoundExecutor` ExecutionTraces (Meta-Harness L225) +
    `MetricsCollector.get_metrics_snapshot()`
- **AG-UI streaming**: All five surfaces are read-mostly and would benefit from AG-UI typed SSE
  events (`/api/agui/stream`) rather than polling. The trace viewer in particular wants
  per-trace events, not 1s polling.
- **Cost router was Wave D1**, the other four are Wave D2.
