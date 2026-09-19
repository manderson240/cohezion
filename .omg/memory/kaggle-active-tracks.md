---
title: "Kaggle Active Competitions & Submission Governance"
category: kaggle
updated: 2026-09-19
coherence: 0.50
---

# Kaggle Active Competitions & Submission Governance

## Active Tracks (Strictly Maintained)
1. **ARC Prize 2026 ($700K)** (`arc-prize-2026`):
   - Tracks: ARC-AGI-2, ARC-AGI-3, Paper Track.
   - Hardware: Quad-L4x4 (`NvidiaL4x4`, 96GB aggregate VRAM).
   - Latest: Sub #56347388 (`manderson240/arc-agi-2-fork-lb33-89-20260903`, v10).
2. **Biohub Cell Tracking ($60K)** (`biohub-cell-tracking-during-development`):
   - Metric: TRA/SEG graph association Jaccard.
   - Latest: Sub #56348421 (Kernel v2 `manderson240/cohezion-biohub-v6`, adaptive threshold 0.945 on 6bba).
3. **RSNA Knee Abnormality Detection ($77K)** (`rsna-knee-abnormality-detection`):
   - Metric: Multi-label weighted log-loss / AUC.
   - Acceleration: `TTA_OVERLAP = False` (8.5x speedup to eliminate hidden test set timeout).
   - Latest: Sub #56347892 (Kernel v7 `manderson240/cohezion-rsna-knee-sota-ensemble`).
4. **Enveda CASMI26 ($50K)** (`casmi-2026-challenge-biomolecule-identification`):
   - Standings: Rank 137 / 744 (Top 18%, LB 0.328). Sub #56346703.
5. **Kaggriculture ($50K)**:
   - Simulation ladder with 2 active slots (`LIVE_SLOTS = 2`).
   - Active agents: Sub #56333720 & #56333717.

## Invariant Rules
- Never report on or submit to expired/closed competitions.
- Explicitly ignore Pokémon TCG per user mandate.
- All notebook submissions must supply `kernel_version` to avoid `403 Forbidden`.
