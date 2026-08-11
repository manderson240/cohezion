# Compound Identity System Implementation Plan

> **For Claude:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Build the Triune Self (KNOWER/THINKER/DOER) navigation, Anima Sigil voice, brand pipeline, HIHO-reactive CSS, and full media system using compound substrate-up architecture.

**Architecture:** 8 layers built substrate-up. Each layer IS the foundation for the next. Layer 0 (brand) feeds Layer 2 (HIHO colors). Layer 1 (SSE) feeds all modes. Layer 4 (Anima) serves all three Triune modes. Nothing is placeholder or throwaway.

**Tech Stack:** Python 3.13 (FastAPI, Pydantic, asyncio), TypeScript (Next.js 16, React 19, React Three Fiber), Tailwind v4, SSE (Server-Sent Events), Pillow (image gen), pocket-tts (voice)

**Design Doc:** `docs/plans/2026-03-08-compound-identity-system-design.md`

**FRs:** FR12 (Triune Navigation), FR13 (Re-Entry Narrative), FR14 (HIHO-Reactive UI), FR15 (Anima Sigil), FR16 (Provenance Tags), FR17 (Semantic Vault Search), FR18 (Loop Visualization), FR22 (Persistent Homology)

Status: PENDING
Approved: No
Worktree: Yes

---

## Task 1: Brand API Service (Layer 0 — Backend)

**Files:**
- Create: `src/cohezion/api/services/brand.py`
- Create: `tests/api/test_brand_service.py`
- Modify: `src/cohezion/api/__init__.py` (line ~19, add router import and mount)

**Step 1: Write the failing test**

Create `tests/api/test_brand_service.py`:

```python
"""Tests for the Brand API service."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI
    from cohezion.api.services.brand import brand_router

    app = FastAPI()
    app.include_router(brand_router, prefix="/api/brand")
    return TestClient(app)


class TestBrandThemeEndpoint:
    def test_get_theme_returns_200(self, client: TestClient) -> None:
        resp = client.get("/api/brand/theme")
        assert resp.status_code == 200

    def test_theme_has_colors(self, client: TestClient) -> None:
        data = client.get("/api/brand/theme").json()
        assert "colors" in data
        assert data["colors"]["nexus_green"] == "#00FF00"
        assert data["colors"]["matte_black"] == "#0A0A0A"
        assert data["colors"]["earth_blue"] == "#0077BE"

    def test_theme_has_identity(self, client: TestClient) -> None:
        data = client.get("/api/brand/theme").json()
        assert "identity" in data
        assert data["identity"]["name"] == "COHEZION"
        assert data["identity"]["tagline"] == "The Nexus of Coherence"

    def test_theme_has_hiho_palette(self, client: TestClient) -> None:
        """HIHO palette maps coherence zones to colors for the CSS bridge."""
        data = client.get("/api/brand/theme").json()
        assert "hiho_palette" in data
        palette = data["hiho_palette"]
        assert "critical_low" in palette
        assert "warning" in palette
        assert "stable" in palette
        assert "critical_high" in palette
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mike-anderson/dev/cohezion && uv run pytest tests/api/test_brand_service.py -q`
Expected: FAIL — `ModuleNotFoundError: No module named 'cohezion.api.services.brand'`

**Step 3: Write minimal implementation**

Create `src/cohezion/api/services/brand.py`:

