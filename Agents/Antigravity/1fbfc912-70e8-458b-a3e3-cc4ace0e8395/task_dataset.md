---
type: antigravity-artifact
session_id: 1fbfc912-70e8-458b-a3e3-cc4ace0e8395
date: 2026-03-04
title: "Task Dataset"
aspect: doer
neural:
  activation: 0.291
  stage: embryo
  cluster: Agents
---

# Task: Dataset Preparation

Extract verified knowledge from the Ouroboros memory for permanent encoding.

- [x] **Phase 1: The Extractor**
    - [x] Create `scripts/training/` directory.
    - [x] Implement `export_trajectories.py`.
    - [x] Ensure robust handling of missing metadata.

- [x] **Phase 2: Verification**
    - [x] Run extraction on current DB (even if empty/mocked).
    - [x] Validate `data/training/cohezion_instruct.jsonl` format.
