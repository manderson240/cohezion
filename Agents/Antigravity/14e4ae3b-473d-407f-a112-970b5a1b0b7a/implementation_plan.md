---
type: antigravity-artifact
session_id: 14e4ae3b-473d-407f-a112-970b5a1b0b7a
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.374
  stage: embryo
  cluster: Agents
---

# Codebase Overhaul & Stability Hardening

This plan outlines a holistic review and improvement strategy for the Cohezion project. We will address accumulated technical debt (specifically the >6000 lint errors remaining after the last autonomous heal) and resolve the OOM system crashes related to mass-scale simulations.

## User Review Required

- Is there any specific feature or component (like the `EVO Cosmology` implementation) that you want me to prioritize differently than what's laid out below? I've targeted `TsunamiSimulator` and `JourneyTracker` based on the crash history.
- The `pytest` command is failing due to a missing dependency setup in the new git worktree. I will resolve this by explicitly installing the dev dependencies via `uv`. Let me know if you have a preferred bootstrap script (e.g., `make setup`).

## Proposed Changes

### Core Operations -> Linting & Code Quality

We currently have 6,355 errors reported by Ruff. We will systematically burn these down:

- Run `uv run ruff check . --unsafe-fixes` to automatically resolve the bulk of the safe/unsafe fixable issues (3000+).
- **Security Scans (`S`-rules)**: Address the `S101` (asserts) and `S311` (randomness) violations. Replace `assert` statements with explicit `if/raise ValueError` checks in application code (`src/`), while suppressing `S101` globally for the `tests/` directory if not already done.
- **Line Length (`E501`)**: Fix structural line breaks in Python files or adjust `pyproject.toml` to permit longer lines (e.g., 100-120 chars) if 88 is creating unnatural breaking, based on the `CODING_STANDARDS.md`.

### Core Operations -> Memory Leaks & Stability

The system crashed during the `EVO Cosmology` run (epochs > 500k) due to VRAM/RAM saturation from vector tracking.

- **[MODIFY] `scripts/drivers/tsunami_simulator.py`**:
  - Implement periodic clearing or pagination of the `latent_states` arrays if expanding over time.
  - Implement a rigorous `.copy()` or memory-view release policy when transferring batches to Rust `FlumePhysics`.
- **[MODIFY] `src/cohezion/compound/journey_tracker.py`** _or equivalent universe tracker_:
  - Add hard limits to the `PerceptionEvent` buffer to bound memory usage (as identified in previous conversation logs).
  - Implement periodic SurrealDB flushing to move large vectors out of memory and onto disk.

### Core Operations -> Audit & Workflows

- **[MODIFY] `/home/mike-anderson/dev/cohezion/cohezion-review/Makefile`**:
  - Update any targets that might be causing pytest execution failures. Ensure `uv sync` installs all `[dev]` optional dependencies.

---

## Verification Plan

### Automated Tests

1. **Pytest Suite execution**: Get the test suite (3200+ tests) running green in the new worktree.
   ```bash
   uv sync --all-extras
   uv run pytest tests/ -q -n auto
   ```
2. **Ruff Verification**:
   ```bash
   uv run ruff check . --statistics
   ```
   _Expected Result_: 0 errors in core source (`src/`), with safe suppressions in `tests/`.

### Manual/System Audits

Run the defined `/audit` workflow to verify overall system topology and persistence sanity:

```bash
uv run python3 src/cohezion/healing/platform_audit.py
uv run python3 src/cohezion/healing/utilization_audit.py
uv run python3 src/cohezion/db/surreal_client.py --verify-schema
```

This will ensure no regressions have been introduced into the underlying FLUME engine or the HIHO stability.
