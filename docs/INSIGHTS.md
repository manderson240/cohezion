# Insights — What This Sprint Taught Us

**Sprint ID:** sorted-churning-toucan (2026-04-18)
**Pairs with:** `SPRINT_2026-04-18_RETROSPECTIVE.md`, `ROADMAP.md`

## Architectural insights

### 1. TTFT is the Universes metric. Cost is secondary.

Benchmark-cycle wall-clock is the real bottleneck for agent training at scale. A 5-step reasoning chain at 1000 ms Claude API TTFT is 5 s; at 80 ms NPU TTFT it's 400 ms. **12.5× faster iteration; 12.5× more rollouts per GPU-hour.** Every cover-letter revision since realizing this has led with TTFT, cost as supporting evidence.

### 2. Tiered orchestration > flat routing.

`route()` is a dispatch primitive. `TieredOrchestrator` is the composition primitive. Flat routing picks one lane; orchestration runs cheap-first and escalates only when quality fails. The same 4-lane fleet under orchestration delivers quality-bounded cost curves that flat routing can't express.

### 3. AMD path preferences should be explicit, not heuristic.

`Lane.NPU < Lane.IGPU_ROCWMMA < Lane.CPU < Cloud` is the ordering that unlocks AMD silicon. The `_AMD_PATH_RANK` dict in `gaia_adapter.py` encodes it. Building a similar ordering off "smartness" or "model size" would mask this: Gemma-4-E2B (2B params) on NPU beats Gemma-4-31B (31B params) on CPU for most agent-decision prompts because TTFT dominates.

### 4. V-model AutoHarness > test suite alone.

Tests check behavior on inputs you remembered. AutoHarnesses check **invariants** that span the whole package. Phase 1 harness caught "every Lane enum must be reachable from ≥1 model" as a structural check — no test would have flagged adding a new `Lane.EDGE` enum without a corresponding model. The harness is a schema gatekeeper.

### 5. Streaming is how you measure TTFT honestly.

Total latency is not TTFT. The distinction is recoverable only via SSE streaming with a first-chunk timestamp. Non-streaming can be faster in absolute total time for small prompts because streaming adds protocol overhead, but it destroys TTFT as a measurable quantity. For reasoning-mode models (Gemma-4 FLM), TTFT is the **first reasoning-content chunk**, not the first visible text — separately measuring reasoning latency would be an even more precise signal.

## Operational insights

### 6. Session-scoped advisor is a hack; persistent advisor needs the Anthropic API.

`/advisor` in Claude Code is interactive-only. Every session has to re-invoke it. The right long-term fix is to wire the Anthropic SDK's Advisor Tool (`advisor-tool-2026-03-01` beta header) into `extend_claude()` so every escalation benefits from a secondary-opinion model automatically — no UI interaction required.

### 7. Adversarial review should run 3-in-parallel by default.

Scientific rigor, edge-case hunting, and security each catch orthogonal bugs. Running them in sequence costs 3× wall-clock and the reviewers don't benefit from each other's findings. Running in parallel + synthesizing in main context produces a combined review in ~90 s + synthesis time.

### 8. Entire.io checkpoints are the real retrospective source.

Git commits capture intent snapshots; entire checkpoints capture **reasoning snapshots**. The difference: commits don't record why a particular intermediate approach was abandoned. Entire does. `entire explain --checkpoint <id>` is the one-line retrospective per checkpoint.

### 9. Stale sessions leak from `-p` subprocesses.

Every `claude -p` / `gemini -p` subprocess registers with entire but doesn't persist a transcript. The original Stop hook errored and exited 0, leaving zombie sessions accumulating. The fix (`stop-resilient.sh`) falls back to `entire sessions stop <id> --force` when transcript is absent. Without this, session tables grow monotonically until a full cleanup pass.

### 10. Cold-boot-only recovery is a real constraint.

The Strix Halo iGPU aperture can enter a Zombie VRAM state that requires physical power-off to clear. Soft-reset, kernel restart, and `rocm-smi --gpureset` all fail to reclaim. The launch script must sequential-load iGPU models (not `lemonade load ... &` in parallel) because `GCVM_L2_PROTECTION_FAULT` during concurrent JIT compilation triggers exactly this state.

## Human-factor insights

### 11. User directives composed additively because each phase was additive.

Four user redirects mid-sprint (TurboQuant → headless CLI → GAIA SDK → tiered orchestration) could have torched the work. They didn't because every new feature was a new module, not a modification. `cohezion.inference` grew from 3 files to 7 without breaking the original 29 tests. Additive design is the key; any time a new directive would have forced modifying existing tested code, the work would have stalled.

### 12. Reviewer-facing artifacts must be shippable in isolation.

`SHOWCASE.md` + `COVER_LETTER_universes.md` + `local_environment_quirks.md` are readable without running any code. That's the bar for Universes-team outreach: a reviewer clicking the GitHub link should get the picture in 2 minutes without cloning.

### 13. Honest numbers beat inflated numbers every time.

The scientific-rigor review could have produced a "your speedup claims are suspicious — needs more samples" response months from now on a real interview. Catching it now, before the cover letter ships, is the single biggest value of doing the adversarial review in-cycle rather than at the end.
