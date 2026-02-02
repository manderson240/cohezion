# RETROSPECTIVE: Phase 12 - Multi-Model Scaling (UMA/Strix Halo)

**Date**: 2026-02-01 (Backfilled)
**Topic**: Unified Memory Architecture (UMA) & Bi-Directional Control
**Phase**: S12 (UMA/Sheet-Control)

## 1. The Challenge
We operate on a "Strix Halo" class machine (128GB Unified Memory). Standard CUDA assumptions (Split RAM/VRAM) hindered performance. We needed to leverage the **Graphics Translation Table (GTT)** to allow models to spill gracefully into system RAM without crashing, effectively giving us 100GB+ of addressable VRAM for 70B+ model swarms.

## 2. Issues Encountered & Solutions

### A. The "VRAM Wall"
**Problem**: Large models (70B) would OOM immediately if VRAM (12GB dedicated) was exceeded.
**Solution**: **GTT Awareness**. We updated `ResourceMonitor` to track `GTT` usage. This confirmed that the system effectively "swaps" VRAM to System RAM.
- **Strategy**: Pushed quantization to `Q4_K_M` to fit 70B models into ~40GB, well within the 128GB Unified bounds.

### B. Bi-Directional Control (Google Sheets)
**Problem**: The user needed to control the swarm from mobile.
**Solution**: **SheetCommandWatcher**.
- **Mechanism**: A background daemon polls a specific Google Sheet cell ("Requested").
- **Action**: Triggers a specific research pipeline (`research_agent.py`) and writes the status back ("In Progress" -> "Complete").
- **Latency**: Tuned polling to 60s to avoid API quotas.

## 3. Metrics & Validation
- **Max Model Size**: 70B Parameters (DeepSeek-R1 / Llama-3.3-70B)
- **Concurrent Models**: 3x Large Models (via GTT spillage)
- **Control Latency**: ~45s average response time from Sheet update.

## 4. Key Takeaways
- **UMA is King**: On Apple Silicon / Strix Halo architectures, VRAM is just a suggestion. GTT is the real limit.
- **Async Control**: Google Sheets acts as a perfect "Slow Database" for human-in-the-loop control without needing a custom mobile app.
