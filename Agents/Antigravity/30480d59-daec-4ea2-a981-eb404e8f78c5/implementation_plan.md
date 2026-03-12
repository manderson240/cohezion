---
type: antigravity-artifact
session_id: 30480d59-daec-4ea2-a981-eb404e8f78c5
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.334
  stage: embryo
  cluster: Agents
---

# Memory Recovery Protocol (MRP)

Establish a standardized process for agents to "wake up" and synchronize with the Cohezion project's Collective Memory (Knowledge Graph + SurrealDB) to solve the "initial memory loss" problem.

## User Review Required

> [!IMPORTANT]
> This protocol will add a `RECOVERY_PRIME` skill and a startup check to the `overnight_driver.py` and other entry points.

## Memory Anchor Pattern

To prevent information decay between sessions, Cohezion will utilize a **Memory Anchor**:
1. **The Pulse**: Every 30 minutes, the agent sends a `MISSION_PULSE` to SurrealDB containing the current 12D state and active objectives.
2. **The Handoff**: At the end of a session, a `SESSION_SNAPSHOT` is generated, including a "Key Context" summary (max 500 tokens).
3. **The Wake-Up**: New agents automatically query the latest `SESSION_SNAPSHOT` and `MISSION_PULSE` to hydrate their local context.

### [Knowledge Graph]

#### [NEW] [mrp_protocol.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/mrp_protocol.md)
Document the 5-step synchronization process:
1. READ `GEMINI.md` (Role & Global Rules)
2. READ `KEY_LEARNINGS.md` (Cumulative Wisdom)
3. READ `retrospectives/` (Latest Delta)
4. QUERY `SurrealDB` (Current Live State)
5. BOOT `12D State Vector` (Session Initialization)

### [Skills]

#### [NEW] [RECOVERY_PRIME.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/RECOVERY_PRIME.md)
A new skill that encapsulates the recovery logic, allowing agents to quickly rebuild context.

### [Core]

#### [MODIFY] [agent_manager.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agent_manager.py)
Add a "Recovery Hook" that triggers the MRP on instantiation if the `persist_context` flag is set.

## Verification Plan

### Automated Tests
- Run `tests/test_recovery.py` to ensure the agent can reconstruct a known "lost" state from SurrealDB.
- `uv run pytest tests/test_recovery.py`

### Manual Verification
- Simulate a "memory loss" event (reset session) and verify the agent can correctly identify the current Phase and Gateway status within 3 tool calls.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
