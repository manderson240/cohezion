---
type: antigravity-artifact
session_id: d9c1fcdb-69db-458c-b64a-f26e49625c33
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.64
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Universal Stabilization & Refactoring Plan

## Goal
Stabilize the Cohezion repository, repair data integrity issues with Google Sheet integration, and prepare the architectural blueprint for the "FLUME Microservices" migration requested by the user.

## User Review Required
> [!IMPORTANT]
> **Duplicate Headers Detected**: The Google Sheet has duplicate columns (likely "Key Abstractions"). I will update the script to handle this or ask you to fix it manually.
> **Repository Cleanup**: I will stage the ~10k deletions/modifications to bring the repo to a clean state.

## Proposed Changes

### 1. Repository Hygiene (The "10k Changes" Fix)
- **Problem**: Large number of unstaged deletions/modifications in `data/` and `node_modules/`.
- **Fix**:
    - Update `.gitignore` to explicitly exclude `data/surrealdb`, `node_modules`, `coverage`, `__pycache__`.
    - Run `git add -u` to stage all deletions.
    - Run `git clean -fdX` (dry run first) to identify untracked bloat.

### 2. Data Integrity Repair (Row 77 & Headers)
- **Problem**: `gspread` reports `DuplicateHeaderError`. This crashes `get_all_records()`.
- **Fix**:
    - Modify `sheet_watcher.py` to use `get_all_values()` (raw) instead of `get_all_records()` (dict mapping) to bypass header strictness.
    - Implement a robust row-finder for "Row 77" to debug why it's empty.

### 3. Architecture Blueprint (Microservices)
- **Concept**: Decompose the monolith into:
    - **Nexus Core (Orchestrator)**: The current `main.py` equivalent.
    - **Cortex (LLM Service)**: Dedicated `ModelWrangler` service.
    - **Memory (SurrealDB)**: Validated.
    - **Sensorium (Input/Output)**: WebSockets and Sheet Watchers.
- **Action**: Create `ARCHITECTURE_MICROSERVICES_DRAFT.md`.
- **Research**: Answer "Exotic Chemistries" question.

## Verification Plan

### Automated Tests
- **Row 77 Check**: Run `python3 scripts/drivers/sheet_watcher.py --check-row 77` (after fix).
- **Repo Cleanliness**: Run `git status` and ensure output is minimal (<10 lines).

### Manual Verification
- **Sheet Audit**: Visually confirm Row 77 and Header layout in the Google Sheet.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
