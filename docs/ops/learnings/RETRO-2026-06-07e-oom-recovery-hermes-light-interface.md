---
date: 2026-06-07
kind: retro
thread: [ops, fleet, hermes, oom]
prompted_by: retro-watch ([retro:due], 12 tasks) + user "this is exactly the experiential learnings we need to capture"
status: captured
folds_into_skill: hermes-local-inference-routing (rule 12 + rule 11 addendum)
related: RETRO-2026-06-07c-bwrap-systemd-boundary.md
---

# Retro — OOM recovery → fleet truth → hook/trigger audit → Hermes light-interface

A generative local-inference request (SD-Turbo image-gen) OOM'd the box into swap-thrash
livelock (hard reset). The recovery arc produced several durable, *measured* learnings and
one honest self-correction. Skill capture: `hermes-local-inference-routing` rule 12.

## What was verified (live, not theorized)

1. **ctx_size/KV-cache dominates footprint, not param count.** Qwen3.6-35B-A3B at `ctx_size=0`
   (full ~128K) = ~31 GB; Granite-4.1-8B at `ctx_size=16384` + q8_0 KV = ~5 GB. "Lighter model"
   means *bounded context + KV quant*, not just fewer params. Verify via `/api/v1/health` →
   `recipe_options.ctx_size` per loaded model.

2. **The Hermes watcher no longer pins the model.** A 693-line churn renamed
   `apply_tunings`→`apply_targets()`; it pins compression/memory/delegation/browser/terminal/
   display/aux-providers but NOT `model.default`/`cheap_model`. The harness "line 126 pins the
   35B" claim is stale. Durable model swap = re-add the pin (both paths) via `config.setdefault`.

3. **Unload doesn't stick while the gateway runs** — the model reloads on demand because config
   still names it. The fix is the config (both `model.default` AND `smart_model_routing.cheap_model`),
   landed with `stop → detect_hermes_change.py --auto-apply → start → unload`.

4. **`lemonade` is a CLIENT, not a server launcher; the live fleet is router-centric.** No
   `serve`/`daemon` subcommand. `lemonade load --port 13307` talks to a server that must already
   exist there; if none → empty-log no-op. One Lemonade Server on :13305 serves the whole catalog
   on demand + dispatches to NPU/GPU. Dedicated :13307/:13309 instances are redundant and ADD
   resident memory — wrong post-OOM. Doc-drift vs harness N1/N2 + `local-inference-default.md`.

5. **No auto-fire hook caused the OOM.** Hook/trigger audit (`docs/audits/HOOK_TRIGGER_AUDIT_2026-06-07.md`):
   `lemonade-warmup.sh` caps at the 1B and exits-on-down; the OOM came from an *interactive*
   generative load that nothing gated. The real gap: no pre-load `MemAvailable` gate on
   big/generative loads (proposed wiring A in the audit; not yet applied).

## The self-correction (the valuable part)

I initially wrote into the skill that "the `!` session shell is reaped like the Bash tool" — to
explain why the user's `! nohup lemonade load --port 13307 &` left an empty log. **That mechanism
was never verified and contradicts RETRO-2026-06-07c (which proved `!` runs in the user's own
session, outside bwrap).** The empty log is fully explained by #4 — a client call to a nonexistent
server no-ops instantly. A backgrounded *client no-op* and a *reaped server* are log-indistinguishable;
the parsimonious + prior-verified explanation wins. **Caught it at retro time by reading the adjacent
retro before persisting** — exactly why the "check existing knowledge" step exists. Skill rule 11
addendum was rewritten to the honest version.

## Reusable rules

- When a launch leaves an **empty log**, first ask "does this command even target a live server?"
  before blaming process lifecycle.
- "Less resource-intensive" for local LLM = **bounded ctx + KV quant**, verified at the health
  endpoint — not a param-count guess.
- A config change to a watcher-governed bot must pin the value in the watcher, or the write-back
  race reverts it; land it `stop → apply → start`.
- Read the adjacent/related retro before persisting a new mechanism claim — it catches overclaims.
