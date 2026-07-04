# Marimo Reactive Notebooks — V-Model Verified Implementation Plan

Created: 2026-06-25
Status: COMPLETE
Approved: Yes
Iterations: 0
Verified: 2026-06-25 (plan-verifier + plan-challenger both passed)
Worktree: No

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED

## Summary

**Goal:** Fix all three Cohezion marimo walkthrough notebooks so every UI control
(sliders, dropdowns, textareas, run buttons, URL inputs) is visible in app mode, then
write a playwright-based V-model test suite that verifies structural, behavioral, and
integration correctness at each layer.

**Architecture:** Marimo's reactive output rule — the *last non-assignment statement
expression* before `return` is the visual output. All current cells assign UI elements
then `return` them as a tuple; the tuple binds globals but renders nothing in app mode.
Fix: add an explicit `mo.vstack([...])` (or `mo.hstack`) display call as the final
statement before `return` for every cell that assigns UI widgets.

**Tech Stack:** marimo 0.23.10, plotly 6.8.0, playwright 1.60.0, pytest, Python 3.11.
Lemonade :13305 (AMD NPU, $0) for agent cells.

## Scope

### In Scope
- Fix all widget-display bugs in `cohezion_compound_loop.py`, `flume_latent_space.py`,
  `thermodynamic_gravity_sweep.py`
- Write `tests/walkthroughs/test_marimo_playwright.py` — V-model playwright suite
- Verify reactivity: slider change → plotly chart re-renders
- Verify agent gate: run_button with `mo.stop()` guard works correctly

