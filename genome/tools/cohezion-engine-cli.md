---
title: "Cohezion Engine CLI (cz)"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, tool, cli, cohezion-engine]
source: "tools/cohezion-engine/"
status: active
aspect: knower
neural:
  activation: 0.370
  stage: embryo
  cluster: specs
---

# Cohezion Engine CLI (`cz`)

> [!abstract] Purpose
> Workflow CLI for session management, context monitoring, worktree isolation, and plan lifecycle. Installed at `~/.local/bin/cz`.

## Install

```bash
cd tools/cohezion-engine && uv pip install -e .
```

## Commands

### Session & Context

| Command | Purpose |
|---------|---------|
| `cz context --json` | Get context usage percentage (OK/WARNING/CLEAR_NEEDED) |
| `cz session status --json` | Show session ID and directory |
| `cz session send-clear <plan.md>` | Trigger continuation with plan context |
| `cz session send-clear --general` | Trigger continuation without plan |

### Worktree Management

| Command | Purpose |
|---------|---------|
| `cz worktree detect --json <slug>` | Check if worktree exists |
| `cz worktree create --json <slug>` | Create worktree on new branch |
| `cz worktree diff --json <slug>` | List changed files vs base |
| `cz worktree sync --json <slug>` | Squash merge to base branch |
| `cz worktree cleanup --json <slug>` | Remove worktree and branch |
| `cz worktree status --json` | Show active worktree |

### Plan Lifecycle

| Command | Purpose |
|---------|---------|
| `cz plan register <path> <status>` | Associate plan with session |
| `cz plan status --json` | Show current plan |

### Status

| Command | Purpose |
|---------|---------|
| `cz status --json` | Version and config dir |
| `cz --version` | Version number |

## Session Identity

- Uses `COHEZION_SESSION_ID` env var (falls back to `pid-<PID>`)
- Session directory: `~/.cohezion-engine/sessions/<id>/`
- Continuation file: `~/.cohezion-engine/sessions/<id>/continuation.md`

## Related

- [[2026-03-05-vault-as-system-of-record]] — Why this spec is in the vault
- [[compound-engineering]] — CLI supports the compound engineering workflow
