---
type: antigravity-artifact
session_id: a62d57fc-4d38-4adb-85a9-90e7977b1b20
date: 2026-03-04
title: "Persistence Implementation Plan"
aspect: doer
neural:
  activation: 0.308
  stage: embryo
  cluster: Agents
---

# Swarm Experience Persistence Implementation Plan

To enable true **Compound Engineering**, agents must persistently store their "Journey State" (SurrealDB) and "Architectural Insights" (Vault).

## Proposed Changes

### [Component] Persistence Layer (Accumulator Pattern)
#### [NEW] [persistence_accumulator.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/persistence_accumulator.py)
A non-blocking buffer (`asyncio.Queue`) that manages flushes to SurrealDB and the Vault.

#### [NEW] [journey_persistence.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/journey_persistence.py)
Handles sharded Parquet + SurrealDB checkpoints. Includes schema-versioning for FLUME state vectors.

#### [NEW] [vault_execution_logger.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/compound/vault_execution_logger.py)
Obsidian logger with "Importance Sampling" logic to prevent indexer bloat.

### [Component] Base Agent
#### [MODIFY] [base.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/agents/base.py)
Hook `_call_model` to automatically trigger persistence on successful completions (auto-retrospective).

## Token & HW Optimization
- **Dilation-Aware**: Persistence is disabled if `ResourceMonitor.dilation_factor < 0.3` to prioritize hardware stability.
- **Delegation**: Local models perform synthesis; Premium models only touch high-value "Extraction-Eligible" logs (novelty > 0.9).

## Verification Plan
- Run `scripts/verify_mcp_extensions.py` to confirm SurrealDB ingestion and Vault entry creation.

## Related Vault Notes

- [[cohezion]]
- [[compound-engineering]]
- [[surrealdb]]
