# Sprint Retrospective — 2026-04-18

**Sprint ID:** sorted-churning-toucan
**Plan file:** `~/.claude/plans/sorted-churning-toucan.md`
**Duration:** ~6 hours of focused session work
**Entire.io checkpoints:** 32+ on branch `isolated/session-oom-modularity`

## What shipped

### New package — `cohezion.inference` (7 modules, 41 tests)

| Module | Purpose | LOC |
|--------|---------|-----|
| `__init__.py` | Public API — `route`, `extend_claude`, orchestrator surface | ~70 |
| `registry.py` | Fleet model × lane × task registry (14 models, 7 lanes) | ~300 |
| `health.py` | 30 s-cached probes for 7 lanes + Omnibus gateway snapshot | ~230 |
| `fleet.py` | `route()` + `extend_claude()` + streaming SSE dispatch | ~500 |
| `harnesses.py` | 3-slot `HarnessPool` for concurrent Ollama cloud via pi/opencode/hermes | ~180 |
| `orchestrator.py` | `TieredOrchestrator` — `/advisor` pattern applied recursively | ~240 |
| `gaia_adapter.py` | GAIA SDK integration + AMD-path-aware factory | ~180 |

### New docs (7 reviewer-facing artifacts)

- `README.md` — rewritten with Local Inference Fleet section (Gemma 4 × NPU/iGPU/CPU)
- `SHOWCASE.md` — 1-page reviewer one-pager with TTFT p50=80ms, `make demo-universes`
- `MANIFEST_ALIGNMENT.md` — hybrid-translation map (esoteric ↔ ML-canonical)
- `local_environment_quirks.md` — Strix Halo living doc (gfx1151, HSA override 11.5.1, reasoning-mode budget)
- `docs/application/COVER_LETTER_universes.md` — Universes-role-targeted cover letter
- `docs/archaeology/INFERENCE_AUDIT.md` — Phase 0 audit
- `docs/archaeology/INVENTORY.md` — 608-item root catalog

### New infrastructure

- `scripts/launch_fleet_safe.sh` — sequential staged launch (avoids aperture contention)
- `scripts/benchmark_fleet.py` — 4-config benchmark (Claude-only vs local-only vs hybrid-budget vs hybrid-quality)
- `scripts/validation/vmodel/phase1_inference_harness.py` — 10-invariant gatekeeper for inference fleet
- `scripts/validation/vmodel/phase2_benchmark_harness.py` — 7-invariant gatekeeper for benchmark output
- `scripts/validation/vmodel/phase6_orchestrator_harness.py` — 8-invariant gatekeeper for orchestrator
- `demo/universes_demo.py` — end-to-end hero demo (`make demo-universes`)
- `demo/orchestrate_demo.py` — tiered-orchestrator live demo (`make demo-orchestrate`)
- `.claude/hooks/stop-resilient.sh` — fixes zombie-session leak from `-p` subprocesses
- `.claude/hooks/advisor-reminder.sh` — SessionStart reminder for `/advisor`

### Infra changes

- BMAD upgraded v6.0.4 → v6.3.0 (26 custom files preserved; 101 claude-code skills re-registered)
- Entire.io: 10 stale sessions closed, DEBUG log level enabled, `.entire/settings.json` updated
- 10 stop-hook Makefile targets added (`make demo-universes`, `health-fleet`, `serve-fleet`, `entire-status`, `entire-retro`, `entire-rewind`, `entire-clean-stale`, `benchmark-fleet`, `vmodel-phase{1,2,6}`, `vmodel-all`, `demo-orchestrate`)

## V-Model compliance

Every workstream got all three artifacts per the `SYSTEMS_ENGINEERING_V_MODEL_PRIME` skill:

