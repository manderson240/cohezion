# V-Model Phase 1 — Inference Fleet Foundation (Retrofit)

**Workstream:** sorted-churning-toucan — Phase 1 (D.1–D.7)
**Status:** implementation shipped 2026-04-18; this doc is the retrofit plan that names the invariants the shipped code must satisfy.
**Pairs with:** `scripts/validation/vmodel/phase1_inference_harness.py` (AutoHarness), `src/cohezion/inference/` (implementation), `tests/inference/` (unit verification).

## 1. Requirement

Ship a unified local-first inference facade (`cohezion.inference.route()` +
`extend_claude()`) with 6 dispatch surfaces (NPU, iGPU-ROCWMMA, iGPU-Unified,
CPU, Ollama, Claude-CLI, Gemini-CLI, HarnessPool) so an agent can call one
function and reach any model. Captures TTFT via streaming.

## 2. Descending Path

### 2.1 Module design
- `registry.py` — single source of truth for lane × model × task × latency observations
- `health.py` — 30s-cached probe of every lane, including Omnibus gateway dashboard
- `fleet.py` — `route()` orchestrator with streaming + TTFT + symmetry-axis injection
- `harnesses.py` — 3-slot `HarnessPool` for concurrent Ollama cloud dispatch

### 2.2 Invariants

| # | Invariant | Rationale |
|---|-----------|-----------|
| F1 | Registry contains the 4 Strix Halo Symphony Gemma 4 entries with ports 13306/13307/13308/13309 | Source-of-truth must match `scripts/launch_gemma4_symphony.sh` |
| F2 | Registry entries have unique `model_id`s (no silent collisions) | Accidental duplicate would make `registry.models[id]` nondeterministic |
| F3 | Every `Lane` enum value is reachable from at least one registered model | Dead lanes should be removed or populated |
| F4 | `route()` is an `async def` with a `stream: bool` parameter | Contract check for streaming TTFT support |
| F5 | `RouteResult` dataclass exposes `ttft_ms`, `tokens_per_sec`, `latency_ms` fields | Streaming benefits must be observable downstream |
| F6 | `extend_claude()` exists and returns `RouteResult` | User's "extend Claude availability" directive |
| F7 | `HarnessPool.size` reflects the number of installed headless harnesses (pi/opencode/hermes) | Environment-aware pool |
| F8 | All 29 unit tests in `tests/inference/` pass | Baseline correctness |
| F9 | `check_fleet()` returns a `FleetHealth` with exactly 7 lanes (npu, igpu_rocwmma, igpu_unified, cpu, ollama, claude, gemini) | Schema stability |
| F10 | `_dispatch_headless_cli()` handles both `Lane.CLOUD_CLAUDE` and `Lane.CLOUD_GEMINI` | Symmetric headless-CLI dispatch |

### 2.3 Acceptance criterion

`make vmodel-phase1` runs the harness; exit 0 confirms all 10 invariants hold
on the currently-checked-in code. If the harness fails, the registry or fleet
has drifted from the contract and must be fixed before Phase 2 is run.

## 3. Apex

Already shipped — `src/cohezion/inference/` with 29 tests. Harness is the
retrofit that gate-keeps future changes.

## 4. Ascending Path

- **Unit** → `phase1_inference_harness.py` + existing pytest suite
- **System** → `make demo-universes` (end-to-end agent-style round-trip)
- **Acceptance** → `vmodel_acceptance.py` logs `{name: 'inference', status: 'verified'}` to SurrealDB

## 5. Out of scope

- Benchmark numbers (that is Phase 2)
- iGPU/CPU Lemonade lane liveness (that is fleet ops)
- TurboQuant MXFP4 activation on iGPU (pending lemond restart + model load)
