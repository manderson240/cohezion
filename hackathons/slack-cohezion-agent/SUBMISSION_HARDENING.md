# Submission Hardening — slack-cohezion-agent (deadline Jul 13)

Lessons from the Nemotron Kaggle deadline run (2026-06-15). See the global skill
`local-inference-hackathon-hardening` for full rationale.

## Already good (keep it)

`handlers/ask_handler.py` is **honest and local-first**: it classifies the question, checks
`lemonade_available(tier)`, actually calls `LemonadeClient(tier).complete()`, and only sets
`tier_used` after genuinely using that tier — falling back to cloud (`messages.create`) when
local silicon is offline. This is exactly the integrity bar the other projects need.

## Done (additive)

- **`shared/cohezion_bridge.py` gained `complete_with_fallback()`** (NPU→iGPU→CPU→omni→cloud,
  empty-as-escalation, returns `(text, backend)`) and **`complete_omni()`** (vision +
  tool-calling models on `:13305`, optional image). N3-safe. Verified live on `Gemma-4-E4B`.

## REVIEW — recommended upgrades (improve robustness + capability)

1. **Full escalation, not single-tier:** `ask_handler` picks ONE tier and drops to cloud if
   *that* tier is down. Swap the single `LemonadeClient(chosen_tier).complete(...)` for
   `bridge.complete_with_fallback(question, cloud_fn=<cloud>)` so a down tier escalates
   NPU→iGPU→CPU→omni before paying for cloud. Set `tier_used` from the returned `backend`.
2. **Stale model IDs:** `_TIER_TO_MODEL` lists `deepseek-r1-8b`, which isn't in the live router
   catalog; dedicated ports (13307/09) are often down. The omni path (`:13305`) reaches models
   that are actually loaded — prefer it.
3. **Leverage omni for images:** Slack messages can carry images. `complete_omni(prompt,
   image_url=...)` handles vision via `Gemma-4-E4B` / `Llama-4-Scout` at $0 — a differentiator
   for the MCP-server track.

## Pre-submit checklist

- [ ] Output artifacts COMPLETE before judging.
- [ ] `/cohezion ask` runs end-to-end against the live fleet and is captured (bank the floor).
- [ ] OOM-safe: omni via `:13305` only (bounded-ctx); no `ctx_size=0` heavy load.
- [ ] Empty local responses escalate; no retry-loop.
- [ ] `tier_used` / cost reflects what actually ran (already true in ask_handler — keep it).
