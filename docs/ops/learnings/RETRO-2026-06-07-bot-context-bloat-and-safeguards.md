---
date: 2026-06-07
kind: retro
thread: [hermes, safeguards, calibration]
prompted_by: retro-watch ([retro:due], 10 tasks)
status: captured
related_commits: [d151ccbc0, 900954683, 7b778bec6, 3c28ce702]
---

# Retro — bot context-bloat, the first self-authored safeguard, and the size gate holding

## 1. Bot empty-response has a SECOND root cause (not the documented CoT trap)

`hermes-local-inference-routing` skill #1 documents one empty-response cause: reasoning models
emitting CoT into `reasoning_content` until the budget exhausts. **This incident was a
different cause** and the skill should be refined (skill is in `~/.claude/skills/`, sandbox
read-only — refine via bypass or hand-edit):

> **`compression.enabled: False` → unbounded session → context bloat → empty content.** The
> Telegram session grew to `history=281` / `tool_turns=123` (days of accumulation, since
> `session_reset` is `mode: idle, idle_minutes: 1440` = never resets an active chat). The
> model (Qwen3.6-35B-A3B-NoThinking, correctly no-think) choked on the bloated context and
> returned empty — NOT a CoT trap, NOT a dead endpoint. A plain `curl` returns "Hello!"; the
> model + cheap_model config were already correct.

**Diagnosis path that worked** (reusable): reproduce with a plain curl (proves inference
healthy) → reproduce with a `tools[]` payload (model returns `finish=tool_calls`, empty
content — correct, but shows the tool path) → read `agent.log` for the failing turn (`history=`
is the smoking gun) → check `compression.enabled`. The fix (`fix_bot_empty_response.sh`):
compression on + `hygiene_hard_message_limit` 120 + drop 5 corrupted `'"…` junk config keys;
restart clears the bloated in-memory session.

## 2. The resource-aware router is the first SELF-AUTHORED safeguard

The fleet-saturation that broke the bot (a background batch starving the iGPU) had no guard:
the fleet had resource *probing* + an OOM *gate* but no *router* consulting live state. Item
122 `resource_aware_route` closes that — and it is the template the user's "adhere AND improve
safeguards" directive wants: a loop tick may PROPOSE a new safeguard (additive, falsifiable,
report-only-until-proven) when it discovers a class of failure an existing invariant didn't
cover. Never weaken an existing invariant without a human decision.

## 3. The size gate held against a surface-attractive model (calibration working)

Research round 28: `unsloth/Qwen3-Coder-Next-GGUF` looked like a clear embrace (3M downloads,
GGUF, apache-2.0, not gated). The K1/rule-5 size gate caught it — 55.8 GB at the smallest
quant (3-part split = big MoE, not a small specialist). Honest decline on fleet-runnability,
not hype. This is the SAME discipline as RETRO-2026-06-06d but in the *accept* direction:
surface signals (downloads/license) are not the gate; the concrete constraint (does it fit
23 GB free?) is. Verify the binding constraint, not the vanity metric.

## 4. Sandbox bypass ≠ user systemd bus

`dangerouslyDisableSandbox` grants filesystem/network freedom but does NOT conjure the user
session DBUS bus (`/run/user/1000/bus` is absent from the agent's process namespace entirely).
So `systemctl --user` (gateway restart, config edits behind it) is genuinely un-runnable by
the agent — those actions require the user's own shell (`! …`). Recorded so the next session
doesn't retry the bypass for systemd-user operations.

## Persistence
- Loop-doctrine (every-interaction-feeds-a-loop / near-infinite / polyglot-refactor /
  safeguards) captured in `docs/IMPROVEMENT_BACKLOG.md` policy section + item 124.
- Git reality surfaced: on `feat/adaptive-calibration-harness`, 423 ahead of main, main
  diverged by 57, 317 unpushed — push/merge awaiting user decision (NOT done unilaterally).