```python
"""Brand API Service.

Single source of truth for Cohezion identity, derived from branding.py.
Serves the canonical theme for the Anima Dashboard including the
HIHO-reactive color palette used by the CSS bridge.
"""

from __future__ import annotations

from fastapi import APIRouter
from pydantic import BaseModel

from cohezion.branding import Colors, Identity

brand_router = APIRouter(tags=["brand"])


class HIHOPalette(BaseModel):
    critical_low: str
    warning: str
    stable: str
    critical_high: str


class BrandColors(BaseModel):
    nexus_green: str
    matte_black: str
    silicon_silver: str
    earth_blue: str
    critical_red: str
    warning_gold: str
    plasma_blue: str
    neon_cyan: str


class BrandIdentity(BaseModel):
    name: str
    tagline: str
    philosophy: str
    sign_off: str


class BrandThemeResponse(BaseModel):
    colors: BrandColors
    identity: BrandIdentity
    hiho_palette: HIHOPalette


@brand_router.get("/theme", response_model=BrandThemeResponse)
async def get_brand_theme() -> BrandThemeResponse:
    """Return the canonical Cohezion brand theme."""
    return BrandThemeResponse(
        colors=BrandColors(
            nexus_green=Colors.NEXUS_GREEN,
            matte_black=Colors.MATTE_BLACK,
            silicon_silver=Colors.SILICON_SILVER,
            earth_blue=Colors.EARTH_BLUE,
            critical_red=Colors.CRITICAL_RED,
            warning_gold=Colors.WARNING_GOLD,
            plasma_blue=Colors.PLASMA_BLUE,
            neon_cyan=Colors.NEON_CYAN,
        ),
        identity=BrandIdentity(
            name=Identity.NAME,
            tagline=Identity.TAGLINE,
            philosophy=Identity.PHILOSOPHY,
            sign_off=Identity.SIGN_OFF,
        ),
        hiho_palette=HIHOPalette(
            critical_low=Colors.CRITICAL_RED,
            warning=Colors.WARNING_GOLD,
            stable=Colors.NEXUS_GREEN,
            critical_high=Colors.EARTH_BLUE,
        ),
    )
```

**Step 4: Run test to verify it passes**

Run: `cd /home/mike-anderson/dev/cohezion && uv run pytest tests/api/test_brand_service.py -q`
Expected: 4 passed

**Step 5: Mount router in main app**

Edit `src/cohezion/api/__init__.py`: Add `from cohezion.api.services.brand import brand_router` near the universe_router import, and `app.include_router(brand_router, prefix="/api/brand")` near the universe_router mount.

**Step 6: Commit**

---

## Task 2: Brand Asset Pipeline (Layer 0 — Build Tools)

**Files:**
- Create: `scripts/generate_brand_assets.py`
- Copy: `apps/webapp/src/logo.png` -> `src/web/anima_dashboard/public/cohezion-logo.png`

**Step 1: Copy the real logo to the dashboard**

Run: `cp apps/webapp/src/logo.png src/web/anima_dashboard/public/cohezion-logo.png`

**Step 2: Write the asset generation script**

Create `scripts/generate_brand_assets.py` that:
- Reads `apps/webapp/src/logo.png`
- Uses Pillow to generate favicon sizes (16, 32, 192, 512) + ICO
- Generates `brand-tokens.css` from `cohezion.branding.Colors`
- Outputs to `src/web/anima_dashboard/public/`

```python
"""Generate brand assets from branding.py single source of truth.

Produces: favicons, CSS custom properties, OG image placeholder.
Run: uv run python scripts/generate_brand_assets.py
"""

from __future__ import annotations

import logging
from pathlib import Path

from PIL import Image

from cohezion.branding import Colors

logger = logging.getLogger(__name__)

PROJECT_ROOT = Path(__file__).resolve().parents[1]
LOGO_SRC = PROJECT_ROOT / "apps" / "webapp" / "src" / "logo.png"
PUBLIC_DIR = PROJECT_ROOT / "src" / "web" / "anima_dashboard" / "public"


def generate_favicons() -> None:
    """Resize logo to standard favicon sizes and generate ICO."""
    img = Image.open(LOGO_SRC)
    sizes = {
        "favicon-16x16.png": 16,
        "favicon-32x32.png": 32,
        "android-chrome-192x192.png": 192,
        "android-chrome-512x512.png": 512,
    }
    for name, size in sizes.items():
        resized = img.resize((size, size), Image.Resampling.LANCZOS)
        resized.save(PUBLIC_DIR / name)
        logger.info("Generated %s", name)

    # ICO with multiple sizes
    ico_img = img.resize((256, 256), Image.Resampling.LANCZOS)
    ico_img.save(
        PUBLIC_DIR / "cohezion-favicon.ico",
        format="ICO",
        sizes=[(16, 16), (32, 32), (48, 48), (256, 256)],
    )
    logger.info("Generated cohezion-favicon.ico")


def generate_css_tokens() -> None:
    """Emit CSS custom properties from Colors class."""
    tokens = []
    for attr in dir(Colors):
        if attr.startswith("_"):
            continue
        value = getattr(Colors, attr)
        if isinstance(value, str) and value.startswith("#"):
            css_name = attr.lower().replace("_", "-")
            tokens.append(f"  --color-{css_name}: {value};")

    css = ":root {\n" + "\n".join(sorted(tokens)) + "\n}\n"
    out = PUBLIC_DIR / "brand-tokens.css"
    out.write_text(css)
    logger.info("Generated brand-tokens.css with %d tokens", len(tokens))


def main() -> None:
    logging.basicConfig(level=logging.INFO)
    PUBLIC_DIR.mkdir(parents=True, exist_ok=True)
    generate_favicons()
    generate_css_tokens()
    logger.info("Brand asset pipeline complete.")


if __name__ == "__main__":
    main()
```

