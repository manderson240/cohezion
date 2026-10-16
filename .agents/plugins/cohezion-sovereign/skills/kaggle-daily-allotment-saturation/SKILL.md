---
name: kaggle-daily-allotment-saturation
metadata:
  version: "1.0.0"
description: >-
  Autonomous 24/7 continuous saturation of Kaggle daily submission allotments with first-principles invariant hypothesis ladders.
---

# SKILL: KAGGLE_DAILY_ALLOTMENT_SATURATION_PRIME

## DOMAIN EXPERTISE
Autonomous orchestration and continuous harvesting of Kaggle daily submission allotments across active competitive tracks (RSNA Knee, ARC-AGI-2, ARC-AGI-3, CASMI26, Name That LLM, Gemma-4). Replaces one-shot midnight execution with event-driven, pacing-governed continuous saturation.

## KEY TEXTS & CONCEPTS
- **Competition Quota Diversity**:
  * Code competitions enforcing 1 submission/day (ARC-AGI-2, ARC-AGI-3, Gemma-4).
  * Feature & diagnostic competitions granting 5 submissions/day (RSNA Knee, CASMI26, Name That LLM).
- **Event-Driven Saturation**: Submissions must never be dispatched while a previous submission for the same competition is in `PENDING` status (strictly prevents HTTP 400 `FAILED_PRECONDITION`).
- **Hypothesis Progression Matrix (Slots 1 to 5)**: Every daily submission must evaluate a distinct, verifiable first-principles invariant rather than redundant noise:
  * Slot 1: Proven baseline / SOTA equilibrium blend.
  * Slot 2: Domain geometric/physical invariant (JSN covariance, D4 dihedral equivariance, deep candidate expansion).
  * Slot 3: Multi-model diversity ensemble (e.g. LinearSVC + HistGBM, copula alignment).
  * Slot 4: Boundary & distribution alignment (Kolmogorov projection, Sinkhorn optimal transport).
  * Slot 5: Calibrated consensus / trimmed median shrinkage.
- **AutoHarness Invariant Factory Gate (arXiv:2603.03329v1)**: Deterministic bytecode and syntax validation gating notebook and code artifacts before kernel push.

## INSTRUCTION
1. Query Competition Quota Status:
   ```python
   from kaggle.api.kaggle_api_extended import KaggleApi
   api = KaggleApi()
   api.authenticate()
   subs = api.competition_submissions(comp_slug)
   used_today = sum(1 for s in subs if s.date.date() == datetime.UTC.date())
   is_pending = bool(subs and "PENDING" in str(subs[0].status).upper())
   ```
2. Dispatch Next Available Slot Variant:
   If `used_today < max_daily` and `not is_pending`:
   - Execute slot patch script (`assemble_*.py` or `patch_*.py`).
   - Run AST and Red-Team IV&V checks.
   - Dispatch via `scripts/kaggle/kaggle_submit.py notebook -c <comp> -k <kernel> -f <file> -m <msg> -w`.
3. Log Learning & State:
   - On completion, record metric score in `daily_allotment_state.json`.
   - Extract retrospective into SurrealDB `experiment_run` table and Obsidian Vault `01-Learnings/`.
4. Continuous 24/7 Execution:
   - Keep daemon running in tmux session `kaggle-allotment`.

## VERSION
v1.0

## SEE ALSO
- FIRST_PRINCIPLES_INVARIANT_SCIENCE_PRIME
- LUKYANENKO_INVARIANT_ENGINEERING_PRIME
- HARNESS2_RECURSIVE_HARNESSING_PRIME
