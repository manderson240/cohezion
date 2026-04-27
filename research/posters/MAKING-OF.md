# MAKING-OF — "COHEZION  12D Universe + Compound Loop"

A 24" × 36" portrait architectural poster for the Cohezion compound-AI platform, designed and rendered on 2026-04-23 — the closing day of the `synthetic-sniffing-panda` polish campaign.

## Design intent

The brief asked for a poster that reads as a **scientific schematic** — a printer's plate from a discipline that does not quite exist, that rewards both the casual glance and the patient stare. The "Instrument Cosmography" philosophy set the tone: information lives in space, line, and color; words are rationed.

Three vertical registers. The eye descends like a star tablet:

1. **Top — the compound loop as a clockwork ring.** Eleven nodes around a circle, starting at 10 o'clock and proceeding clockwise. The five orchestrator nodes are magenta (the fan-out hub); the other six are cyan. At the centre, a Ψ glyph and twelve radial spokes diagram the 12-D state vector recorded by `JourneyTracker`.
2. **Middle — the architecture as a slab cake.** Eighteen horizontal strata, each with name, one-line description, and entry-point class on the right (`CompoundExecutor`, `LemonadeAdapter`, etc.). A magenta bracket on the left margin marks the seven-of-eighteen physics-and-world cluster — *39% of platform mass*.
3. **Bottom — the protocol stack as a hex lattice.** A 2 × 3 honeycomb of MCP, A2A, UCP, AP2, A2UI, AG-UI, shaded by adoption posture. Dotted lines between the green cells render the live integration mesh. Below, the 70 / 20 / 10 cost-routing bar.

Negative space is the most expensive material on the canvas.

## Color palette (hex)

| token | role | hex |
|---|---|---|
| navy | field, ground | `#0a0e1a` |
| navy-2 | inset boxes | `#0f1424` |
| ink | primary type | `#f1f5f9` |
| ink-dim | secondary type | `#cbd5e1` |
| gray | annotation, leader lines | `#475569` |
| gray-dim | divider lines, faint geometry | `#1e293b` |
| **cyan** | signal, the loop, the trace | `#22d3ee` |
| cyan-dim | activity bars (non-physics) | `#0891b2` |
| **magenta** | physics cluster, hub steps, output | `#e879f9` |
| magenta-dim | activity bars (physics) | `#a21caf` |
| amber | "in progress" status | `#fbbf24` |
| green | "strong / shipped" status | `#34d399` |

Three colors do all the meaningful speaking — cyan for the cool half of the system, magenta for the warm physics half, and a green/amber/gray triad for protocol status. The other tokens are hierarchy and connective tissue only.

## Typography choices

Each typeface has a single job:

- **Big Shoulders Bold** — title block (`COHEZION`, 150 pt) and section headers. Geometric sans with the gravity of a brass nameplate.
- **Outfit Bold / Regular** — layer names and short labels.
- **IBM Plex Mono Bold / Regular** — every numeric, every entry-point class, every register mark, every dimension label (`D01..D12`). The teletype log of the schematic.
- **IBM Plex Serif Italic** — figure captions. The engineer's pencil note.
- **Nothing You Could Do** — a single hand-drawn line in two places only: the vertical margin quote and the stamp signature.
- **mathtext** — Ψ at the centre and Ω in the plate number / stamp (the canvas-design TTFs don't carry Greek; this fallback reads as consistent with the schematic feel).

Sizes follow strict ratios: 150 → 26 → 13.5 → 10.5 → 8 → 7.5 pt.

## Composition rationale

24" × 36" portrait, vector PDF + 2880 × 4320 PNG (120 DPI screen). Built in matplotlib with inches as the native unit, so every coordinate is a printer's inch. Margins 0.55 in; a hairline-then-faint double frame anchors the page like an aquatint plate. A reseaux of register marks (2 in coarse + 0.25 in fine) recedes beneath the artwork like graph paper held up to the light — texture without noise. Section captions live in the corners so they never fight the central geometry; figure numbers sit in the right-hand corners and form a quiet vertical rhythm.

## Easter eggs

Seven small marks for the patient viewer.

1. **Ψ at the centre of the ring.** The spinor wavefunction symbol — Cohezion's house glyph for any "state vector". Set in cyan, never explained.
2. **`D01..D12` as the inner dial.** The twelve dimensions of `JourneyTracker.position(t)` are spelled out as the hour-marks on a clock face.
3. **Margin quote in handwriting.** The left edge of the ring carries, in pencil-script, *"every feature makes future features easier"* — the compound-engineering manifesto, vertical, sized just below the threshold of attention.
4. **`HIHO STABILITY ≈ 0.50`** on the right margin. The half-coherence target — Cohezion's HIHO optimum at the boundary between exploitation and exploration.
5. **The physics bracket — `7 / 18 = 39%`.** The magenta bracket on the left margin of the slab marks Physics→Environments as seven of eighteen layers — the platform's quiet self-identification: physics-first agentic infrastructure, not a thin LLM wrapper.
6. **Footer aphorism.** The bottom-left quotes CLAUDE.md verbatim: *EXECUTE FIRST · PLAN SECOND · INFRASTRUCTURE NEVER*.
7. **Hardware autograph.** The bottom rule reads `PRINTED ON THE AMD RYZEN AI MAX+ 395 · LPDDR5X 128 GiB · STRIX HALO` — the actual hardware, a nod to `HARDWARE_PROFILE_PRIME.md`.

The MADE-IN stamp in the lower-right names the polish campaign (`synthetic-sniffing-panda · campaign Ω14`), the date, the commit count, and signs it by hand.

## Print recommendation

- **Stock**: 200–250 gsm matte art paper. Avoid gloss — it kills the schematic feel.
- **Printer**: giclée at 240 dpi or higher. The PDF is vector except for the matplotlib glyphs, so it scales without artifacts.
- **Frame**: thin black aluminium or oiled walnut, no mat — the hairline inner frame already supplies the optical mat. Anti-glare museum glass for an office; bare for a studio.
- **Lighting**: single warm directional light from the upper left, ~3000 K. The navy reads as black in low light and as deep blue when lit.

## Files

- `2026-04-23-cohezion-architecture-poster.pdf` — print master.
- `2026-04-23-cohezion-architecture-poster.png` — 2880 × 4320 raster at 120 DPI (screen). For print, regenerate at higher DPI by editing `DPI_PNG` in `build_poster.py`.
- `build_poster.py` — the matplotlib generator (re-runnable, deterministic).
- `DESIGN-PHILOSOPHY.md` — the "Instrument Cosmography" manifesto used as the aesthetic compass.