**Step 3: Run the pipeline**

Run: `cd /home/mike-anderson/dev/cohezion && uv run python scripts/generate_brand_assets.py`
Expected: Favicon PNGs + ICO + brand-tokens.css generated in `src/web/anima_dashboard/public/`

**Step 4: Update layout.tsx**

Edit `src/web/anima_dashboard/src/app/layout.tsx`:
- Change metadata title to `"COHEZION — The Nexus of Coherence"`
- Change description to `"12D Agentic Universe with HIHO Physics"`
- Add favicon link, OG tags

**Step 5: Update globals.css**

Edit `src/web/anima_dashboard/src/app/globals.css`:
- Import brand-tokens.css: `@import url('/brand-tokens.css');` at the top (after tailwind)
- Replace `--background: #0a0a0a` with `--background: var(--color-matte-black)`
- Add HIHO-reactive variable placeholders

**Step 6: Commit**

---

## Task 3: SSE Universe Stream (Layer 1 — Backend)

**Files:**
- Modify: `src/cohezion/api/services/universe.py`
- Create: `tests/api/test_universe_stream.py`

**Step 1: Write the failing test**

Create `tests/api/test_universe_stream.py`:

```python
"""Tests for SSE universe stream (Master Clock)."""

import json

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.universe import (
    UniverseStateService,
    universe_router,
)


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(universe_router, prefix="/api/universe")
    return TestClient(app)


class TestUniverseHistory:
    def test_service_stores_tick_history(self) -> None:
        svc = UniverseStateService(num_evos=4)
        for _ in range(5):
            svc.tick()
        history = svc.get_history(limit=3)
        assert len(history) == 3
        assert history[-1].tick == 5

    def test_history_bounded_to_max(self) -> None:
        svc = UniverseStateService(num_evos=2)
        svc._max_history = 10  # Override for test speed
        for _ in range(15):
            svc.tick()
        assert len(svc._history) == 10

    def test_history_endpoint_returns_json(self, client: TestClient) -> None:
        client.post("/api/universe/tick")
        client.post("/api/universe/tick")
        resp = client.get("/api/universe/history?limit=2")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 2


class TestSSEStream:
    def test_stream_endpoint_returns_sse(self, client: TestClient) -> None:
        """SSE endpoint returns event stream content type."""
        with client.stream("GET", "/api/universe/stream?max_ticks=3") as resp:
            assert resp.status_code == 200
            assert "text/event-stream" in resp.headers.get("content-type", "")
            events = []
            for line in resp.iter_lines():
                if line.startswith("data: "):
                    events.append(json.loads(line[6:]))
                if len(events) >= 3:
                    break
        assert len(events) >= 1
        assert "tick" in events[0]
        assert "coherence" in events[0]
```

**Step 2: Run test to verify it fails**

Run: `cd /home/mike-anderson/dev/cohezion && uv run pytest tests/api/test_universe_stream.py -q`
Expected: FAIL — `get_history` and `/stream` don't exist

**Step 3: Implement SSE stream + history**

Edit `src/cohezion/api/services/universe.py` to add:
1. `collections.deque` for tick history (max 1000)
2. `get_history(limit)` method
3. `GET /api/universe/history` endpoint
4. `GET /api/universe/stream` SSE endpoint that ticks and yields events
5. The SSE endpoint accepts `max_ticks` query param (for testing; omit for infinite)

Key implementation details:
- `tick()` method appends to `self._history` deque after each tick
- SSE endpoint uses `StreamingResponse` with `text/event-stream` media type
- Every tick yields `event: tick\ndata: {json}\n\n`
- Every 10th tick yields `event: report\ndata: {report_json}\n\n`
- Alert events when coherence exits [0.3, 0.7]

**Step 4: Run test to verify it passes**

Run: `cd /home/mike-anderson/dev/cohezion && uv run pytest tests/api/test_universe_stream.py -q`
Expected: All passed

