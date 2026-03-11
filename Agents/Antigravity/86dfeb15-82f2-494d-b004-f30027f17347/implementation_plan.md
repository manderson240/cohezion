---
type: antigravity-artifact
session_id: 86dfeb15-82f2-494d-b004-f30027f17347
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.313
  stage: embryo
  cluster: Agents
---

# Resolve Git Bloat Implementation Plan (Round 3)

## User Review Required

> [!WARNING]
> I will be removing the following files from git tracking. They will remain on your local disk but will not be part of future commits. 
> - `src/cohezion/library/Steps_to_the_Discovery_of_Electro-Nuclear_Collapse-Matsumoto-draft_26.pdf` (325MB)
> - `apps/dashboard/assets/` (>1000 files)
> - `tests/flume_hf_test/model.safetensors` (4.5MB)
> - `portfolio/assets/` (New finding)
> - `src/cohezion/library/*_files/` (Saved webpages)

## Proposed Changes (Round 3)

### Configuration
#### [MODIFY] [.gitignore](file:///home/mike-anderson/dev/cohezion/.gitignore)
- **Portfolio Assets**: Ignore `portfolio/assets/`.
- **Saved Webpages**: Ignore `src/cohezion/library/*_files/` (matches both "Guidance..." and "Job Application..." folders).
- **Bundles**: Ignore `*.bundle` if they are binaries.

### Git Cleanup
- Determine if `git rm --cached` is needed for these new paths.
- Verify `git status` is clean.

## Verification Plan

### Automated Tests
- Run `git ls-files --others --exclude-standard` to ensure the "Untracked & Not Ignored" list is empty.
- Run `git status` to ensure it is clean.

### Manual Verification
- Check that important PDFs (if any) are still accessible (on disk).
