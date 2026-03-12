---
type: antigravity-artifact
session_id: 86dfeb15-82f2-494d-b004-f30027f17347
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.322
  stage: embryo
  cluster: Agents
---

# Git Bloat Resolution Walkthrough

I have successfully resolved the git bloat issue by removing large generated files and strictifying `.gitignore` rules across three rounds of cleanup.

## Changes Made

### Round 1: Initial Cleanup
- Removed from tracking: `Steps_to_the_Discovery_of_Electro-Nuclear_Collapse-Matsumoto-draft_26.pdf` (325MB), `model.safetensors` (4.5MB), and `apps/dashboard/assets/`.
- Updated `.gitignore` for standard exclusions.

### Round 2: Recursion & New Apps
- **Global PDF Ignore**: Added `*.pdf` to `.gitignore` (excluding `docs/`). This solved the recurrence of the 325MB PDF appearing in status.
- **Trace Files**: Added `trace.json` to global ignore.
- **New Apps**: Added ignore rules for `apps/mcp-*/dist` and `apps/webapp/src/assets` to prevent thousands of small build files from cluttering the status.

### Round 3: Residual Bloat
- **Portfolio Assets**: Ignored `portfolio/assets/` (>1K files).
- **Saved Webpages**: Ignored `src/cohezion/library/*_files/` (recursive HTML save artifacts).
- **Bundles**: Ignored `*.bundle` binaries.

## Verification Results

### Configuration Checks
Ran `git check-ignore` to verify rules:
- `src/.../Matsumoto-draft_26.pdf` -> IGNORED (Rule: `*.pdf`)
- `trace.json` -> IGNORED (Rule: `trace.json`)
- `apps/dashboard/assets/` -> IGNORED (Rule: `apps/dashboard/assets/`)
- `portfolio/assets/` -> IGNORED (Rule: `portfolio/assets/`)

### Repository Status
The `git status` check now shows ~380 untracked files, all of which are legitimate source code directories for new applications (`apps/mcp-*`, `apps/webapp/src`) and configuration. The thousands of build artifacts and large binaries are no longer cluttering the repository.

## Related Vault Notes

- [[cohezion]]
