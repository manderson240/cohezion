# Compound Identity System Design

**Date:** 2026-03-08
**Status:** APPROVED
**Approach:** Substrate Up (Approach 2)
**Scope:** Full Epic Push (Epics 2+4 — Triune Self, Anima, Media Pipeline)
**FRs Covered:** FR12, FR13, FR14, FR15, FR16, FR17, FR18, FR22

## Problem Statement

The Anima Dashboard displays real HIHO physics (coherence, EVOs, CA grid) but lacks:
- Brand identity (uses Next.js defaults and marimo's favicon)
- The Triune Self navigation (KNOWER/THINKER/DOER modes)
- An in-app assistant (no onboarding, no help, no guide)
- HIHO-reactive UI (coherence value doesn't affect visual presentation)
- Architecture diagrams, voice narration, or persistent homology visualization

The physics engines exist and work. The branding module exists. The MCP knowledge server exists. The TTS service exists. They are disconnected.

## Architecture: Compound Substrate Up

Each layer IS the foundation for the next. Nothing is placeholder.

```
Layer 0: Brand Pipeline ──────── branding.py -> API + CSS + favicon + OG
Layer 1: SSE Universe Stream ─── Master Clock replaces polling
Layer 2: Triune Nav + HIHO CSS ─ 3 modes + coherence-reactive colors
Layer 3: Observatory (KNOWER) ── Existing panels + Re-Entry Narrative + Provenance
Layer 4: Anima Service ───────── Template -> MCP-grounded -> Voice (graceful tiers)
Layer 5: Vault Mode (THINKER) ── Semantic search + Three Pillars + Freeze-Frame
Layer 6: Cockpit Mode (DOER) ── Compound loop viz + architecture diagrams
Layer 7: Persistent Homology ── Topological persistence overlay
```

## Layer 0: Brand Pipeline

**Source of Truth:** `src/cohezion/branding.py` (Colors, Identity, Motifs)

### Brand API
- `GET /api/brand/theme` returns JSON with colors, identity, and motifs
- Consumed by dashboard at runtime for dynamic HIHO color shifting

### Build-Time Pipeline
- `scripts/generate_brand_assets.py` reads `branding.py` and generates:
  - Favicons (16, 32, 192, 512, ICO) from `apps/webapp/src/logo.png` via Pillow
  - OG image (1200x630) with logo + brand colors + version text
  - `brand-tokens.css` with CSS custom properties from Colors class

### Files
| File | Action |
|------|--------|
| `src/cohezion/api/services/brand.py` | New — Brand API endpoint |
| `scripts/generate_brand_assets.py` | New — Favicon + OG + CSS generation |
| `src/web/anima_dashboard/public/cohezion-logo.png` | Copy from apps/webapp |
| `src/web/anima_dashboard/public/cohezion-favicon.ico` | Generated |
| `src/web/anima_dashboard/src/app/layout.tsx` | Edit — metadata, favicon, OG |
| `src/web/anima_dashboard/src/app/globals.css` | Edit — brand token variables |
| `tests/api/test_brand_service.py` | New — TDD |

## Layer 1: SSE Universe Stream (Master Clock)

**Replaces:** `useUniverseState` polling hook (3s interval)
**Enables:** All three Triune modes share one data stream

### Server Side
- Background `asyncio.Task` ticks the `UniverseStateService` at 10 Hz
- Stores last 1000 tick snapshots in a bounded `deque` (for Re-Entry Narrative)
- `GET /api/universe/stream` SSE endpoint broadcasts events

### Event Types
| Event | Payload | Frequency |
|-------|---------|-----------|
| `tick` | `{ tick, coherence, ca_grid, evo_states, time }` | Every tick |
| `report` | `{ hiho_status, ca_analysis, evo_health, summary }` | Every 10th tick |
| `alert` | `{ kind, message }` | When coherence exits 0.3-0.7 |
| `narration` | `{ text, mode, tier }` | On mode change, perturbation, alert |

### Client Side
- `useUniverseStream()` hook with `EventSource` + auto-reconnect
- `UniverseProvider` React Context wraps the app — all modes consume same data
- Existing `POST /tick` stays as manual step button for debugging

### Files
| File | Action |
|------|--------|
| `src/cohezion/api/services/universe.py` | Edit — background tick loop, SSE endpoint, history deque |
| `src/web/anima_dashboard/src/hooks/useUniverseStream.ts` | New — EventSource hook |
| `src/web/anima_dashboard/src/context/UniverseProvider.tsx` | New — React Context |
| `tests/api/test_universe_stream.py` | New — TDD |

## Layer 2: Triune Navigation + HIHO-Reactive CSS Bridge

### Triune Navigation (FR12)
Three distinct cognitive modes with embodied transitions:

| Mode | Label | Content | Transition |
|------|-------|---------|------------|
| KNOWER | Observatory | Physics panels, Re-Entry Narrative | Fade + scale (400ms) |
| THINKER | Vault | Semantic search, Three Pillars | Slide-left + blur (600ms) |
| DOER | Cockpit | Compound loop, architecture diagrams | Slide-up + iris (800ms) |

Transitions slow down as modes deepen (NFR12: ritualized cognitive shift).

### HIHO-Reactive CSS Bridge (FR14)
Coherence value from SSE stream drives CSS custom properties every tick:

```
coherence 0.0-0.3   -> CRITICAL (reds, fast pulse, high particle density)
coherence 0.3-0.45  -> WARNING (golds, medium density)
coherence 0.45-0.55 -> STABLE (greens, calm — HIHO sweet spot)
coherence 0.55-0.7  -> WARNING (golds -> blues)
coherence 0.7-1.0   -> CRITICAL (deep blues/purples, rigid)
```

CSS variables set on `<html>` element:
- `--hiho-hue`, `--hiho-saturation`, `--hiho-pulse-speed`
- `--hiho-glow-color`, `--hiho-particle-density`

Every component inherits the mood without knowing about HIHO.

### Anima Sigil (Visual Presence)
- Breathing indicator in header — stylized "C" from brand logo
- Pulses at HIHO-reactive speed
- Click to expand Anima narration panel
- States: online / template-mode / offline

### Files
| File | Action |
|------|--------|
| `src/web/anima_dashboard/src/app/page.tsx` | Rewrite — Triune shell |
| `src/web/anima_dashboard/src/components/TriuneNav.tsx` | New — Header + tabs + Anima Sigil |
| `src/web/anima_dashboard/src/components/HIHOBridge.tsx` | New — Coherence -> CSS variables |
| `src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx` | New — Template narration |
| `src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx` | New — KNOWER wrapper |
| `src/web/anima_dashboard/src/components/modes/VaultMode.tsx` | New — THINKER shell |
| `src/web/anima_dashboard/src/components/modes/CockpitMode.tsx` | New — DOER shell |
| `src/web/anima_dashboard/src/app/globals.css` | Edit — HIHO variables + transitions |

## Layer 3: Observatory Mode (KNOWER)

### Re-Entry Narrative (FR13)
On first load, Anima summarizes recent history from the tick deque:
> "Welcome back. While you were away, 847 ticks elapsed. Coherence held stable at 0.51 +/- 0.03. One coherence spike event was detected and recovered in 23 ticks. CA density settled at 33.6%."

Generated from deque history — no model needed.

### Provenance Tags (FR16)
Every data point carries a hover tooltip showing its source:
- Coherence: "HIHOStabilizationEngine.apply_hiho_loop() -> EvoState.coherence"
- CA Grid: "CellularAutomataEngine.evolve() -> Rule 30, 256 cells"
- Helicity: "MagnetohydrodynamicsEngine.apply_mhd_forces() -> rotation matrix"

### Layout
Existing panels reorganized into a grid:
- Top: OuroborosControlRoom (coherence + EVO telemetry)
- Middle: TensorBeam (3D visualization) | SnapshotGallery (CA heatmap)
- Bottom: Perturbation controls | Synthesis report panel

### Files
| File | Action |
|------|--------|
| `src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx` | Fill — grid layout |
| `src/web/anima_dashboard/src/components/ReEntryNarrative.tsx` | New — history summary |
| `src/web/anima_dashboard/src/components/ProvenanceTag.tsx` | New — hover tooltip |
| `src/cohezion/api/services/universe.py` | Edit — GET /api/universe/history endpoint |

## Layer 4: Anima Service

Three-tier graceful degradation:

### Tier 1: Template Narration (always works)
Formats `SynthesisReport` data into natural language using Python string templates.
No dependencies. Generates narration events on the SSE stream.

### Tier 2: MCP-Grounded Intelligence (requires Knowledge MCP)
Routes user questions to `KnowledgeMCP` (port 8371) for skill/vault lookups.
User asks "What is HIHO?" -> searches skills -> returns grounded answer.
Falls back to Tier 1 if MCP unavailable.

### Tier 3: Voice Synthesis (requires pocket-tts model)
Pipes Tier 1/2 text through `PocketTTSService` for audio.
Returns base64 WAV. Dashboard plays via Web Audio API.
Falls back to Tier 2 (text only) if model not installed.

### API
- `GET /api/anima/status` — current tier, online state
- `POST /api/anima/narrate` — generate narration for current state
- `POST /api/anima/ask` — ask a question (routed through MCP)
- `POST /api/anima/speak` — synthesize text to audio

### Frontend
- `AnimaChatPanel.tsx` — expandable chat interface in Anima Sigil
- User can type questions, get MCP-grounded answers
- Narration bar shows latest template narration (auto-updating)

### Files
| File | Action |
|------|--------|
| `src/cohezion/api/services/anima.py` | New — Anima service (3 tiers) |
| `src/web/anima_dashboard/src/components/AnimaChatPanel.tsx` | New — chat UI |
| `src/web/anima_dashboard/src/hooks/useAnima.ts` | New — Anima API hook |
| `tests/api/test_anima_service.py` | New — TDD for all 3 tiers |

## Layer 5: Vault Mode (THINKER)

### Semantic Search UI (FR17)
- Search bar with natural language input
- Queries `KnowledgeMCP.search_knowledge()` across Three Pillars
- Results show: title, excerpt, pillar type (Decision/Experiment/Pattern), relevance score
- Each result has a ProvenanceTag (FR16)

### Freeze-Frame Capture
- Button to snapshot current universe state
- Saves as a vault Decision with: tick, coherence, EVO states, CA grid, user annotation
- Stored via `/api/anima/ask` with intent "save decision"

### Files
| File | Action |
|------|--------|
| `src/web/anima_dashboard/src/components/modes/VaultMode.tsx` | Fill — search UI |
| `src/web/anima_dashboard/src/components/VaultSearchResult.tsx` | New — result card |
| `src/web/anima_dashboard/src/components/FreezeFrame.tsx` | New — snapshot capture |
| `src/cohezion/api/services/anima.py` | Edit — vault query routing |

## Layer 6: Cockpit Mode (DOER)

### Compound Loop Visualization (FR18)
Five-phase ring visualization:
EXPANDING -> PLANNING -> EXECUTING -> REFLECTING -> REFINING
Current phase highlighted. Historical cycles shown as concentric rings.

### Architecture Diagrams
- Extend `gen_arch.py` to output JSON (nodes + edges) consumed by dashboard
- `GET /api/architecture/graph` serves the live architecture graph
- Rendered as an interactive force-directed graph in the Cockpit

### Skill Diffs
- Show before/after when skills are refined
- Sourced from skill registry changes

### Files
| File | Action |
|------|--------|
| `src/web/anima_dashboard/src/components/modes/CockpitMode.tsx` | Fill — loop viz + graph |
| `src/web/anima_dashboard/src/components/CompoundLoopViz.tsx` | New — phase ring |
| `src/web/anima_dashboard/src/components/ArchitectureGraph.tsx` | New — force graph |
| `src/cohezion/api/services/architecture.py` | New — graph API |
| `tests/api/test_architecture_service.py` | New — TDD |

## Layer 7: Persistent Homology Overlay

### Topological Persistence (FR22)
- Overlay on Observatory showing which 12D features persist vs. are transient
- Renders as a persistence diagram (birth vs. death scatter plot)
- Uses existing `src/cohezion/compound/topological_persistence.py`
- Updated every 10th tick via the SSE `report` event

### Files
| File | Action |
|------|--------|
| `src/web/anima_dashboard/src/components/PersistenceDiagram.tsx` | New — scatter plot |
| `src/cohezion/api/services/universe.py` | Edit — add topology data to report |

## Compounding Matrix

| Layer | Consumes From | Provides To |
|-------|--------------|-------------|
| 0 (Brand) | `branding.py` | 2 (HIHO palette), layout.tsx, favicon, OG |
| 1 (SSE) | Universe service | 2 (coherence), 3 (all panels), 4 (narration trigger) |
| 2 (Triune) | 0 (colors), 1 (coherence) | 3-6 (mode containers), 4 (Anima bar) |
| 3 (Observatory) | 1 (stream), 2 (container) | User observes universe |
| 4 (Anima) | 1 (state), Knowledge MCP, pocket-tts | 3 (narration), 5 (vault answers) |
| 5 (Vault) | 4 (MCP routing), 2 (container) | 6 (skill data for diffs) |
| 6 (Cockpit) | 5 (skill data), gen_arch.py | User acts on universe |
| 7 (Homology) | 1 (stream), topological_persistence.py | 3 (overlay) |

## Total File Count

- **New files:** ~22
- **Modified files:** ~6
- **Tests:** ~5 new test files
- **Multi-session:** Yes (Layers 0-3 in session 1, Layers 4-7 in session 2+)
