---
type: antigravity-artifact
session_id: 8c5a9d85-c294-4aa3-a0e9-9d2d51a72f9c
date: 2026-03-04
title: "Mcp Optimization Plan"
aspect: doer
neural:
  activation: 0.58
  stage: growing
  synapse_in: 0
  synapse_out: 3
---

# Project: MCP Optimization & Token Reduction

## 1. Discovery: SurrealMCP
- **Why**: Directly interacts with SurrealDB via standard MCP interface.
- **Token Benefit**: Offloads complex SurrealQL construction and graph traversal from the LLM to local tool calls. Instead of me "writing" Python code to query the DB, I call MCP tools.
- **Capability**: Permission-aware, real-time memory management for the FLUME swarm.

## 2. Discovery: FastMCP & Custom Servers
- **Approach**: Build a small, dedicated `SkillMCP` server that provides direct access to the `src/cohezion/skills/` directory.
- **Token Benefit**: Reduces the overhead of me searching, reading, and "thinking" about which skill to use. The MCP server can provide semantic search over skills.

## 3. Implementation Plan
- [x] **Step 1**: Install `surrealmcp` via NPM or Python (done via `npx` in config).
- [x] **Step 2**: Create `config/mcp_config.json` to define the connection strings.
- [x] **Step 3**: Develop a `CohezionSkillMCP` server using the Python MCP SDK to expose FLUME skills as tools.
- [ ] **Step 4**: Measure token savings on a standard 10,000 simulation run.

## Related Vault Notes

- [[cohezion]]
- [[semantic-search]]
- [[surrealdb]]
