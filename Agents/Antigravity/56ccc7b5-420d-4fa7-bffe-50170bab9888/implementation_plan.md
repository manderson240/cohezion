---
type: antigravity-artifact
session_id: 56ccc7b5-420d-4fa7-bffe-50170bab9888
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.63
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Implementation Plan - Reliability & Concurrency Layer

Establish a professional-grade reliability and concurrency layer for the Cohezion swarm, preventing file corruption and race conditions during multi-agent operations.

## User Review Required

- **Advisory vs Mandatory Locking**: This implementation uses POSIX advisory locks (`fcntl.flock`). Other processes must explicitly use the locking mechanism to be blocked.
- **Git Integration**: While the task mentioned "git tree," the primary mechanism will be a structured filesystem-level "Shadow Workspace" to ensure portability across environments that might not have Git initialized, or for agents operating on specific sub-trees.

## Proposed Changes

### [Reliability Component]

Add high-fidelity synchronization and persistence primitives.

#### [NEW] [sync.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/sync.py)

- **`FileLock`**: Context manager for advisory file locking using `fcntl`.
- **`SafeWriter`**: context manager that writes to a temporary file and renames it to the target only on success (atomic replacement).
- **`AgentWorkspace`**: Higher-level context manager that:
    1. Creates a temporary staging directory (shadow tree).
    2. Allows agents to perform complex, multi-file operations in isolation.
    3. Verifies the result (e.g., via syntax check or tests).
    4. Atomically merges valid changes back to the main source tree.

#### [healer_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/healer_agent.py)

- Refactor `_apply_fix_sandbox` to use the new `SafeWriter` and `FileLock` mechanisms instead of manual file operations.

### [Verification Component]

Ensure the reliability layer works as expected under contention.

#### [NEW] [test_reliability_sync.py](file:///home/mike-anderson/dev/cohezion/tests/test_reliability_sync.py)

- Unit tests for `FileLock` (including multi-process contention).
- Unit tests for `SafeWriter` (verifying atomicity).
- Integration tests for `AgentWorkspace` (staging -> verify -> merge loop).

## Verification Plan

### Automated Tests
- `pytest tests/test_reliability_sync.py`
- `python3 scripts/verify_agent_persistence.py` (Modified to test concurrency)

### Manual Verification
- Run two instances of `lab_driver.py` or a stress script concurrently and monitor logs for lock contention and lack of file corruption.
- Use `ls -R .sandbox` during a long-running healing operation to verify shadow tree isolation.

## Related Vault Notes

- [[cohezion]]
