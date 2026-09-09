# Cohezion High-ROI Kaggle Compute Maximization Plan
**Generated:** 2026-09-06
**Target Prize Pool:** $1,550,000 USD (ARC-AGI-3 $850k + ARC-AGI-2 $700k)

---

## 1. Current Compute Resource Allocation

| Resource | Allocated / Total | Remaining | Expiration / Refresh | Strategic Action |
|---|---|---|---|---|
| **Kaggle GPU (L4)** | 8.25h / 30.00h | **21.75h** | 2026-09-12 (5 days) | Exhaust on full-dataset test-time search runs (4-6h each) |
| **Kaggle TPU (v3-8)** | 0.00h / 20.00h | **20.00h** | 2026-09-12 (5 days) | High-throughput distributed grid embeddings & symbolic verification |
| **Kaggle AI Models API** | $0.00 / $50/day | **$50.00/day** | Resets 00:00 UTC | Zero GPU-cost prompt verification for AGI tracks |
| **Local Strix Halo / 128GB**| NPU/iGPU/CPU | Unlimited | Local | Offline transform pre-generation (Bonsai-8B, Qwen-30B) |

---

## 2. The 3-Step Leaderboard Acceleration Strategy

### Step 1: Submit Completed Run (Zero Compute Cost)
- Kernel `manderson240/arc-agi-2-fork-subset16-20260903` (Version 2) completed on L4 GPU.
- Generated `submission.json` with Quantile Diversified Selector ($q=0.425$) over 16 D4 TTA views.
- **Action**: Click "Submit to Competition" in Kaggle Notebook Output to update leaderboard score.

### Step 2: Launch Full-Dataset GPU Run (Consuming 6-8 GPU Hours)
- Upgrade task-subset from 16 puzzles to the complete test evaluation challenges.
- Leverage the remaining 21.75 GPU hours to run the full test-time LoRA search tree.

### Step 3: Deploy TPU v3-8 for ARC-AGI-3 Interactive Agent Exploration
- Utilize 20.00 idle TPU hours to run large-scale parallel rollouts in `arcengine`.
