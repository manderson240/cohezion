# Fable 5 Run Summary — 2026-07-07 — Genesis Unification

Branch `worktree-imperative-wondering-kettle`, 6 commits. Same content drafted to Gmail
(the available Gmail tool creates drafts only — nothing was sent).

## Outcome (TL;DR)

Items 1, 2, and 5b are **done and independently verified**; item 3 is **done at the
code level** (real leak fixes) with true-FPS numbers left as a one-command desktop
punch-list item because this session's container has no GPU; item 5a's ":13305 hang"
is **solved** (it was cold-model-load time, not a hang) and the full NPU+iGPU+CPU
parallel-inference recipe is proven and written down; item 4 was **skipped** by budget
decision after you flagged 81% usage.

## What shipped, with evidence

**Item 1 — Vacuum tab (commits `3db821e59`, `dc0a1ed`-series).** The five orphan
Three.js components now render as a Genesis "Vacuum — Latent Mind Theater" tab fed by
a new `/api/journey-nexus/frame` endpoint serving live simulation state (8 EVO agents'
12D latent vectors, vacuum-topology winding numbers, 16³ density field, nexus I/Q).
Key discovery: the test suite already contained the full designed contract for this
endpoint ("Latent Mind Theater", previously 404-failing) — implemented to it, **19/19
router tests pass** (was 9/19). Zod validates every fetch: real payload accepted,
**5/5 malformed variants rejected** (`scripts/zod-reject-check.mts`). Live badge
verified in a real browser: ticks advance, 9× HTTP 200, **0 console errors from the
new tab**. Fresh-context verifier: **PASS-WITH-CAVEATS** (caveat = no GPU pixels in
this container; disclosed, not hidden).

**Item 2 — Agent-driven A2UI cosmogony.** `genesis-cosmogony.json` renders in a new
Genesis "A2UI" tab. Nothing decorative: the state panel polls the real cosmogony
engine; the temperature slider POSTs `set-temperature` and the engine's response is
observable (verified round-trip: slider 42 → badge `T=42.00 · SO(12) · stage 1`);
every symmetry transition is narrated live by a **real GAIA-tier agent**
(`/api/gaia/narrate`, `build_gaia_llm_tier(llama3.2-1b-FLM)` — the GAIA SDK's first
API exposure) with a provenance badge (`gaia-local` vs `fallback`). Found and fixed a
real bug my first version introduced (unguarded state merge → 1927 update-depth
errors → 0). Fresh-context verifier: **PASS** on every check. Bonus: `tsc --noEmit`
is now completely clean (fixed 2 pre-existing errors).

**Item 3 — Performance.** Real fixes: JourneyRibbon was allocating 8 geometries +
materials **every 2-second poll** with no disposal; all five scene components now
dispose GPU resources on unmount (previously every tab switch leaked the whole
scene). Verifier caught the fifth component (QuadratureNexus) missing disposal —
fixed. **True FPS was unmeasurable here**: the container has no /dev/dri; WebGL fails
in every browser/flag combination (exhaustively tried, documented in PROGRESS.md).

**Item 5a + your fleet directive — the full neural net, cooking.** The prior
"trivial fast / real prompt hangs" mystery is solved: it's **cold-load time exceeding
client timeouts**. Recipe, verified live with zero config changes: pre-load one model
per backend lane (`lemonade_load_model`, bounded ctx, save_options), then dispatch
concurrently — llama3.2-1b (NPU) + Gemma-4-E4B (iGPU/vulkan) + Bonsai-8B (CPU) ran
**three real prompts in parallel: 35.8 s total wall = the slowest lane, not the
54.6 s sum**. Second trap confirmed: thinking models (E4B) return empty content below
~512 max_tokens. Vault decision: `2026-07-08-multi-lane-parallel-local-inference-...`.

**Item 5b — `docs/genesis-walkthrough.md`** (drafted on the local 1B lane,
fact-corrected — quarter-on-a-string in practice).

## Honest limits / punch list (needs you or a local session)

1. **Look at the 3D scenes on your desktop** (aesthetic judgment + true FPS):
   `cd src/web/anima_dashboard && node scripts/vacuum-verify.mjs` — saves screenshots
   + 10 s FPS sample. I never saw rendered pixels; "engaging/polished" is unverified.
2. **SurrealDB indexing is broken**: `surrealdb_start_watching` returns success but
   notes written 3.5 h earlier never appeared (`vault_neuron` count = 1). All vault
   markdown is on disk; nothing new is in SurrealDB. Worth a debugging session.
3. Pre-existing, not mine (documented in PROGRESS.md): FlumeLatentViz + SwarmTopologyViz
   fetch wrong `/api/...` prefixes (404 today); `journey_status` router never mounted;
   7 failing service-level tests in `tests/api/test_journey_nexus.py` (the service half
   of the contract whose router half this run implemented).

## What a $0 local-Lemonade session can pick up before Friday's Fable reset

- **Implement `JourneyNexus` service methods** (`stream_snapshot`, `quadrature`,
  `narrate`, `omni_chat`) against the 7 already-written failing tests — the exact
  tests-as-spec pattern this run used for the router; Bonsai-8B/Qwen3-Coder can draft,
  tests judge.
- **Fix the two frontend prefix bugs** (mechanical one-liners, tests exist via e2e).
- **Multi-lane narration**: route `/api/gaia/narrate` heavy stages to the iGPU E4B lane
  (max_tokens ≥ 600) using the proven pre-load recipe; keep 1B as the fast default.
- **Item 4 leftovers**: embedded Lemonade instance per the Embeddable SDK; generated
  static imagery/audio for the Genesis tabs (kokoro-v1 TTS + gemma3-4b vision are
  already in the fleet catalog).
- **Debug the vault→SurrealDB watcher** (point 2 above).

## Where everything lives

- Working log + all evidence: `docs/fable5-run-20260707/PROGRESS.md` (+ 5 screenshots)
- Walkthrough: `docs/genesis-walkthrough.md`
- Verify scripts: `src/web/anima_dashboard/scripts/{vacuum-verify,a2ui-verify}.mjs`,
  `zod-reject-check.mts`
- Vault decisions: tests-as-spec · liveDataModel value-guard · multi-lane parallel recipe
- Memory: `quarter-on-a-string-protocol` saved to project auto-memory