**Step 5: Commit**

---

## Task 4: Universe Context Provider (Layer 1 — Frontend)

**Files:**
- Create: `src/web/anima_dashboard/src/hooks/useUniverseStream.ts`
- Create: `src/web/anima_dashboard/src/context/UniverseProvider.tsx`

**Step 1: Create the SSE hook**

Create `src/web/anima_dashboard/src/hooks/useUniverseStream.ts`:
- Uses `EventSource` to connect to `/api/universe/stream`
- Parses `tick`, `report`, `alert`, `narration` event types
- Auto-reconnects on disconnect (exponential backoff, max 30s)
- Returns `{ state, report, alerts, connected, error }`
- Exports `UniverseState`, `EvoState`, `SynthesisReport` interfaces (moved from useUniverseState.ts)

**Step 2: Create the Context Provider**

Create `src/web/anima_dashboard/src/context/UniverseProvider.tsx`:
- Wraps `useUniverseStream` in a React Context
- Provides `useUniverse()` hook for any child component
- Includes `perturb(kind, magnitude)` and `fetchReport()` action methods
- Single SSE connection shared across all Triune modes

**Step 3: Verify TypeScript compiles**

Run: `cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard && npx tsc --noEmit`
Expected: No errors

**Step 4: Commit**

---

## Task 5: Triune Navigation Shell (Layer 2 — Frontend)

**Files:**
- Create: `src/web/anima_dashboard/src/components/TriuneNav.tsx`
- Create: `src/web/anima_dashboard/src/components/HIHOBridge.tsx`
- Create: `src/web/anima_dashboard/src/components/AnimaNarrationBar.tsx`
- Create: `src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx`
- Create: `src/web/anima_dashboard/src/components/modes/VaultMode.tsx`
- Create: `src/web/anima_dashboard/src/components/modes/CockpitMode.tsx`
- Rewrite: `src/web/anima_dashboard/src/app/page.tsx`
- Modify: `src/web/anima_dashboard/src/app/globals.css`

**Step 1: Create HIHOBridge component**

`HIHOBridge.tsx`:
- Reads `coherence` from `useUniverse()` context
- Maps coherence to HIHO zone (critical_low, warning, stable, warning, critical_high)
- Sets CSS custom properties on `document.documentElement`:
  - `--hiho-hue` (computed from zone)
  - `--hiho-glow-color` (interpolated from brand palette)
  - `--hiho-pulse-speed` (faster at extremes: `2s` critical, `4s` warning, `8s` stable)
  - `--hiho-particle-density` (0.3 stable, 0.8 critical)
- Renders nothing visible (headless component)

**Step 2: Create TriuneNav component**

`TriuneNav.tsx`:
- Header bar with: Cohezion logo (left), three mode tabs (center), Anima Sigil (right)
- Modes: KNOWER/Observatory, THINKER/Vault, DOER/Cockpit
- Active tab has `--hiho-glow-color` underline
- Anima Sigil: small breathing "C" icon that pulses at `--hiho-pulse-speed`
- Props: `activeMode`, `onModeChange`, `animaStatus`

**Step 3: Create AnimaNarrationBar component**

`AnimaNarrationBar.tsx`:
- Bottom bar showing template-generated narration from live metrics
- Reads `state` and `report` from `useUniverse()` context
- Formats: "HIHO {stability}: {coherence:.4f} coherence. CA Rule 30: {active}/{total} active. {nominal}/{total} EVOs nominal."
- Typing animation effect for new narrations
- Subtle `--hiho-glow-color` border

**Step 4: Create mode shell components**

`ObservatoryMode.tsx`: Wraps existing OuroborosControlRoom, TensorBeamVisualizer, SnapshotGallery. Reads from `useUniverse()` context instead of props.

`VaultMode.tsx`: Shell with "THINKER — Vault" header and "Semantic search coming in Layer 5" placeholder. Styled with brand colors.

`CockpitMode.tsx`: Shell with "DOER — Cockpit" header and "Compound loop visualization coming in Layer 6" placeholder. Styled with brand colors.

**Step 5: Rewrite page.tsx**

Rewrite `src/web/anima_dashboard/src/app/page.tsx`:
- Wrap in `UniverseProvider`
- Include `HIHOBridge` (headless)
- `TriuneNav` with mode state
- Animated mode switching (CSS transitions per NFR12: 400ms/600ms/800ms)
- `AnimaNarrationBar` at bottom
- Move perturbation/report controls into ObservatoryMode

