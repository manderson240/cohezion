---
branch: polish/design-artifacts
base: polish/research-deep-think
commits: 4 (incremental) / 89 (vs main)
files_changed: 45 (incremental)
loc_delta: +18299 / -0 (incremental, all additions; HTML/SVG/PDF artifacts)
campaign: synthetic-sniffing-panda (2026-04-23)
campaign_plan: ~/.claude/plans/synthetic-sniffing-panda.md
campaign_retrospective: ~/vaults/cohezion-vault/retrospectives/2026-04-23-synthetic-sniffing-panda.md
---

# polish/design-artifacts — Mockups, Algorithmic Art, Posters, Theme Variants

## Summary
This PR is the visual/design tier: 4 dashboard mockups (Wave D2), 5 algorithmic art pieces (Wave D3), the 12D-universe architecture poster with both PNG and PDF outputs (Wave Ω14), and 4 themed variants of each D2 mockup (Wave Ω15) for a total of 16 themed mockup HTML files. Pure visual artifacts — no source code, no tests, no documentation prose. Sized for review by designers / brand reviewers / PMs more than engineers.

## Scope
**In scope (4 commits):**
- Wave D2 — `feat(design): complete D2 dashboard mockups` — 4 standalone interactive mockups (HTML+SVG)
- Wave D3 — `feat(design): add 5 algorithmic art pieces for cohezion concepts` — p5.js generative art pieces
- Wave Ω14 — `feat(design): cohezion 12D-universe architecture poster` — Python-generated poster (`build_poster.py`) + PNG + PDF + design philosophy doc
- Wave Ω15 — `feat(design): apply 4 themes to Wave D2 mockups` — themed variants (modern-minimalist, retro-pixel, dark-mode, colorblind-safe) of each D2 mockup

**Out of scope:**
- Wave D1 (architecture diagrams) — already in main / separate PR (not in this campaign's commits)
- The poster build script's runtime output (only the SVG/PNG/PDF outputs and the build script are committed; reproducing requires `uv run python research/posters/build_poster.py`)

## Wave breakdown

### Wave D2 — Dashboard mockups (commit 2088f0b62)
4 interactive HTML mockups (~560 lines each) for hypothetical Cohezion product surfaces:
- `research/mockups/journey-tracker-12d.html` — 12D journey visualization
- `research/mockups/swarm-topology.html` — swarm agent topology
- `research/mockups/flume-latent-explorer.html` — FLUME latent space explorer
- `research/mockups/compound-loop-traces.html` — compound execution trace viewer
- `research/mockups/INDEX.md` — mockup navigation

Standalone HTML — drag-drop into a browser to view.

### Wave D3 — Algorithmic art (commit 6f86add38)
5 p5.js pieces (~440 lines each) illustrating cohezion concepts:
- `research/visualizations/algorithmic-art/spin-coherence.html`
- `research/visualizations/algorithmic-art/swarm-mycelium.html`
- (and 3 others — see `INDEX.md`)

Each uses seeded randomness so the visual is reproducible.

### Wave Ω14 — 12D-universe poster (commit 3fc16356c)
- `research/posters/build_poster.py` — 916-line Python generator (matplotlib-based)
- `research/posters/2026-04-23-cohezion-architecture-poster.png` — rendered PNG
- `research/posters/2026-04-23-cohezion-architecture-poster.pdf` — rendered PDF
- `research/posters/MAKING-OF.md` — process notes
- `research/posters/DESIGN-PHILOSOPHY.md` — visual language rationale

### Wave Ω15 — Themed mockup variants (commit 6ea8c0f3a)
For each of 4 D2 mockups, generate 4 themed variants → 16 themed HTML files in `research/mockups/themed/<theme>/<mockup>.html`:
- `modern-minimalist/`
- `retro-pixel/`
- `dark-mode/`
- `colorblind-safe/`

Plus theme manifests / shared CSS.

## Key metrics
- **Visual artifacts shipped**: 4 + 5 + 1 (poster image) + 16 (themed mockups) = 26 standalone artifacts
- **Build scripts**: 1 (`build_poster.py`, 916 lines)
- **Largest file**: `cohezion-architecture-poster.pdf` (binary, exact size in git LFS or directly committed — check `git lfs ls-files`)
- **Total lines**: 18,299 (HTML+CSS+SVG+JS+Python — includes large generated SVG paths)

## Test impact
- **No source/test changes.** Test counts unchanged from `polish/research-deep-think` baseline.
- **Build script verification**: `uv run python research/posters/build_poster.py` must succeed and regenerate the PNG/PDF. Suggested as a manual verification step pre-merge.

## Files changed (categorized)

| Directory | Files | Notes |
|---|---|---|
| `research/mockups/` | 5 | 4 D2 mockups + INDEX |
| `research/mockups/themed/` | 29 | 4 themes × 4 mockups + shared assets + theme INDEX files |
| `research/visualizations/algorithmic-art/` | 6 | 5 art pieces + INDEX |
| `research/posters/` | 5 | build_poster.py + PNG + PDF + MAKING-OF + DESIGN-PHILOSOPHY |

## Reviewer guide

**For designers / brand reviewers:**
1. Open each D2 mockup in a browser (drag the file into Chrome/Firefox).
2. Review the 4 themed variants (Ω15) for color contrast (especially `colorblind-safe`).
3. Open the poster PDF and assess the 12D-universe visual storytelling.

**For engineers:**
1. Skim `research/posters/build_poster.py` for code quality (it's matplotlib + numpy heavy; not on the critical path).
2. Verify the algorithmic art pieces are seeded (same input → same output).
3. Confirm no large binary blobs were committed without LFS — `git lfs ls-files` should show the PDF if LFS is wired correctly. (If not, file size is acceptable: PDF is ~few MB.)

**For product managers:**
- The 4 D2 mockups are HYPOTHETICAL — they don't reflect a shipped product surface. They're conceptual design probes to inform future UX.

## Dependencies
- **Builds on `polish/research-deep-think`** for stack ordering only — no actual code dep. Could merge against main directly.
- **No PR depends on this** — design artifacts are leaf nodes.

## Verification recipe
```bash
git checkout polish/design-artifacts
# Visual smoke (manual):
xdg-open research/mockups/journey-tracker-12d.html
xdg-open research/posters/2026-04-23-cohezion-architecture-poster.pdf
# Re-build the poster (verifies the build script works):
uv run python research/posters/build_poster.py
# Should regenerate PNG/PDF without changes (deterministic). Diff if curious:
git diff -- research/posters/
```

## Risks
- **Repository size**: 18,299 LOC of HTML/SVG/PDF inflates the bundle. Verify the PDF is in git LFS (per `.gitattributes` it should be — `*.pdf` may need to be added if not already). Run `git lfs ls-files | grep poster` to confirm.
- **Build script reproducibility**: `build_poster.py` uses matplotlib's font cache. Different machines may produce slightly different PNG bytes (font hinting, antialiasing). Treat the committed PNG/PDF as canonical; don't auto-regenerate in CI without comparing visually.
- **Themed mockups maintenance burden**: changing a base mockup requires re-generating 4 themed variants. No automation exists yet — manual sync.
- **Bit-rot**: HTML mockups will go stale as design evolves. Date-stamp in the filename helps; treat them as snapshots, not living docs.

## Out of scope (deferred)
- Wave D1 architecture diagrams (already in main, not in this campaign)
- Productionizing any of the mockups (these are concept probes, not implementation specs)
- Theme automation (manual generation for now)
- Poster physical printing (PDF is print-ready; not procured)
