---
title: "Kaggle Active Competitions & Submission Governance"
category: kaggle
updated: 2026-10-15
coherence: 0.50
---

# Kaggle Active Competitions & Submission Governance

## Active Tracks Portfolio (Strictly Maintained)
1. **ARC Prize 2026 ($700K)**:
   - Tracks: ARC-AGI-2 (`arc-prize-2026`), ARC-AGI-3, Paper Track (`flume-arc-prize-2026-paper.ipynb`).
   - SOTA Approaches: Poincaré conformal MCTS, D4 dihedral transformation invariance, AutoHarness AST solvers.
   - Latest: ARC-AGI-2 baseline 0.3148 (+0.0120 SOTA improvement), ARC-AGI-3 v37 Poincaré MCTS patch.
2. **RSNA Knee Abnormality Detection ($77K)** (`rsna-knee-abnormality-detection`):
   - Metric: Multi-label weighted log-loss / AUC.
   - SOTA Approaches: R7 Raptor blend, Nelder-Mead copula calibration, adversarial OOF validation ($\text{ROC-AUC} = 0.5461$).
   - Current Score: 0.9480 baseline / 0.957 Raptor blend.
3. **Enveda CASMI26 ($50K)** (`casmi-2026-challenge-biomolecule-identification`):
   - Metric: Formula cleavage matching and adduct latent marginalization.
   - Current Score: LB 0.328 (Top 18%, Rank 137/744).
   - Latest: v27 deep expansion pipeline (`patch_casmi26_v27_deep_expansion.py`).
4. **NFL Big Data Bowl 2027 ($100K)** (`nfl-big-data-bowl-2027`):
   - Metric: Pre-snap prospect motion, Voronoi passing lanes, defensive closing velocity.
   - SOTA Approaches: LightGBM + XGBoost + CatBoost blended prospect scout cards (`generate_prospect_scout_cards.py`).
   - Current Score: 0.7620 baseline.
5. **Gemma-4 Developer Agent Competition**:
   - Focus: Autonomous agent code generation and repository synthesis using Gemma-4 models.
   - SOTA Approaches: Sub-agent code analyzer, sampling configurations, and compiled paper PDF.

## Invariant Rules & Submission Discipline
- Never report on or submit to expired/closed competitions (e.g. Biohub, Kaggriculture).
- Explicitly ignore Pokémon TCG per user mandate.
- All code competitions strictly reject local file uploads with HTTP 400 `FAILED_PRECONDITION`.
- All submissions MUST be dispatched through `scripts/kaggle/kaggle_submit.py` using mode `notebook` (calling `api.competition_submit_code` with `kernel_version`, NOT `version`).

## Related Artifacts & Code
- Submitter: `scripts/kaggle/kaggle_submit.py`
- Midnight Queue: `scripts/kaggle/queue_midnight_all_competitions.py`
- Ascension Worker: `scripts/kaggle/stateless_npu_ascension_worker.py`
- Sentinel: `scripts/kaggle/master_24_7_kaggle_sentinel.py`
