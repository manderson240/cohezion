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

## REVIEW — honesty gap (your call; affects the "$0/loop on AMD silicon" claim)

The agents currently generate via **cloud Anthropic** (`self.client.messages.create(...)` in
`agents/*.py`), while `engineer_agent.py:83` sets
`implementation["cohezion_cpu_tier_used"] = self.bridge.lemonade_available("cpu")` — that flag
reports tier *reachability*, not that the tier *generated* anything. So the artifact can claim
"cpu tier used" / "$0/loop" while the work ran on cloud.

Two honest options:
1. **Make the claim true** — route generation through `bridge.complete_with_fallback(prompt,
   cloud_fn=lambda p: <anthropic call>)` and set the metric from the returned `backend`. Gate
   behind an env flag (e.g. `COHEZION_LOCAL_FIRST`) so the default demo path is unchanged.
   Note: local SLMs produce lower-quality *structured JSON* than Claude, so task-appropriate
   routing (classify→NPU, structured codegen→cloud) is legitimate — don't force local on codegen.
2. **Make the metric honest** — report `generation_backend: "anthropic-cloud"` (or the actual
   backend) instead of labeling a reachability probe as "used".

## Pre-submit checklist

- [ ] Every output artifact is COMPLETE before judging it (no mid-stream-empty false negatives).
- [ ] A working baseline demo runs end-to-end and is captured (bank the floor first).
- [ ] Inference is OOM-safe: omni via `:13305` only (bounded-ctx models); no `ctx_size=0` heavy load.
- [ ] Empty local responses escalate; no retry-loop.
- [ ] Reported backend/cost matches what actually ran (resolve the REVIEW item above).