### Out of Scope
- Lemonade live-inference test (requires :13305 up; tested separately)
- WASM export testing
- Audio/image generation tasks (#49, #50)

## Prerequisites
- `uv run marimo run` works (confirmed)
- `uv run python3 -c "from playwright.sync_api import sync_playwright"` succeeds (confirmed)
- Port 2719 available for test server

## Context for Implementer

**Root cause (confirmed by playwright + screenshot):**
In marimo's functional cell format, the cell's visual output = the last *expression statement*
evaluated before the `return`. Assignment statements (`x = ...`) don't count. So:

```python
# BROKEN — assignments only, nothing displayed:
@app.cell
def _(mo):
    slider = mo.ui.slider(0, 10)   # assignment — not displayed
    return (slider,)                # return tuple — NOT displayed in app mode

# CORRECT — explicit display call as last statement:
@app.cell
def _(mo):
    slider = mo.ui.slider(0, 10)
    slider                          # bare name expression → displayed
    return (slider,)

# OR use vstack for multiple controls:
@app.cell
def _(mo):
    n_cycles = mo.ui.slider(...)
    seed_val  = mo.ui.slider(...)
    mo.vstack([n_cycles, seed_val]) # last expression → output
    return n_cycles, seed_val
```

**Current failures (playwright confirmed, 2026-06-25):**
| Cell | Bug | Fix |
|------|-----|-----|
| Slider cell (n_cycles, seed_val) | returns tuple, no display call | add `mo.hstack([n_cycles, seed_val])` before return |
| Dropdown cell (chart_type) | returns `(chart_type,)`, no display | add `mo.vstack([chart_type])` before return (NOT bare name — ruff B018!) |
| Agent UI cell | `mo.md("heading"); return (controls...)` — heading shows, controls hidden | replace `mo.md(...)` with `mo.vstack([mo.md("## ..."), mo.hstack([loop_url, loop_model]), loop_query, loop_run])` |
| Agent response cell | `mo.callout(...); return ()` — callout IS the last expr → WORKS | no change needed |

**⚠️ NEVER use a bare name expression to display:**
```python
# WRONG — ruff B018 "useless expression" will remove this silently:
slider   # bare name on its own line
# RIGHT — always wrap in a marimo layout call:
mo.vstack([slider])
```

**⚠️ NEVER put display in the return tuple:**
```python
# WRONG — return lists variable names only, never expressions:
return mo.vstack([n_cycles, seed_val]), n_cycles, seed_val
# RIGHT — separate statement before return:
mo.hstack([n_cycles, seed_val])   # display
return n_cycles, seed_val          # bind globals only
```

**⚠️ FLUME + GRAVITY agent cells were REMOVED by a parallel audit fork:**
- `flume_latent_space.py`: currently 201 lines — has NO agent UI or response cells
- `thermodynamic_gravity_sweep.py`: currently 228 lines — has NO agent UI or response cells
- Tasks 2 and 3 must ADD these cells (copying the compound_loop pattern), not just fix display

The agent UI/response cell pattern to replicate lives in `compound_loop.py` lines 206-257.

**marimo.toml:** `~/.config/marimo/marimo.toml` already has `[ai.ollama]` → `:13305`.

**Pattern references:**
- Working cells (last expr = display): `mo.ui.plotly(fig); return (fig,)` at line ~176
- Working cells: `mo.md(text); return ()` at lines 24, 53, 187

**Playwright pattern:** inline server management (see `/tmp/claude/marimo_playwright_test.py`).
Start server as subprocess, wait for HTTP 200, run tests, SIGTERM on exit.

## Confirmed Playwright Baseline (pre-fix)

```
PASS T0_server        http_200
PASS T1_title         "Cohezion Compound Loop"
PASS T2_h1            ["Cohezion Compound Loop Metrics"]
FAIL T3_sliders       0 sliders found
PASS T4_plotly        chart present
FAIL T5_textarea      0 textareas found
FAIL T6_ask_button    buttons have empty text
FAIL T7_url_input     no input with 13305
PASS T8_summary_stats HIHO text present
PASS T9_screenshot    saved
```

## Progress Tracking

- [x] Task 1: Fix compound_loop.py — all widget cells display correctly
- [x] Task 2: Fix flume_latent_space.py — all widget cells display correctly
- [x] Task 3: Fix thermodynamic_gravity_sweep.py — all widget cells display correctly
- [x] Task 4: Write V-model playwright test suite
- [x] Task 5: Run full playwright suite — all tests pass on all three notebooks

**Total Tasks:** 5 | **Completed:** 5 | **Remaining:** 0

---

## Implementation Tasks

### Task 1: Fix cohezion_compound_loop.py

**Objective:** Add explicit display expression statements for every cell that assigns UI
widgets, so all controls render visibly in app mode.

**Dependencies:** None

**Files:**
- Modify: `docs/walkthroughs/cohezion_compound_loop.py`

**Cells to fix (file line numbers, pre-fix):**

| Cell | Lines | Fix |
|------|-------|-----|
| Sliders (n_cycles, seed_val) | 44-48 (confirmed) | Add `mo.hstack([n_cycles, seed_val], justify="start")` before `return n_cycles, seed_val` |
| Dropdown (chart_type) | 99-106 (confirmed) | Add `mo.vstack([chart_type])` before `return (chart_type,)` — NOT bare name (ruff B018) |
| Agent UI (loop_query, model, run, url) | 206-223 (confirmed) | Replace `mo.md("## heading")` with `mo.vstack([mo.md("## Live Agent — Ask About the Compound Loop"), mo.hstack([loop_url, loop_model], justify="start"), loop_query, loop_run])` |
| Metrics display | 53 | `mo.md(f"**Running...**"); return ()` — ALREADY WORKS, no change |
| Summary stats | ~187 | `mo.md(f"""..."""); return avg_...` — ALREADY WORKS, no change |
| Agent response | 226-257 | `mo.callout(...); return ()` — ALREADY WORKS, no change |

**Key Decision / Notes:**
- Use `mo.hstack([n_cycles, seed_val], justify="start")` for sliders — side-by-side looks better
- Use `mo.vstack(...)` for agent UI — stacks vertically
- Agent response cell (`mo.callout(...); return ()`) already works — last expr is callout. Do NOT change.
- Keep `return n_cycles, seed_val` as-is after adding display — the return still binds globals

**Definition of Done:**
- [ ] `uv run marimo check docs/walkthroughs/cohezion_compound_loop.py` exits 0 or warnings only
- [ ] Playwright T3 (sliders ≥ 2 found) PASS
- [ ] Playwright T5 (textarea found) PASS
- [ ] Playwright T6 (Ask Agent button found) PASS
- [ ] Playwright T7 (URL input with 13305 found) PASS

**Verify:**
```bash
uv run marimo check docs/walkthroughs/cohezion_compound_loop.py
uv run pytest tests/walkthroughs/test_marimo_playwright.py -k compound -v --timeout=60
```

---

### Task 2: Fix flume_latent_space.py

**Objective:** Fix widget display in FLUME notebook — sliders (n_points, n_clusters,
latent_dim, beta_val) and agent UI (flume_query, model, run, url).

**Dependencies:** None (parallel with Task 1)

**Files:**
- Modify: `docs/walkthroughs/flume_latent_space.py`

**Cells to fix/add:**

| Cell | Current state | Fix |
|------|--------------|-----|
| 4-slider cell (n_points, n_clusters, latent_dim, beta_val) | lines 50-57, no display | Add `mo.vstack([n_points, n_clusters, mo.hstack([latent_dim, beta_val], justify="start")])` before return |
| Agent UI cell | **MISSING — must be added** | Copy compound_loop agent UI cell (lines 206-223), replace `loop_*` with `flume_*`, update system prompt to FLUME/VAE/β expert |
| Agent response cell | **MISSING — must be added** | Copy compound_loop agent response cell (lines 226-257), replace `loop_*` with `flume_*` |

**Definition of Done:**
- [ ] `uv run marimo check docs/walkthroughs/flume_latent_space.py` exits 0 or warnings only
- [ ] Playwright: 4+ sliders visible, textarea visible, run button visible

**Verify:**
```bash
uv run marimo check docs/walkthroughs/flume_latent_space.py
uv run pytest tests/walkthroughs/test_marimo_playwright.py -k flume -v --timeout=60
```

---

### Task 3: Fix thermodynamic_gravity_sweep.py

**Objective:** Fix widget display in ThermodynamicGravity notebook — sliders (epsilon,
temperature, n_legs) and agent UI (gravity_query, model, run, url).

**Dependencies:** None (parallel with Tasks 1 & 2)

**Files:**
- Modify: `docs/walkthroughs/thermodynamic_gravity_sweep.py`

**Cells to fix/add:**

| Cell | Current state | Fix |
|------|--------------|-----|
| 3-slider cell (epsilon, temperature, n_legs) | lines 53-65, no display | Add `mo.vstack([epsilon, mo.hstack([temperature, n_legs], justify="start")])` before return |
| Agent UI cell | **MISSING — must be added** | Copy compound_loop agent UI cell, replace with `gravity_*` names, update system prompt to ThermodynamicGravity/ε/Otto-cycle expert |
| Agent response cell | **MISSING — must be added** | Copy compound_loop agent response cell, replace with `gravity_*` names |

**Definition of Done:**
- [ ] `uv run marimo check docs/walkthroughs/thermodynamic_gravity_sweep.py` exits 0 or warnings only
- [ ] Playwright: 3+ sliders visible, textarea visible, run button visible

**Verify:**
```bash
uv run marimo check docs/walkthroughs/thermodynamic_gravity_sweep.py
uv run pytest tests/walkthroughs/test_marimo_playwright.py -k gravity -v --timeout=60
```

---

### Task 4: Write V-model playwright test suite

**Objective:** Write `tests/walkthroughs/test_marimo_playwright.py` covering all three
V-model layers: structural (DOM elements present), behavioral (reactivity), integration
(agent cell mo.stop guard works).

**Dependencies:** Tasks 1, 2, 3 (fixes must be in place first)

**Files:**
- Create: `tests/walkthroughs/__init__.py`
- Create: `tests/walkthroughs/test_marimo_playwright.py`

**V-Model test layers:**

**Layer 1 — Structural (what elements exist):**
- S1: Title contains notebook name
- S2: H1 heading renders
- S3: Sliders present (≥2 for compound, ≥4 for flume, ≥2 for gravity)
- S4: Plotly chart renders (`.js-plotly-plot` present)
- S5: Agent textarea present (compound: placeholder contains "compound")
- S6: Ask Agent run button present
- S7: Lemonade URL input present (value contains "13305")
- S8: Model dropdown present

**Layer 2 — Behavioral (reactivity):**
- B1: Slider drag → plotly chart label updates (title text changes)
- B2: Dropdown selection → chart type changes
- B3: Run button click without query → mo.stop() fires, no error, shows hint text

**Layer 3 — Integration (system boundaries):**
- I1: Run button click with query → loading state appears (or Lemonade response arrives)
- I2: Lemonade unreachable → graceful error message shown (not crash)

**Test structure (use raw sync_playwright — pytest-playwright plugin is NOT installed):**
```python
import pytest
from playwright.sync_api import sync_playwright  # NOT pytest-playwright plugin

_NOTEBOOKS = [
    ("cohezion_compound_loop.py", 2720, 2),
    ("flume_latent_space.py",     2721, 4),
    ("thermodynamic_gravity_sweep.py", 2722, 3),
]

@pytest.fixture(
    params=_NOTEBOOKS,
    ids=["compound", "flume", "gravity"],
    scope="module",
)
def marimo_server(request, tmp_path_factory):
    """Start a marimo server per notebook; yield (base_url, n_sliders); SIGTERM on teardown."""
    nb, port, n_sliders = request.param
    nb_path = Path("docs/walkthroughs") / nb
    proc = subprocess.Popen(
        ["uv", "run", "marimo", "run", str(nb_path), "--no-token", "--headless", "--port", str(port)],
        stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
    )
    # Poll until ready
    base = f"http://localhost:{port}"
    for _ in range(30):
        try: urllib.request.urlopen(base); break
        except Exception: time.sleep(0.5)
    yield base, n_sliders
    proc.terminate(); proc.wait(timeout=5)  # yield teardown: runs even on test failure

def test_structural_layer(marimo_server):
    base_url, n_sliders = marimo_server
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.goto(base_url, wait_until="networkidle")
        # S3: slider count
        sliders = page.locator("input[type='range']")
        assert sliders.count() >= n_sliders
        browser.close()
```

**B1 behavioral anchor (plot title is static — assert something reactive):**
```python
# B1: change chart_type dropdown → assert plotly subplot count changes
# OR: change seed slider → assert summary stats "Mean" text changes
# Confirmed observable: dropdown "Quality Score" → 1 subplot; "All" → 4 subplots
```

**Definition of Done:**
- [ ] `tests/walkthroughs/test_marimo_playwright.py` exists and imports cleanly
- [ ] All S1-S8 structural tests pass for all 3 notebooks
- [ ] B3: run button without query → `mo.stop()` guard prevents agent call, shows hint text
- [ ] I2 (graceful Lemonade error) verified by pointing URL to port 9999

**Verify:**
```bash
uv run pytest tests/walkthroughs/test_marimo_playwright.py -v --timeout=120
```

---

### Task 5: Full V-model acceptance run

**Objective:** Run the complete playwright suite against all three fixed notebooks.
All tests pass. Update HACKATHON_LOOPS.md progress line for Task #48.

**Dependencies:** Tasks 1, 2, 3, 4

**Files:**
- Read/update: `~/cohezion-labs/HACKATHON_LOOPS.md` (progress line for Task #48)

**Definition of Done:**
- [ ] `uv run pytest tests/walkthroughs/ -v` exits 0
- [ ] Screenshot evidence saved to `docs/walkthroughs/images/playwright-verified-*.png`
- [ ] HACKATHON_LOOPS.md Task #48 progress updated to: "COMPLETE. Playwright V-model: all structural + behavioral + integration tests pass."

**Verify:**
```bash
uv run pytest tests/walkthroughs/ -v --timeout=120
ls docs/walkthroughs/images/playwright-verified-*.png
```

---

## Testing Strategy

- **Structural:** DOM element presence via playwright CSS/ARIA selectors
- **Behavioral:** Playwright `fill()` + `wait_for()` to verify reactive re-render
- **Integration:** Subprocess mock server on 9999 returns 503; notebook shows error msg

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|-----------|--------|------------|
| marimo version API change for `mo.hstack` signature | Low | Med | Read marimo 0.23.10 source; use keyword args |
| Port conflicts during parallel test runs | Med | Low | Each notebook uses a unique port (2720/2721/2722) |
| Playwright timing flakiness on slow CI | Med | Med | All `wait_for` calls use 8000ms timeout; add retry |
| Lemonade :13305 not running during I1 test | High | Low | I1 is optional; I2 (error handling) is mandatory |

## Open Questions

None — root cause confirmed, fixes are clear.

### Deferred Ideas
- WASM export test (notebooks work offline in browser)
- Visual regression testing (screenshot diffs across marimo versions)
- Accessibility audit (ARIA labels on all UI controls)
