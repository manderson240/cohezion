---
description: "Strict Kaggle competition rules, active track focus, and submission governance"
globs: ["scripts/kaggle/**", "src/cohezion/agi/kaggle*"]
alwaysApply: true
---

# Rule: Kaggle Discipline & Active Tracks Only

## Triggers
- Any task interacting with Kaggle CLI, kernels, datasets, or submissions.

## Enforced Behavior
1. **Active Tracks Only**: Strictly limit auditing and submissions to currently ACTIVE competitions:
   - ARC Prize 2026 (ARC-AGI-2, ARC-AGI-3, Paper Track)
   - Biohub Cell Tracking
   - RSNA Knee Abnormality Detection
   - Enveda CASMI26
   - Kaggriculture
2. **Strict Exclusions**: Never report on expired competitions. Explicitly exclude Pokémon TCG per user mandate.
3. **Code Competition Submission Protocol**:
   - For notebook competitions (Biohub, RSNA, ARC-AGI-2), always use `api.competition_submit_code()` with an explicit `kernel_version` parameter to avoid 403 Forbidden errors.
4. **Quota Stewardship**: Maximize allocated weekly GPU/TPU hours without hitting throttling limits.