**Step 6: Update globals.css**

Add HIHO-reactive CSS variables, transition keyframes, mode animation classes:
- `@keyframes hiho-pulse` using `--hiho-pulse-speed`
- `.mode-enter-knower`, `.mode-enter-thinker`, `.mode-enter-doer` transition classes
- Glow effects using `--hiho-glow-color`

**Step 7: Verify it renders**

Run: `cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard && npx tsc --noEmit`
Then start the dev server and verify with playwright-cli.

**Step 8: Commit**

---

## Task 6: Observatory Mode — Re-Entry Narrative + Provenance (Layer 3)

**Files:**
- Create: `src/web/anima_dashboard/src/components/ReEntryNarrative.tsx`
- Create: `src/web/anima_dashboard/src/components/ProvenanceTag.tsx`
- Modify: `src/web/anima_dashboard/src/components/modes/ObservatoryMode.tsx`
- Modify: `src/cohezion/api/services/universe.py` (add history summary endpoint)

**Step 1: Write failing test for history summary endpoint**

Add to `tests/api/test_universe_stream.py`:

```python
class TestHistorySummary:
    def test_summary_returns_narrative_fields(self, client: TestClient) -> None:
        for _ in range(20):
            client.post("/api/universe/tick")
        resp = client.get("/api/universe/history/summary")
        assert resp.status_code == 200
        data = resp.json()
        assert "ticks_elapsed" in data
        assert "mean_coherence" in data
        assert "coherence_range" in data
        assert "alert_count" in data
        assert "narrative" in data
```

**Step 2: Implement history summary endpoint**

Add `GET /api/universe/history/summary` that reads the history deque and returns:
- `ticks_elapsed`, `mean_coherence`, `coherence_range` (min, max), `alert_count`, `ca_density_trend`
- `narrative`: template-generated text summarizing the history

**Step 3: Create ReEntryNarrative component**

Fetches `/api/universe/history/summary` on mount. Displays narrative with typewriter animation. Fades out after 10 seconds or on click.

**Step 4: Create ProvenanceTag component**

A tooltip component that accepts `source` string. Shows on hover with monospace font. Example: `source="HIHOStabilizationEngine.apply_hiho_loop()"`.

**Step 5: Wire into ObservatoryMode**

Add ProvenanceTags to key data points in OuroborosControlRoom. Show ReEntryNarrative on first Observatory visit per session.

**Step 6: Commit**

---

## Task 7: Anima Service — Template + MCP Tiers (Layer 4)

**Files:**
- Create: `src/cohezion/api/services/anima.py`
- Create: `tests/api/test_anima_service.py`
- Modify: `src/cohezion/api/__init__.py` (mount anima router)

**Step 1: Write failing tests**

```python
"""Tests for the Anima service (3-tier narration)."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI
    from cohezion.api.services.anima import anima_router

    app = FastAPI()
    app.include_router(anima_router, prefix="/api/anima")
    return TestClient(app)


class TestAnimaStatus:
    def test_status_returns_current_tier(self, client: TestClient) -> None:
        resp = client.get("/api/anima/status")
        assert resp.status_code == 200
        data = resp.json()
        assert data["tier"] in ("template", "mcp", "voice")
        assert "online" in data


class TestAnimaNarrate:
    def test_narrate_returns_text(self, client: TestClient) -> None:
        resp = client.post("/api/anima/narrate")
        assert resp.status_code == 200
        data = resp.json()
        assert "text" in data
        assert "HIHO" in data["text"]
        assert data["tier"] == "template"


class TestAnimaAsk:
    def test_ask_returns_answer(self, client: TestClient) -> None:
        resp = client.post("/api/anima/ask", json={"question": "What is HIHO?"})
        assert resp.status_code == 200
        data = resp.json()
        assert "answer" in data
```

**Step 2: Implement Anima service**

Create `src/cohezion/api/services/anima.py`:
- `AnimaService` class with 3-tier graceful degradation
- Tier 1 (Template): Format synthesis report into natural language
- Tier 2 (MCP): Route questions to KnowledgeMCP via HTTP (try/except for offline)
- Tier 3 (Voice): Pipe text through PocketTTSService (try/except for missing model)
- Endpoints: `GET /status`, `POST /narrate`, `POST /ask`, `POST /speak`

