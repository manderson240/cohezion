# Submission Hardening — uipath-maestro (deadline Jun 29)

Lessons from the Nemotron Kaggle deadline run (2026-06-15). See the global skill
`local-inference-hackathon-hardening` for full rationale.

## Done (additive, no behavior change by default)

- **`shared/cohezion_bridge.py` gained `complete_with_fallback()`** (NPU→iGPU→CPU→omni→cloud,
  empty-as-escalation, returns `(text, backend)`) and **`complete_omni()`** (vision +
  tool-calling models on `:13305` — `Gemma-4-E4B` / `Gemma-4-31B` / `Llama-4-Scout-17B`,
  optional image input). N3-safe. Verified live on `Gemma-4-E4B-it-GGUF`.

## REVIEW — honesty gap (your call; affects the "$0/loop" claim)

Agents generate via **cloud Anthropic** (`self._client.messages.create(...)` —
`orchestrator_agent.py:114`, `engineer_agent.py:185/237`, `analyst_agent.py:174`), while
`engineer_agent.py:137` sets `implementation["cohezion_cpu_tier_used"] = cpu_used` from a
reachability probe. Resolve by either (1) routing generation through
`bridge.complete_with_fallback(prompt, cloud_fn=<anthropic call>)` behind a
`COHEZION_LOCAL_FIRST` flag and reporting the returned `backend`, or (2) reporting an honest
`generation_backend` instead of labeling reachability as "used". Task-appropriate routing
(structured codegen → cloud) is legitimate; just don't claim local while calling cloud.

## Pre-submit checklist

- [ ] Output artifacts COMPLETE before judging (no mid-stream-empty false negatives).
- [ ] Baseline Maestro-case flow runs end-to-end and is captured (bank the floor).
- [ ] OOM-safe: omni via `:13305` only (bounded-ctx models); no `ctx_size=0` heavy load.
- [ ] Empty local responses escalate; no retry-loop.
- [ ] Reported backend/cost matches what actually ran (resolve the REVIEW item).
