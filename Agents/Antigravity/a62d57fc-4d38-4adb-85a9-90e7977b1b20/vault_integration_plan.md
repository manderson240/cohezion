---
type: antigravity-artifact
session_id: a62d57fc-4d38-4adb-85a9-90e7977b1b20
date: 2026-03-04
title: "Vault Integration Plan"
aspect: doer
neural:
  activation: 0.61
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Unifying Cohezion Vault Persistence Plan

We need to provide both **Structured Vault Persistence** (for machine-readable guidance, checkpoints, and patterns) and **Human-Readable Obsidian Retrospectives** (for architectural review).

## Proposed Changes

### [Component] Experience Persistence Layer
#### [MODIFY] [vault.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/exp_persistence/vault.py)
- Restore the `VaultExecutionLogger` contract: `log_execution_start`, `log_execution_result`, `get_experience_guidance`, `extract_execution_pattern`.
- Implement these using the `MCPClient` for structured data.
- Keep the `log_batch` method for Obsidian-specific retrospectives.

### [Component] Session Management
#### [MODIFY] [session_manager.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/session_manager.py)
- Wire up `VaultCheckpointManager` to use `get_mcp_client()`.
- Implement `save`, `load`, and `delete` using `vault_write` and `vault_read`.

### [Component] Compound Persistence
#### [MODIFY] [persistence.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/persistence.py)
- Add `_save_to_vault` and `_load_from_vault` methods to `CompoundPersistence`.
- Ensure multi-tiered persistence: `Vault -> SurrealDB -> JSONL`.

## Verification Plan
1. **Executor Test**: Run a compound task and verify that both a "mission_journey" (SurrealDB) and a "mission_retrospective" (Vault/Obsidian) are created.
2. **Checkpoint Test**: Start a long-running session, trigger a checkpoint, and verify it exists in the Vault (`vault_list checkpoints/`).
3. **Pattern Retrieval**: Verify `executor.py` can fetch guidance from previous runs stored in the Vault.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
