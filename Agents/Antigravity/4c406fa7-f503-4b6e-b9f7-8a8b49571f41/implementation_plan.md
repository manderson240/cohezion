---
type: antigravity-artifact
session_id: 4c406fa7-f503-4b6e-b9f7-8a8b49571f41
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.342
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Fix Runaway Git Changes

The "10000 pending changes" issue is caused by generated simulation data (specifically in `data/overnight/`) being tracked by git. Even though `data/` is in `.gitignore`, files already tracked are not ignored.

## Proposed Changes

### 1. Fix Git Tracking (Immediate Relief)
- [ ] **Untrack `data/overnight/`**: Run `git rm -r --cached data/overnight/` to remove these files from the git index while keeping them on disk.
- [ ] **Untrack other generated artifacts**: Check `results/`, `logs/`, and `renders/` for similar issues.

### 2. Strengthen Prevention
- [ ] **Update `.gitignore`**: Ensure specific patterns like `data/overnight/**` are explicitly ignored if generalized rules aren't catching them (though `data/` should be enough).
- [ ] **Add Pre-commit Hook (Optional)**: If this keeps happening, a pre-commit hook to prevent committing files in `data/` could be useful, but `gitignore` is the standard way.

### 3. Verification
- [ ] **Check `git status`**: Confirm the pending changes drop from ~10000 to a reasonable number.
- [ ] **Run a minimal test**: Ensure `LabAgent` or simulation scripts can still write to these directories without git noticing.

## Democratic Consensus Plan

### Phase 1: Diagnostic and Root Cause Analysis (Critical)
- [ ] Run `git ls-files | grep "data/overnight/"` to see exactly what's tracked
- [ ] Check for conflicting `.gitignore` patterns in parent directories
- [ ] Verify `git status` shows the exact issue before any changes

### Phase 2: Safe Fix Implementation
- [ ] Create a backup branch: `git checkout -b fix/runaway-files-pre-cleanup`
- [ ] Run `git rm -r --cached data/overnight/` (checking output carefully)
- [ ] Run `git rm -r --cached results/` if needed.
- [ ] Add comprehensive ignore patterns to `.gitignore`:
    - `data/overnight/**`
    - `results/**`
- [ ] Commit the ignore changes with clear message.

### Phase 3: Preventive Measures
- [ ] Verify `check-ignore` reports correct ignoring.

