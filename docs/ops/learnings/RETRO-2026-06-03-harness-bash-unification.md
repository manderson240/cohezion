---
type: retro
date: 2026-06-03
session: harness-bash-unification
tags: [harness, claude-code, pi, hermes, bwrap, mcp, sandbox, tool-use, env-var, ouroboros, mycelium]
commits: [pending]
methodology: [diagnose-first, autoharness-update, ouroboros-failure-analysis, mycelium-clustering]
related: [claude-code-bwrap-sandbox-missing-bind]
---

# RETRO 2026-06-03 — Harness bash unification: every agent must be able to run shell

## What shipped

Three independent bash blockers, one per Cohezion harness, surfaced during a
real end-to-end deployment via `scripts/ci/deploy_harness_agents.sh` —
launching one verification agent per harness in detached tmux sessions and
running the harness check. The deployment succeeded, but the three agents
returned three different failures, each pointing at a distinct bash-unfriendly
condition in the harness integration.

This retro consolidates the three findings, captures the one fix (Claude),
and emits the second/third as durable observations for follow-up.

## The 3 findings (verbatim agent reports)

### 1. Claude Code — `bwrap: Can't create file at /opt/rocm: No such file or directory`
- **Status:** FIXED.
- **Root cause:** `LD_LIBRARY_PATH` contained 3 non-existent directories
  (`/usr/lib/mesa-diverted/x86_64-linux-gnu`,
  `/usr/lib/x86_64-linux-gnu/mesa`, `/usr/lib/x86_64-linux-gnu/gallium-pipe`).
  Claude's bubblewrap sandbox bind-mounts each colon-separated entry and
  fails on the first missing one. Earlier diagnosis (in the existing
  `claude-code-bwrap-sandbox-missing-bind` skill) attributed this to
  `ROCM_PATH=/opt/rocm`, but the actual env var was `LD_LIBRARY_PATH`.
- **Fix:** `~/.config/cohezion/safe-env.sh` strips any colon-separated
  entry that doesn't resolve to an existing path from
  `LD_LIBRARY_PATH / PATH / PYTHONPATH / ROCM_PATH / HIP_PATH / CUDA_PATH`
  before Claude spawns subprocesses.
- **Verification:** `source ~/.config/cohezion/safe-env.sh && claude --print
  "bash -c 'cd /home/mike-anderson/dev/cohezion && python3 .claude/rules/
  harness_check.py --fast'"` now returns the harness check output (was
  failing with bwrap error before).
- **Skill refined:** `claude-code-bwrap-sandbox-missing-bind` updated with
  the actual culprit (`LD_LIBRARY_PATH`, not `ROCM_PATH`) and a
  deployment-script-aware guard pattern.

### 2. Pi 0.78.0 — harness check legitimately fails on pre-existing format/lint drift
- **Status:** DOCUMENTED, not fixed (out of scope this session).
- **Root cause:** `python3 .claude/rules/harness_check.py --fast` returns
  exit 1 because ruff format check finds 9 files needing reformat in
  `src/`, and ruff quick-lint finds 625 errors across the same.
- **Scope of drift:** pre-existing on `feat/adaptive-calibration-harness`
  branch before any of this session's work. Not introduced by the harness-
  alignment commits. The agent did its job correctly — it ran the check
  and honestly reported the failure.
- **Next step:** A separate `make format && make lint` sweep on the branch
  is needed before harness_check.py can be relied on for agent verification.
  Tracked as `WS-pre-existing-drift-cleanup`.

### 3. Hermes — `mcp_cohezion_cohezion_run_cli` wraps every bash call with `python -m cohezion …`
- **Status:** DOCUMENTED, not fixed (out of scope this session).
- **Root cause:** `~/.hermes/config.yaml` line 651–658 defines a `cohezion`
  mcp_server that exposes `run_cli`, which unconditionally prefixes every
  command with `python -m cohezion`. Hermes's MCP integration routes all
  bash through that tool, so any `python3 script.py` or `bash -c '...'` is
  transformed into `python -m cohezion script.py` and rejected as an
  unknown cohezion subcommand.
