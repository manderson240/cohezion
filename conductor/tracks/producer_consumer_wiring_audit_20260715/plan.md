# Implementation Plan: Producer and Consumer Wiring Audit

## Phase 1: Setup & Red-Phase Testing (TDD Initialization)
- [ ] Task: Create new unit test files for Mycelium and Ouroboros changes.
  - [ ] Write failing unit tests for `MyceliumRegistry` singleton, thread-safe access, and memory limits (500 cluster cap with FIFO eviction) in `tests/mycelium/test_registry_remediation.py`.
  - [ ] Write failing unit tests for `CardAlignmentMonitor` model ID tracking and payload validation in `tests/ouroboros/test_monitor_remediation.py`.
- [ ] Task: Create failing unit tests for daily researcher verify evolve lane changes.
  - [ ] Write failing unit tests for `_query_mycelium_patterns` integration with the registry in `tests/researcher/test_verify_mycelium_integration.py`.
  - [ ] Write failing unit tests for `_query_ouroboros_healing_events` SurrealDB query validation, input sanitization, and retry logic.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Run the new tests and verify they all fail cleanly (Red Phase confirmed).

## Phase 2: Registry and Monitor Implementation (Green Phase)
- [ ] Task: Implement `MyceliumRegistry` thread-safe singleton, cluster filtering, and memory limits.
  - [ ] Add `_singleton` variable, `get_instance(cls)` and `reset_instance(cls)` thread-safe methods (using `threading.Lock`) to `MyceliumRegistry`.
  - [ ] Add `member_families` and `member_tasks` fields to `MyceliumCluster` and update ingestion to populate them.
  - [ ] Implement `query_patterns(self, family: str, task: str) -> list[dict]` filtering.
  - [ ] Enforce the 500-cluster cap and FIFO eviction policy when adding a new cluster.
- [ ] Task: Implement `CardAlignmentMonitor` model ID tracking.
  - [ ] Update `__init__` to accept `model_id: str | None = None`.
  - [ ] Include `model_id`, `rate`, `threshold`, and `timestamp` in the emitted `HEALING_EVENT` payload.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Run registry and monitor unit tests and verify they now pass (Green Phase confirmed).

## Phase 3: Verification Lane Integration (Green Phase)
- [ ] Task: Implement `verify_evolve.py` query wiring for Mycelium patterns.
  - [ ] Update `_query_mycelium_patterns` in `verify_evolve.py` to resolve model family, fetch `MyceliumRegistry` singleton, and query it.
- [ ] Task: Implement `verify_evolve.py` query wiring for SurrealDB healing events.
  - [ ] Implement the `_query_ouroboros_healing_events` method to query the `precipitation_event` table.
  - [ ] Add input sanitization validating `model_id` matches `^[a-zA-Z0-9:-]+$`.
  - [ ] Add connection timeout (2.0s) and exponential backoff retry logic (3 retries).
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Run the complete test suite under `tests/researcher/` and verify all verify_evolve tests pass.

## Phase 4: Final Verification & Governance
- [ ] Task: Run full regression checks.
  - [ ] Run the fast test suite `make test-fast` to check for any regressions.
- [ ] Task: Document changes and audit learnings.
  - [ ] Document learnings in `src/cohezion/knowledge_graph/KEY_LEARNINGS.md`.
- [ ] Task: Phase Verification & Checkpoint (Refer to workflow.md)
  - [ ] Verify that all checklist items are complete and all files pass formatting, linting, and type checking (`make lint-check`, `make type-check`).
