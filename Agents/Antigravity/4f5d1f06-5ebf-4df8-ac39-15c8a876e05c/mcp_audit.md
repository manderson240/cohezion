---
type: antigravity-artifact
session_id: 4f5d1f06-5ebf-4df8-ac39-15c8a876e05c
date: 2026-03-04
title: "Mcp Audit"
aspect: doer
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# MCP Server Audit: Cohezion Ecosystem

## Current Servers
| Server | Use Case | Status | Recommendation |
|--------|----------|--------|----------------|
| **CloudRun** | Service deployment | Active | Add multi-project support & automatic resource tagging. |
| **Sequential Thinking** | Complex reasoning | Active | Implement "Dynamic Branching" via `mcp_sequential-thinking`. |

## Missing Gaps (High Priority)
1. **SurrealDB MCP:**
   - **Why:** Allow agents to query/mutate the Knowledge Graph directly via tools rather than wrapper scripts.
   - **Action:** Integrate an existing SurrealDB MCP or create a capability-based wrapper.
2. **Gmail/Communication MCP:**
   - **Why:** Robust handling of Inbox Mining and Command Listener.
   - **Action:** Evaluate `gmail-mcp` for secure OAuth-based access.
3. **DePIN Monitor MCP:**
   - **Why:** Real-time visibility into Akash/Grass/Render earnings.
   - **Action:** Create custom MCP for resource yield tracking.

## Improved Tooling Strategy
- **Context Injection:** MCPs should automatically inject relevant **12D PhysicsState** metadata when interacting with the filesystem or database.
- **Safety Layer:** Integrate `cohezion.security.prompt_guard` as an MCP middleware.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
