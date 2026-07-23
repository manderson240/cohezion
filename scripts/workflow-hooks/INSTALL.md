# Branch-landing hooks — install

Built + tested 2026-07-23 (13/13 guard/hygiene fixtures pass). Drafted by the local Coder
(:13305), hardened + verified here, design grounded in Ollama-Cloud research on merge queues /
policy-as-code / agent guardrails / semver automation.

The install targets live under `~/.claude/` (read-only to the agent sandbox), so **you** run
these three steps. Everything is deterministic and $0.

## 1. Copy the two hook scripts into place

```bash
mkdir -p ~/.claude/hooks
cp scripts/workflow-hooks/branch-hygiene.sh     ~/.claude/hooks/
cp scripts/workflow-hooks/git-branch-guard.sh   ~/.claude/hooks/
cp scripts/workflow-hooks/land-ready-signal.sh  ~/.claude/hooks/
chmod +x ~/.claude/hooks/branch-hygiene.sh ~/.claude/hooks/git-branch-guard.sh ~/.claude/hooks/land-ready-signal.sh
```

## 2. Wire them into `~/.claude/settings.json`

Add these two entries (merge into the existing `hooks` object — do not replace it). The
guard must run as a **PreToolUse** matcher on `Bash`; the hygiene signal on **SessionStart**.

```jsonc
// under "hooks":
"SessionStart": [
  // ...existing entries...
  { "hooks": [ { "type": "command", "command": "/home/mike-anderson/.claude/hooks/branch-hygiene.sh" } ] }
],
"PreToolUse": [
  // ...existing entries...
  { "matcher": "Bash",
    "hooks": [ { "type": "command", "command": "/home/mike-anderson/.claude/hooks/git-branch-guard.sh" } ] }
],
"Stop": [
  // ...existing entries...
  { "hooks": [ { "type": "command", "command": "/home/mike-anderson/.claude/hooks/land-ready-signal.sh" } ] }
]
```

> Note: `settings.json` is on the sandbox deny-list, and a SessionStart hook
> (`check-settings-size.sh`) validates it — if it reports `[settings-check:FAIL]`, fix that
> first. The guard exits `2` to BLOCK a tool call (stderr shown to the model), `0` to allow.

## 3. Install the reacting rule

```bash
cp scripts/workflow-hooks/branch-landing-protocol.md ~/.claude/rules/
```

The rule tells the agent how to react to `[branch-hygiene]` and (future) `[land:ready]`.

## Verify after install

```bash
# guard blocks a main push, allows a feature push:
printf '{"tool_input":{"command":"git push origin HEAD:main"}}'      | ~/.claude/hooks/git-branch-guard.sh; echo "exit=$? (want 2)"
printf '{"tool_input":{"command":"git push origin feat/x"}}'         | ~/.claude/hooks/git-branch-guard.sh; echo "exit=$? (want 0)"
# hygiene emits when adrift:
CLAUDE_PROJECT_DIR="$PWD" ~/.claude/hooks/branch-hygiene.sh   # prints [branch-hygiene] ... when on main or >=5 ahead
```

## Behavior summary

| Hook | Event | Effect | Cost |
|---|---|---|---|
| `git-branch-guard.sh` | PreToolUse[Bash] | Blocks commit-on-main + direct push-to-main (exit 2). `CZ_ALLOW_MAIN=1` overrides. | $0, deterministic |
| `branch-hygiene.sh` | SessionStart | Emits `[branch-hygiene]` when on main or ≥5 ahead | $0, deterministic |
| `branch-landing-protocol.md` | rule | Reacts: branch-split proposal; the gated `[land:ready]` local→cloud landing pipeline | inference only in the review gate |

## Escape hatch

For a deliberate, human-authorized main write, set it in the **session/shell that launches
Claude Code** (or the hook's env): `CZ_ALLOW_MAIN=1`. Note (verified): an *inline*
`CZ_ALLOW_MAIN=1 git push …` inside a tool command does **not** bypass — the hook reads its
own environment, and Bash tool calls don't persist env — so the hatch is human-controlled,
not agent-settable. When it fires, the guard logs an audit line to stderr.

## Adversarial review (2026-07-23) — 4 independent perspectives

Reviewed by 3 local lenses (:13305 — bypass/security via Qwen3-Coder-30B, bash/fail-mode via
Qwen3-Coder-30B, design/guarantees via Gemma-4-E4B) + 1 Ollama-Cloud holistic pass. Producer
did not self-sign; every finding was re-verified against the code before accept/reject.

**Fixed + regression-tested (24 fixtures green across 3 rounds):** `git -c key=val push`
anchor bypass; `+main` force refspec; chained `; git push origin main`; `git push
--all`/`--mirror`; `git push origin refs/heads/main` full-ref; quoted `"main"`/`'main'`;
`CZ_ALLOW_MAIN` now audits to stderr (not silent).

**Overstated — verified already-caught:** `sh -c '…git push…'`, `@:main`, `HEAD~1:main`
(the git command is textually present, so the refspec/positional greps already block).

**Documented residual (threat-model boundary, NOT fixed by design):** base64/eval obfuscation,
git aliases hiding a push, plumbing (`commit-tree`+`update-ref`), `-C`/`GIT_DIR` targeting
another repo, and a subprocess that runs git internally. A command-string guard cannot stop a
determined/compromised actor — that is what **server-side branch protection (GitHub rulesets)
+ a git-native pre-push hook** are for. This hook is the cheap, deterministic *honest-agent*
guardrail; pair it with the server-side layer for a real security boundary.