| Phase | Plan (`docs/vmodel/`) | AutoHarness | Verification |
|-------|-----------------------|-------------|--------------|
| 1 — Inference fleet | `PHASE1_INFERENCE_PLAN.md` | `phase1_inference_harness.py` (10 invariants) | 29 unit tests |
| 2 — Benchmark | `PHASE2_BENCHMARK_PLAN.md` | `phase2_benchmark_harness.py` (7 invariants) | Exit-0 gated live run |
| 6 — Orchestrator | `PHASE6_ORCHESTRATOR_PLAN.md` | `phase6_orchestrator_harness.py` (8 invariants) | 12 unit tests |
| Review | `ADVERSARIAL_REVIEW_2026-04-18.md` | 3 parallel reviewer agents | 6 critical fixes shipped |

All 3 harnesses green. 41/41 tests passing.

## Empirical results

- **NPU TTFT p50 = ~80 ms** (informal 5-call warm loop via `route(stream=True)`) — pending full n=20 benchmark for statistical validity
- **Pilot benchmark (n=3):** Config B (local-only) 3/3 ok, Config C (hybrid budget) 3/3 ok, Config A (Claude-only) 0/3 silent failures diagnosed in review, Config D (extend_claude) 0/3 cascaded from A
- **Live demo (`make demo-universes`):** 5 prompts dispatched through `route()` → NPU → all ok, $0 cost, 2.7 s wall-clock
- **Live orchestrator demo:** NPU Gemma-4-E2B passed gate on first tier, 0 escalations, $0 cost

## What went well

1. **V-model + AutoHarness every phase.** Each workstream shipped plan + harness + acceptance gate. Running `make vmodel-all` gives a 30-second confidence snapshot.
2. **Adversarial review in parallel.** 3 reviewer agents (scientific, edge-case, security) produced 20+ findings in ~90 s each. 6 critical fixes landed in the same session.
3. **Auto mode + user-directed pivots composed well.** User redirected the scope 4 times (Turboquant focus → headless CLIs → GAIA SDK → orchestrator abstraction) and the accumulated work kept composing because each layer was additive.
4. **Entire.io checkpoints.** 32 checkpoints mean the full reasoning context is rewindable — this retrospective is sourced from the checkpoints plus the plan file plus the review reports.

## What hurt

1. **n=5 warm-loop observations got promoted to typed `p50/p95` registry fields.** Caught by scientific-rigor review. Fixed by nulling typed fields; warm-loop described as informal in notes.
2. **`--yolo` / `--approval-mode yolo` flags slipped into production dispatch paths.** Caught by security review. Risk: any prompt reaching `harnesses.py` or the Gemini CLI could have executed shell commands without confirmation. Fixed.
3. **Benchmark report had a corpus-size inconsistency** (header said 20, table said 3 for the pilot). Caught by scientific-rigor review. Fixed — header now discloses executed N of 20 available + PILOT/BENCHMARK flag.
4. **`HarnessPool.acquire()` race** could leak busy slots on cancellation. Caught by edge-case reviewer. Fixed with `asyncio.shield`.
5. **Config A (Claude-only) silent failure in benchmark.** `claude -p` returned empty stderr; no diagnostic trail. Partial fix: PILOT status flag. Full fix (stderr sidecar + I2b invariant) deferred as follow-up.
6. **Demo stochasticity from reasoning-mode models.** Gemma-4 FLM used all 256 max_tokens on `<thinking>`, leaving empty visible text in some runs. Fix: demo now uses max_tokens=1024 non-streaming; `local_environment_quirks.md` documents the budget floor.

## Follow-ups (13 catalogued, not shipped)

See `docs/vmodel/ADVERSARIAL_REVIEW_2026-04-18.md` bottom section. Prioritized:

1. Edge-case #10 — nested orchestrator budget pass-through (O3 invariant)
2. Edge-case #14 — CLI liveness probe needs `-p` check, not `--version`
3. Security MED — explicit `httpx.Timeout(connect=5.0)`
4. Edge-case #2 — validate `claude_model` before extend_claude's local loop
5. Scientific #2 — Config A stderr capture + I2b invariant in Phase 2 harness
