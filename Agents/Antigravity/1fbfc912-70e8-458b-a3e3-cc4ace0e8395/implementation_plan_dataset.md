---
type: antigravity-artifact
session_id: 1fbfc912-70e8-458b-a3e3-cc4ace0e8395
date: 2026-03-04
title: "Implementation Plan Dataset"
aspect: doer
neural:
  activation: 0.302
  stage: embryo
  cluster: Agents
---

# Implementation Plan: Cohezion Fine-Tuning Data Prep

## Goal
Extract high-quality "Bug -> Fix" trajectories from the Ouroboros memory (SurrealDB) and format them for local QLoRA fine-tuning. This turns the system's "Dreams" and "Heals" into permanent muscle memory.

## Proposed Changes

### 1. The Extractor
- Create `scripts/training/export_trajectories.py`.
- Query `universe_nodes` for verified fixes (`metadata.tested = true`).
- Find the corresponding bug node.
- Format as:
```json
{
  "instruction": "Fix the following python bug: {bug_type}",
  "input": "{bug_code}",
  "output": "{fix_code}"
}
```

### 2. The Dataset
- Save to `data/training/cohezion_instruct.jsonl`.
- Validate JSON structure.

## Verification
- Run extraction script.
- Check if JSONL file is created and valid.