- **Workarounds tried by the Hermes agent:** (a) raw `python3 …` → prefixed;
  (b) `bash -c "python3 …"` → still prefixed; (c) `python3 -e
  'subprocess.run(...)'` → still prefixed.
- **Next step:** Two viable fixes, not applied here:
  1. Add a second mcp_server entry to `~/.hermes/config.yaml` for raw bash
     (e.g. an open `mcp-server-bash` if it exists for Hermes's tool surface,
     or a thin custom shim that runs the command unmodified).
  2. Modify `cohezion.mcp.servers.cohezion.run_cli` to detect a `!raw`
     sentinel and bypass the prefix.
  Tracked as `WS-hermes-mcp-raw-bash`.

## Why this matters (high-level)

- The three harnesses are not equivalent for shell-bound verification work.
  Before this session, the asymmetry was latent: claude/pi/hermes had
  different MCP server sets, different skills coverage, and different
  harness-rule sets, but all of those were caught by the prior session's
  WS1–WS4 work. The shell-bind asymmetry only surfaces when you actually
  try to run a command from each.
- `scripts/ci/deploy_harness_agents.sh` is now a load-bearing tool: any
  regression to the bash guard or to the Hermes MCP wrapper will silently
  break cross-harness verification. The CI workflow should run the deploy
  script in dry-run periodically and fail if a harness can't reach bash.
- The user's request — "every harness needs to be able to use bash" — is
  now: claude YES (after fix), pi YES (always was), hermes NO (the MCP
  wrapper is the bottleneck).

## Ouroboros analysis (failure pattern)

`OuroborosFailureAnalyzer.analyze(logs=claude_bwrap_log,
target="claude-bwrap-sandbox-bind")` classified this as a recurring class:
**environment-misconfiguration on shared-dev-machine with stale ROCM /
LD_LIBRARY_PATH exports**. Pattern matches `L392-arc-local-harness-zero-
percent` (also a stale-env-blocked agent invocation) and
`RETRO-2026-04-29-hermes-vault-retrospective` (also a harness-config drift).

## Mycelium cluster

The Mycelium precipitation event `harness-bash-unification-2026-06-03` was
subscribed to cluster `cluster:env-var-bwrap-bind` (id pending — see
ouroboros+mycelium run output). The cluster now contains 3 events with
the same signature: `env_var_contains_missing_path ∧ harness_spawns_bwrap
→ bash_blocked`.

## Decisions

- **Keep the fix minimal.** A shell script (`safe-env.sh`) that runs at
  Claude's parent shell is enough. No need to add a Claude settings.json
  `permissions.disableSandbox` (loses auth) or `--bare` (loses OAuth).
- **Don't auto-apply safe-env.sh to Pi or Hermes.** Pi's bash worked
  throughout (the bwrap issue was Claude-specific). Hermes's bash is
  blocked by a different mechanism (MCP wrapper) and the fix is to add
  raw-bash MCP server, not to strip env vars.
- **Pre-existing format/lint drift stays out of scope for this session.**
  Fixing it requires a `make format && make lint && git add -A && git
  commit` sweep that touches 9 files and would dominate the diff.

## Commits expected

1. `fix(claude): add safe-env.sh to guard LD_LIBRARY_PATH from bwrap bind failure`
2. `docs(ops): capture harness-bash-unification-2026-06-03 retrospective`
3. `feat(skill): refine bwrap-sandbox skill with deployment-script-aware guard`
4. `feat(ouroboros): persist bwrap failure analysis + mycelium cluster registration`

## Follow-ups (queued, not committed)

- `WS-pre-existing-drift-cleanup`: format + lint sweep on the branch so
  harness_check.py --fast passes.
- `WS-hermes-mcp-raw-bash`: add a raw-bash mcp_server to Hermes or
  modify cohezion.run_cli to support a `!raw` sentinel.
- `WS-deploy-script-in-ci`: run `scripts/ci/deploy_harness_agents.sh
  --dry-run` in the skills-sync workflow as a regression gate.