**Step 3: Run tests, verify passing**

**Step 4: Mount router in main app**

**Step 5: Commit**

---

## Task 8: Anima Chat Panel (Layer 4 — Frontend)

**Files:**
- Create: `src/web/anima_dashboard/src/components/AnimaChatPanel.tsx`
- Create: `src/web/anima_dashboard/src/hooks/useAnima.ts`
- Modify: `src/web/anima_dashboard/src/components/TriuneNav.tsx` (Sigil opens chat)

**Step 1: Create useAnima hook**

`useAnima.ts`:
- `ask(question: string)` — POST to `/api/anima/ask`
- `narrate()` — POST to `/api/anima/narrate`
- `status` — polls `/api/anima/status` on mount
- Returns `{ ask, narrate, status, messages, loading }`

**Step 2: Create AnimaChatPanel**

`AnimaChatPanel.tsx`:
- Slide-out panel from right side (triggered by clicking Anima Sigil)
- Chat messages list (user questions + Anima responses)
- Input field at bottom
- Anima responses styled in Instrument Serif italic (per Story 4.4)
- Brand-colored: `--color-neon-cyan` for Anima, `--color-silicon-silver` for user
- Shows tier badge: "Template Mode" / "MCP Grounded" / "Voice Active"

**Step 3: Wire Sigil click to open panel**

Modify TriuneNav: clicking Anima Sigil toggles AnimaChatPanel visibility.

**Step 4: TypeScript compile check + visual verification**

**Step 5: Commit**

---

## Task 9: Vault Mode — Semantic Search (Layer 5)

**Files:**
- Modify: `src/web/anima_dashboard/src/components/modes/VaultMode.tsx`
- Create: `src/web/anima_dashboard/src/components/VaultSearchResult.tsx`
- Create: `src/web/anima_dashboard/src/components/FreezeFrame.tsx`

**Step 1: Fill VaultMode with search UI**

`VaultMode.tsx`:
- Search bar at top with placeholder "Search Decisions, Experiments, Patterns..."
- On submit, calls `POST /api/anima/ask` with `question` (reuses Anima MCP routing)
- Results displayed as VaultSearchResult cards
- Three-pillar filter tabs: All / Decisions / Experiments / Patterns

**Step 2: Create VaultSearchResult component**

`VaultSearchResult.tsx`:
- Card with: title, excerpt, pillar badge (Decision/Experiment/Pattern), relevance score
- ProvenanceTag on hover showing source path
- Expand to show full content on click

**Step 3: Create FreezeFrame component**

`FreezeFrame.tsx`:
- Button: "Freeze Frame — Capture Current State"
- On click: reads current universe state from context
- Shows modal with: tick, coherence, EVO summary, annotation text field
- Submit saves as a vault Decision via `/api/anima/ask` with structured intent

**Step 4: TypeScript compile check**

**Step 5: Commit**

---

## Task 10: Cockpit Mode — Compound Loop + Architecture (Layer 6)

**Files:**
- Modify: `src/web/anima_dashboard/src/components/modes/CockpitMode.tsx`
- Create: `src/web/anima_dashboard/src/components/CompoundLoopViz.tsx`
- Create: `src/web/anima_dashboard/src/components/ArchitectureGraph.tsx`
- Create: `src/cohezion/api/services/architecture.py`
- Create: `tests/api/test_architecture_service.py`

**Step 1: Write failing test for architecture endpoint**

```python
"""Tests for the Architecture Graph API."""

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI
    from cohezion.api.services.architecture import architecture_router

    app = FastAPI()
    app.include_router(architecture_router, prefix="/api/architecture")
    return TestClient(app)


class TestArchitectureGraph:
    def test_graph_returns_nodes_and_edges(self, client: TestClient) -> None:
        resp = client.get("/api/architecture/graph")
        assert resp.status_code == 200
        data = resp.json()
        assert "nodes" in data
        assert "edges" in data
        assert len(data["nodes"]) > 0
```

**Step 2: Implement architecture graph endpoint**

Create `src/cohezion/api/services/architecture.py`:
- Reads actual package structure from `src/cohezion/` (using `pathlib`)
- Builds nodes (packages) and edges (imports) as JSON
- `GET /api/architecture/graph` returns the graph data
- Cached — regenerates only when requested

