---
title: "Kaggle Active Competitions & Submission Governance"
category: kaggle
updated: 2026-10-15
coherence: 0.50
---

# Kaggle Active Competitions & Submission Governance

## Active Tracks Portfolio (Strictly Maintained)
1. **ARC Prize 2026 ($700K)**:
   - Tracks: ARC-AGI-2 (`arc-prize-2026-arc-agi-2`), ARC-AGI-3 (`arc-prize-2026-arc-agi-3`), Paper Track (`flume-arc-prize-2026-paper.ipynb`).
   - SOTA Approaches: Poincaré conformal MCTS, D4 dihedral group non-duplication, Cayley budget entropy deadlock watchdog.
   - Latest Scored: ARC-AGI-2 28.19% (Ref #57288127); ARC-AGI-3 v42 online entropy variance gating.
2. **RSNA Knee Abnormality Detection ($77K)** (`rsna-knee-abnormality-detection`):
   - Metric: Multi-label weighted log-loss.
   - SOTA Approaches: Raptor-384 + Raptor-224 + R7 ConvNeXt blend, Calibrated Trimmed Median Consensus Ensemble.
   - Current Score: 0.956 peak (v38), v40 Trimmed Median Consensus running on Kaggle GPU.
3. **Enveda CASMI26 ($50K)** (`enveda-CASMI26-molecule-id-mass-spectra`):
   - Metric: Top-25 MRR biomolecule identification.
   - Current Score: 0.407 (Ref #57307937, v28), 0.417 peak (v26).
   - In-Flight: Slot 4 v29 Parsimonious Chemical Graph Reranker (Ref #57317713).
4. **Name That LLM ($50K)** (`name-that-llm`):
   - Metric: Multi-class log-loss across 7 LLM model classes.
   - SOTA Approaches: 5-stream stylometric feature pipeline, two-stage Hierarchical Bayesian Decomposition with Dirichlet-Multinomial shrinkage, L2 feature scaling.
   - Current Score: 0.330; pre-verified SOTA v7 kernel executed in 1m47s primed for UTC reset.
5. **Gemma-4 Developer Agent Competition**:
   - Focus: Autonomous agent code generation and repository synthesis using Gemma-4 models.
   - SOTA Approaches: Near-greedy deterministic sampling ($T=0.10$), sub-agent code analyzer, and AutoHarness manifest verification.
   - Current Score: 0.15 peak (v12); sampling calibrated to $T=0.10$ in submission.zip.

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
