---
title: "Parallel Session Coordination via Vault Registry"
date: 2026-03-05
tags: [pattern, parallel-sessions, coordination, vault]
aspect: thinker
---

# Pattern: Parallel Session Coordination via Vault Registry

## Problem

Multiple Claude Code sessions running in parallel (e.g., one doing research, another implementing a feature) can conflict — editing the same files, duplicating work, or losing state when one session's context window fills up.

## Solution

Use the vault as a shared registry for session state. Each session registers itself, declares its active files/branches, and checks for conflicts before writing.

Key components:
- **Session registration** at start (`track_session` in SurrealDB or `vault_push_session_state`)
- **File lock declaration** — each session declares which files/directories it owns
- **Conflict check** before writing — if another session owns a file, defer or coordinate
- **State handoff** — when one session hits context limits, it writes full state to the vault for the next session to pick up

## Code Example

```python
# Session start
vault_push_session_state(
    session_id="abc123",
    branch="track-c",
    owned_paths=["cortex/", "sensory/"],
    phase="research",
    status="active"
)

# Before writing a file
active_sessions = vault_query_active_sessions(path="cortex/new-note.md")
if active_sessions and active_sessions[0].session_id != my_session_id:
    # Another session owns this path — coordinate or defer
    pass
```

## When to Use

- Running multiple Claude Code terminals simultaneously
- Long-running tasks that span multiple context windows
- Team environments where multiple agents work on the same vault

## Related

- [[2026-03-05-vault-first-enforcement-protocol]] — the enforcement protocol that mandates vault-based state tracking
- [[2026-02-11-vault-first-knowledge-architecture]] — the architectural decision behind vault-first
