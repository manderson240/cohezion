---
title: "System Card: Cohezion Engine CLI"
date: 2026-03-05
version: 1
last_revised: 2026-03-05
tags: [spec, system-card, cli, tooling, infrastructure]
card_type: system
status: active
aspect: knower
neural:
  activation: 0.7
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# System Card: Cohezion Engine CLI

> [!abstract] Summary
> The `cz` CLI is the cohezion-engine workflow tool managing session identity, context monitoring, worktree isolation, and plan lifecycle for /spec-driven development. It provides the plumbing that makes cross-session continuity and isolated implementation branches work.

## Identity

| Field | Value |
|-------|-------|
| **Component** | Cohezion Engine CLI (`cz`) |
| **Type** | CLI |
| **Owner** | Cohezion platform team |
| **Status** | active |
| **Version** | See `cz --version` |
| **Source** | `tools/cohezion-engine/` in vault repo |
| **Deployed As** | pip package (`uv pip install -e .`) |

## Connection Details

| Field | Value |
|-------|-------|
| **Binary** | `~/.local/bin/cz` |
| **Config Dir** | `~/.cohezion-engine/` |
| **Session Dir** | `~/.cohezion-engine/sessions/<session-id>/` |
| **Protocol** | Local filesystem + subprocess |

## Dependencies

| Dependency | Type | Required | Notes |
|-----------|------|----------|-------|
| Python 3.10+ | runtime | Yes | Via uv |
| uv | build | Yes | Package management |
| git | runtime | Yes | Worktree operations |
| Claude Code | integration | Yes | Session context (env vars) |

## Capabilities

### What It Does
- **Session management:** Track session identity via `COHEZION_SESSION_ID` env var
- **Context monitoring:** Report context usage percentage, trigger continuations at 80%/90%
- **Worktree isolation:** Create, detect, diff, sync, cleanup git worktrees for /spec implementation
- **Plan lifecycle:** Register plans with sessions, track status (PENDING/COMPLETE/VERIFIED)
- **Continuation protocol:** Write trigger files for session restarts

### What It Does NOT Do
- Does not modify vault notes (that's agent + MCP tools)
- Does not run tests (that's the test framework)
- Does not manage git commits (that's the agent following git rules)

## Command Reference

| Command | Purpose |
|---------|---------|
| `cz context --json` | Context usage percentage |
| `cz session status --json` | Session ID and directory |
| `cz session send-clear <plan>` | Trigger continuation with plan |
| `cz session send-clear --general` | Trigger continuation without plan |
| `cz worktree create --json <slug>` | Create isolated worktree |
| `cz worktree sync --json <slug>` | Squash merge back to base |
| `cz worktree cleanup --json <slug>` | Remove worktree |
| `cz plan register <path> <status>` | Register plan with session |

See [[cohezion-engine-cli]] for the full command reference.

## Configuration

```bash
# Environment variable (set by Claude Code hooks)
COHEZION_SESSION_ID=<uuid>

# Install
cd tools/cohezion-engine && uv pip install -e .
```

## Monitoring & Health

| Check | Method | Frequency | Alert Threshold |
|-------|--------|-----------|-----------------|
| CLI installed | `cz --version` | Session start | Error if missing |
| Session identity | `cz session status --json` | Session start | Warn if no session ID |
| Context level | `cz context --json` | Via `context_monitor.py` hook | 80% warning, 90% mandatory handoff |

## Known Limitations

- Context percentage is estimated (based on conversation token count)
- Worktree operations require clean working tree
- No Windows support (git worktree + bash dependency)

## Reconstruction Steps

> [!tip] Disaster Recovery
> Steps to rebuild this system from scratch using only vault knowledge.

1. Ensure `tools/cohezion-engine/` exists in vault repo
2. Install: `cd tools/cohezion-engine && uv pip install -e .`
3. Verify: `cz --version && cz status --json`
4. Configure hooks: Copy `context_monitor.py` and `tdd_enforcer.py` to `.claude/hooks/`
5. Set env var in Claude Code settings: `COHEZION_SESSION_ID`

## Security Considerations

- Local-only tool — no network access
- Session files stored in user home directory
- No secrets managed by this tool

## Related

- [[cohezion-engine-cli]] — Full CLI command reference in `specs/tools/`
- [[context-management]] — Concept note on context engineering
- [[2026-03-05-vault-as-system-of-record]] — ADR establishing specs directory

## Revision History

| Version | Date | Change |
|---------|------|--------|
| 1 | 2026-03-05 | Initial system card |
