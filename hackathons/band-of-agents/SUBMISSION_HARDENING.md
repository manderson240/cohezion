# Submission Hardening — band-of-agents (deadline Jun 19)

Lessons from the Nemotron Kaggle deadline run (2026-06-15), applied to this local-inference
submission. See the global skill `local-inference-hackathon-hardening` for the full rationale.

## Done (additive, no behavior change by default)

- **`shared/cohezion_bridge.py` gained `complete_with_fallback()`** — local-first
  NPU→iGPU→CPU→omni-router→cloud, with empty-response-as-escalation (an empty local reply
  escalates; it is never retry-looped). Returns `(text, backend)` so callers can report the
  backend that ACTUALLY served the request.
- **`complete_omni()`** — routes to the fleet's OMNI (vision + tool-calling) models on the
  `:13305` router (`Gemma-4-E4B`, `Gemma-4-31B`, `Llama-4-Scout-17B`), supports an optional
  image. Verified live: `complete_omni("Reply with OK")` → `Gemma-4-E4B-it-GGUF` → "OK".
  N3-safe (these models are bounded-ctx / no-KV-risk; never an unbounded `ctx_size=0` load).

## RESOLVED — the "$0 on AMD silicon" claim is now real

All three agents (orchestrator, analyst, engineer) now generate via a `_generate()` helper that
is **local-first with cloud fallback**: when `COHEZION_LOCAL_FIRST=1`, generation routes to the
fleet's already-loaded OMNI model (`Gemma-4-E4B`, via `:13305`, OOM-safe); an empty local reply
escalates to the cloud model (calibration-as-signal). The serving backend is recorded in
`self._last_backend` and reported HONESTLY:
- `implementation["generation_backend"]` = what ACTUALLY served generation.
- `implementation["cohezion_local_silicon_used"]` = True only when a local backend served it
  (replaces the old `cohezion_cpu_tier_used`, which mislabeled a reachability probe).
- The demo prints the real backend (`Generated on local AMD silicon: Gemma-4-E4B-it-GGUF ($0)`).

Default (`COHEZION_LOCAL_FIRST` unset) keeps the cloud path, so the demo never regresses; set the
flag to showcase genuine $0 local execution. Verified live: orchestrator + engineer served on
`Gemma-4-E4B`; the fallback correctly escalates when a local tier returns empty.

## Pre-submit checklist

- [ ] Every output artifact is COMPLETE before judging it (no mid-stream-empty false negatives).
- [ ] A working baseline demo runs end-to-end and is captured (bank the floor first).
- [ ] Inference is OOM-safe: omni via `:13305` only (bounded-ctx models); no `ctx_size=0` heavy load.
- [ ] Empty local responses escalate; no retry-loop.
- [ ] Reported backend/cost matches what actually ran (resolve the REVIEW item above).
