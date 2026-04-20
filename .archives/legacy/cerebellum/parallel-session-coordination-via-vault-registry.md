---
title: "Parallel Session Coordination via Vault Registry"
date: 2026-03-05
tags: [pattern, parallel-sessions, coordination, vault]
aspect: thinker
neural:
  activation: 0.68
  stage: embryo
  synapse_in: 1
  synapse_out: 2
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

## Registry Schema (SurrealDB)

```surql
DEFINE TABLE session SCHEMAFULL;
DEFINE FIELD session_id   ON session TYPE string;
DEFINE FIELD branch       ON session TYPE string;
DEFINE FIELD owned_paths  ON session TYPE array;
DEFINE FIELD phase        ON session TYPE string;   -- research | implement | review
DEFINE FIELD status       ON session TYPE string;   -- active | paused | complete | crashed
DEFINE FIELD heartbeat    ON session TYPE datetime;
DEFINE FIELD context_pct  ON session TYPE float;    -- 0–100, from cz context --json
DEFINE FIELD continuation ON session TYPE option<string>; -- path to continuation file

-- Mark a session as owning a path
RELATE session:abc123 -> owns -> file:cortex/new-note.md;
```

The `heartbeat` field is updated every N tool calls. Sessions with heartbeats older than 30 minutes are treated as crashed and their locks released automatically.

## Conflict Resolution Algorithm

1. **Query**: `SELECT * FROM session WHERE status = 'active' AND owned_paths CONTAINS $target_path`
2. **Owner exists?**
   - **Same session ID** → proceed
   - **Different session, heartbeat < 30min** → defer; write intent to `thalamus/` for the owner to pick up
   - **Different session, heartbeat ≥ 30min** → assume crashed; claim the path, log takeover to `hippocampus/`
3. **No owner** → claim the path with `vault_push_session_state`

## Failure Modes

| Failure | Symptom | Recovery |
|---------|---------|----------|
| Session crashes mid-write | Stale `owned_paths` lock never released | Heartbeat timeout (30 min) auto-releases; next session reads continuation file |
| Two sessions claim the same path simultaneously | Duplicate content, merge conflict | Use SurrealDB `IF NOT EXISTS` check on `owns` relation to prevent race condition |
| Continuation file not written before context fills | Work state is lost | Enforce `context_monitor.py` hook at 80% to trigger early write |
| Session ID collision (two `pid-<PID>` sessions) | Registry thinks one session is two | Use `COHEZION_SESSION_ID` env var (UUID) instead of PID-based fallback |

## Handoff Protocol

When a session hits 80% context:

1. Write current `owned_paths`, in-progress task, and `next_steps` to `continuation.md`
2. Update `vault_push_session_state(status="paused", context_pct=82)`
3. Release non-critical path locks (`REMOVE relation session:id -> owns -> file:path`)
4. Retain locks on actively-written files until the next session claims them

The successor session starts by reading `continuation.md`, then calling `vault_query_active_sessions()` to see what paths it inherits.

## When to Use

- Running multiple Claude Code terminals simultaneously
- Long-running tasks that span multiple context windows
- Team environments where multiple agents work on the same vault
- Multi-agent mission coordination (e.g., `missions/` directory workflows)

## Cohezion Relevance

This pattern is the operational foundation for Cohezion's parallel agent teams — the strategy used in the vault densification sprint (2026-03-03) where 5 parallel agents coordinated without file conflicts. Without a shared registry, parallel sessions either serialize unnecessarily or produce merge conflicts. The vault-as-registry approach leverages the existing SurrealDB graph infrastructure rather than introducing a separate coordination layer.

## Related

- [[2026-03-05-vault-first-enforcement-protocol]] — the enforcement protocol that mandates vault-based state tracking
- [[2026-02-11-vault-first-knowledge-architecture]] — the architectural decision behind vault-first
- [[multi-agent-systems]] — coordinating multiple specialized agents is the broader pattern this enables
- [[cloud-vault-mcp]] — the MCP server that provides `vault_push_session_state` and `vault_query_active_sessions`
- [[surrealdb]] — the graph database backing the session registry
- [[workflow-orchestration]] — sequencing and parallelizing agent tasks across pipelines
- [[context-management]] — context window limits are the primary trigger for state handoff
