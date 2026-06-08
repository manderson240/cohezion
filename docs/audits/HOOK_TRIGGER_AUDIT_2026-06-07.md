---
type: audit
title: Hook & Trigger Audit
date: 2026-06-07
trigger: post-OOM recovery; user request "we need a hook and trigger audit as part of the loop"
scope: Claude Code hooks (~/.claude/settings.json), hook scripts, agentic trigger signals
  (~/.claude/rules/*.md), git/pre-commit hooks. OOM-risk lens.
status: report-only (no behavior changed)
---

# Hook & Trigger Audit — 2026-06-07

## Why now
A generative-AI-artifacts local-inference request OOM'd the box into a swap-thrash
livelock (hard reset required). This audit answers: **did an auto-firing hook/trigger
cause it, and what auto-fire vectors exist?**

## Headline finding
**No auto-fire hook caused the OOM.** Every inference-firing hook is memory-guarded.
The OOM came from an *interactive* generative load (SD-Turbo image-gen, in the 13305
catalog) that sits in the **one place nothing gates**: there is no pre-load memory
check on large/generative model loads anywhere in the hook chain. This is the same
coverage gap the in-flight registry work (`item 146 — OOM-fallback coverage audit`)
was already reaching toward.

---

## 1. Claude Code hooks (23 entries across 9 events)

| Event | Count | Hooks |
|---|---|---|
| SessionStart | 7 | cwd-guard, check-settings-size, version-watch, _safe_run→repo-health-check, **lemonade-warmup** (async), session-register, autoresearch-session-digest |
| PreToolUse | 3 | pre-bash-check (Bash), bouncer --block (Bash `git push*`), bouncer --shadow-check (Write `*/.claude/skills/*`) |
| PostToolUse | 4 | post-bash-cleanup (Bash), post-edit-lint (Edit\|Write), **bouncer --watch** (Bash\|Write\|Edit, asyncRewake), retro-watch record (TaskUpdate) |
| UserPromptSubmit | 4 | autoresearch-context, **router.py** (async, t=4), session-inbox, retro-watch --emit |
| PostToolUseFailure | 1 | post-tool-failure-logger (async) |
| PermissionDenied | 1 | on-permission-denied |
| PreCompact | 1 | pre-compact-checkpoint |
| PostCompact | 1 | post-compact-context |
| Stop | 1 | autoresearch-stop |

### Inference-firing hooks (the OOM-relevant subset)
| Hook | Fires on | Target | Memory posture |
|---|---|---|---|
| `lemonade-warmup.sh` | SessionStart (async) | NPU 13306 (1B FLM) only; iGPU **exits if 13307 down** | **SAFE** — caps at 1B; never loads a big model |
| `router.py` | every UserPromptSubmit (async, t=4) | NPU classify | SAFE — NPU only, cheap |
| `bouncer.py --watch` | every Bash\|Write\|Edit | iGPU 13307 Gemma-4-E4B; **fail-open if down** | SAFE per-call (~5GB resident); highest-frequency caller |
| `release-notes-parse.py` | SessionStart on version bump | optional Gemma enrichment, capped 5 bullets × 10s | SAFE — bounded |

**None loads SD-Turbo, the 26B, or the 31B.** The warmup hook's iGPU branch
deliberately *exits* rather than loading when 13307 is offline — good design.

---

## 2. Agentic trigger signals (6 distinct)

| Signal | Handler rule | Action | Risk |
|---|---|---|---|
| `[retro:due]` | retrospective-and-persistence.md | run /learn + retro (in-context) | low |
| `[anthropic-intel:stale]` | anthropic-intel-scan.md | **spawn background Agent** (/anthropic-scan) | autonomous fan-out (cloud) |
| `[version-watch:notes-ready]` | anthropic-intel-scan.md | **spawn background Agent** (/release-notes-audit) | autonomous fan-out (cloud) |
| `[version-watch:parsed-ready]` | anthropic-intel-scan.md | read parsed JSON (in-context) | low |
| `[version-watch]` (fallback) | anthropic-intel-scan.md | spawn background Agent | autonomous fan-out (cloud) |
| `[permission-scan:findings]` | anthropic-intel-scan.md | read findings, propose merge (in-context, **no agent**) | low |

Two families auto-spawn **background Claude agents** (cloud, not local silicon → not a
direct OOM vector, but un-gated autonomous fan-out). All 6 signals have a matching
handler rule — **no orphan signals, no orphan handlers**.

---

## 3. Git / pre-commit hooks
- **Active git hooks (8):** commit-msg, post-checkout, post-commit (+`.pre-entire` Entire variant), post-merge, post-rewrite, pre-commit, pre-push, prepare-commit-msg. `pre-commit.disabled` present (inert).
- **pre-commit config:** healthy guard set incl. `check-added-large-files`, `large-artifact-gate`, `lfs-pointer-check`, `detect-secrets`, `bandit`, `kaggle-branch-guard`. These guard *commits*, not *runtime memory*.

---

## 4. THE GAP (actionable)
`pre-bash-check.sh` (the PreToolUse Bash guard, 44 lines) does **not** gate memory or
model loads. So an interactive `lemonade load <26B|31B>` or an SD-Turbo generation runs
**ungated** → exactly the OOM that happened. No hook, invariant, or wrapper checks
`MemAvailable` before a large local load.

### Recommendation A — close the gap (1 file, additive)
Extend `pre-bash-check.sh`: when the Bash command matches `lemonade load <big-model>`
or an SD-Turbo / image-gen invocation, read `/proc/meminfo MemAvailable` and **block
(or warn) if avail < model_size + headroom**. Generalizes registry item 146 from the
*route()* path to the *interactive shell* path. ~15 lines.

### Recommendation B — make the audit recurring ("as part of the loop")
✅ **IMPLEMENTED 2026-06-07** as invariant **HT1** in `harness_check.py`: asserts the only
inference-firing SessionStart hook (`lemonade-warmup.sh`) caps at the 1B NPU model and never
loads a big/generative model (Gemma-4-31B/26B, Qwen3.x-35B, SD-Turbo). WARN-only. Re-runs every
`harness_check.py`. (Future extension: assert every trigger signal has a handler rule — not yet
wired; the current HT1 covers the OOM-relevant vector.)

### Recommendation A — STILL PENDING (higher risk, your call)
The pre-load `MemAvailable` gate in `pre-bash-check.sh` is **not yet implemented** — it runs on
*every* Bash call, so it's the one wiring that warrants explicit sign-off before landing.

Both are additive, gated on approval. No behavior changed by this report.
