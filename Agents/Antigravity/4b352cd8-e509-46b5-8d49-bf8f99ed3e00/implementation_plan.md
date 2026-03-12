---
type: antigravity-artifact
session_id: 4b352cd8-e509-46b5-8d49-bf8f99ed3e00
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.339
  stage: embryo
  cluster: Agents
---

# IDE Fixes Implementation Plan

This plan addresses the widespread IDE linting and typing issues in `ASCENSION_REACTIVE.py` and `overnight_driver.py`, and implements missing modules identified as the root cause of module not found errors.

## Proposed Changes

### 1. `src/cohezion/core/persistence/surreal_client.py` (Import Fix)

#### [MODIFY] `overnight_driver.py`

- Fix `from cohezion.db.surreal_client import ...` to use the correct path: `from cohezion.core.persistence.surreal_client import PhysicsState, SurrealClient, UniverseNode`
- Add type parameters to generic types (`dict[str, Any]` instead of `dict`).
- Add `# type: ignore` to `prometheus_client` and `mem0` imports, since they appear as unresolved in the environment.

### 2. Implementation of Missing Modules

The `overnight_driver.py` script attempts to import `mass_simulator` and `training_data_capture`, which are defined in the project's skills directory as `mass_simulation.md` and `TRAINING_DATA_CAPTURE_PRIME.md`, but have not been implemented in source yet.

#### [NEW] `src/cohezion/swarm/mass_simulator.py`

- Create module containing `SimulationConfig`, `SimulationState`, and `MassSimulator` as defined in `src/cohezion/skills/mass_simulation.md`.

#### [NEW] `src/cohezion/training/training_data_capture.py`

- Create module containing `InteractionRecord`, `JourneyRecord`, and `TrainingDataCapture` as defined in `src/cohezion/skills/TRAINING_DATA_CAPTURE_PRIME.md`.
- Ensure directory `src/cohezion/training/` contains `__init__.py`.

### 3. Updating Notifications

#### [MODIFY] `src/cohezion/mcp/email_notifier.py`

- Modify `send_email` and `_send_email` to accept `attachments: list[Path] | None = None`.
- Import `MIMEApplication` and attach provided files correctly to the email, which fixes the missing parameter issue in `overnight_driver.py`.

### 4. `notebooks/marimo/ASCENSION_REACTIVE.py` Typing Fixes

#### [MODIFY] `notebooks/marimo/ASCENSION_REACTIVE.py`

- Add `from typing import cast, Any` and `dict` type hints.
- Typecast the results from SurrealDB queries: `node = cast(dict[str, Any], results[0]["result"][0])` and `ps = cast(dict[str, Any], node.get("physics_state", {}))`. This resolves ~80 dictionary indexing errors flagged by the IDE.
- Add `# type: ignore` to `marimo.App` and missing library imports like `plotly.graph_objects`.

## Verification Plan

### Automated Tests

- Run `uv run ruff check` and `uv run pyright` on `overnight_driver.py` and `ASCENSION_REACTIVE.py`.
- Run pytest if applicable to ensure we did not break `email_notifier`.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
