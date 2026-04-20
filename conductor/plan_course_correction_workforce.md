# Implementation Plan: Tri-Orbit Experiment Course Correction & Workforce Expansion

## Background & Motivation
The **Tri-Orbit Experiment** is currently running, but monitoring indicates the `Code Surgeon` journey is potentially bottlenecked by a full 967-file static scan. Additionally, a malformed `.pattern_buffer.json` file is causing errors in the `PatternRepository`.

## Objective
1.  **Fix PatternRepository**: Transition from single JSON to JSONL for robust appending.
2.  **Optimize EigentAgent**: Throttled scanning and granular checkpointing for long-running journeys.
3.  **Expand Workforce**: Introduce the `Sovereign Documenter` role to leverage `Code Surgeon` findings.

## Key Files & Context
-   `src/cohezion/core/persistence/repositories/pattern_repository.py`: Fixing JSON error.
-   `src/cohezion/swarm/agents/eigent_agent.py`: Optimizing journey logic.
-   `src/cohezion/api/routes/eigent.py`: Adding the `Sovereign Documenter` role.

## Proposed Solution
-   **JSONL Support**: Update `PatternRepository` to append findings as single-line JSON objects.
-   **Incremental Journeys**: Modify `Code Surgeon` logic to scan files in batches of 10 per iteration, ensuring checkpoints are written frequently.
-   **New Role**: `Sovereign Documenter` will periodically poll `PatternRepository` for new findings and generate `docs/findings/` markdown reports.

## Implementation Steps
### 1. Repository Fix
-   Update `_load_buffer` to parse JSONL.
-   Update `_save_buffer` to append lines.

### 2. Agent Optimization
-   Refactor `run_journey` to allow role-specific "sub-batching" logic.
-   Implement `Code Surgeon` file slicing (e.g., `files[i*10 : (i+1)*10]`).

### 3. API Expansion
-   Add `Sovereign Documenter` to the `WorkforceRequest` role validation (if any).
-   Define a new task loop for documentation generation.

## Verification & Testing
1.  **Restart Server**: `fuser -k 8080/tcp` and restart uvicorn.
2.  **Check Progress**: Monitor `data/eigent/checkpoints/` for iteration count increases across all three agents.
3.  **Documentation Check**: Verify files are created in `docs/findings/`.

## Migration & Rollback
-   Delete the corrupted `.pattern_buffer.json` before starting.
-   Old JSON checkpoints will be preserved; the new logic will handle them or start fresh.