**Step 3: Create CompoundLoopViz component**

`CompoundLoopViz.tsx`:
- Five-phase ring: EXPANDING → PLANNING → EXECUTING → REFLECTING → REFINING
- SVG-based circular layout with animated phase indicator
- Current phase highlighted with `--hiho-glow-color`
- Historical cycles as fading concentric rings

**Step 4: Create ArchitectureGraph component**

`ArchitectureGraph.tsx`:
- Fetches from `/api/architecture/graph`
- Force-directed graph using canvas/SVG (or extend Three.js from existing R3F)
- Nodes colored by package category (compound=green, swarm=blue, physics=purple)
- Edges show import relationships
- Hover shows module details

**Step 5: Fill CockpitMode**

Wire CompoundLoopViz and ArchitectureGraph into CockpitMode layout.

**Step 6: Run tests, TypeScript compile, visual verification**

**Step 7: Commit**

---

## Task 11: Persistent Homology Overlay (Layer 7)

**Files:**
- Create: `src/web/anima_dashboard/src/components/PersistenceDiagram.tsx`
- Modify: `src/cohezion/api/services/universe.py` (add topology to report)
- Create: `tests/api/test_topology_overlay.py`

**Step 1: Write failing test**

```python
"""Tests for persistent homology data in reports."""

import pytest
from fastapi.testclient import TestClient

from cohezion.api.services.universe import universe_router


@pytest.fixture
def client() -> TestClient:
    from fastapi import FastAPI

    app = FastAPI()
    app.include_router(universe_router, prefix="/api/universe")
    return TestClient(app)


class TestTopologyInReport:
    def test_report_includes_topology(self, client: TestClient) -> None:
        for _ in range(10):
            client.post("/api/universe/tick")
        resp = client.get("/api/universe/report")
        data = resp.json()
        assert "topology" in data
        assert "persistence_pairs" in data["topology"]
        assert "entropy" in data["topology"]
```

**Step 2: Add topology data to SynthesisReport**

Modify `universe.py` `get_report()`:
- Collect EVO coherence trajectories from history deque
- Feed into `TopologicalPersistence.compute()` from `src/cohezion/compound/topological_persistence.py`
- Add `topology` field to `SynthesisReport` with `persistence_pairs` and `entropy`

**Step 3: Create PersistenceDiagram component**

`PersistenceDiagram.tsx`:
- Scatter plot: x = birth, y = death for each persistence pair
- Diagonal line (birth = death) shows noise threshold
- Points far from diagonal = persistent features
- Color-coded: H0 (clusters) in green, H1 (loops) in blue
- Updates from SSE report events

**Step 4: Wire into ObservatoryMode as an overlay**

Toggle button in Observatory: "Show Topology" reveals/hides the persistence diagram.

**Step 5: Run tests, TypeScript compile, visual verification**

**Step 6: Commit**

---

## Task 12: Integration Testing + Final Verification

**Files:**
- All test files from Tasks 1-11
- Playwright E2E test

**Step 1: Run full Python test suite**

Run: `cd /home/mike-anderson/dev/cohezion && uv run pytest tests/api/ -q`
Expected: All passing, zero regressions

**Step 2: Run full TypeScript type check**

Run: `cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard && npx tsc --noEmit`
Expected: No errors

**Step 3: Start both servers and verify E2E**

Start FastAPI: `cd /home/mike-anderson/dev/cohezion && uv run uvicorn cohezion.api:app --port 8080`
Start Next.js: `cd /home/mike-anderson/dev/cohezion/src/web/anima_dashboard && npm run dev`
Verify with playwright-cli:
- Open http://localhost:3000
- Verify Cohezion logo and favicon are present
- Verify KNOWER/THINKER/DOER navigation works
- Verify HIHO colors shift with coherence
- Verify Anima narration bar shows live metrics
- Verify Anima chat panel opens and responds
- Verify mode transitions have correct timing

**Step 4: Final commit**

---

## Session Boundaries

**Session 1 (current):** Tasks 1-5 (Layers 0-2: Brand + SSE + Triune Nav)
**Session 2:** Tasks 6-8 (Layers 3-4: Observatory + Anima)
**Session 3:** Tasks 9-12 (Layers 5-7: Vault + Cockpit + Topology + Integration)

Each session delivers a working, testable increment.
