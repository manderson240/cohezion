---
description: "Mandatory dual-store persistence to SurrealDB port 8001 and Obsidian Vault"
globs: ["src/cohezion/agi/recursive_learning.py", "src/cohezion/knowledge_graph/**", "src/cohezion/data_mesh/**"]
alwaysApply: true
---

# Rule: Dual-Store Persistence

## Triggers
- Retrospectives, key learnings, kanban task updates, and recursive learning cycles.

## Enforced Behavior
1. **SurrealDB Primary**: All structured telemetry, kanban items, and learning cycles must write to SurrealDB (`http://localhost:8001`, namespace `cohezion`, database `main`).
2. **Obsidian Vault Mirror**: All markdown learnings and decisions must be written to `~/vaults/cohezion-vault/` (`01-Learnings/` and `kanban/`).
3. **No Ephemeral Drift**: Never rely solely on in-memory conversation context across sessions.
4. **WAL Fallback Safeguard**: If SurrealDB is unreachable, append to local WAL (`~/.cohezion/wal/learning_cycles.jsonl`) and alert for backfill.
