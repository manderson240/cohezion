---
name: kaggle-strix-verifier
version: 1.0.0
description: "Hardware-aware, zero-OOM deterministic verification on AMD Strix Halo (128GB Unified Memory / Ryzen AI MAX+ 395). Directs Tier 0 Zen 5 CPU multithreading and Tier 1 FastFlowLM NPU execution for pre-submission mathematical proof checking, metric cost sensitivity validation, and AutoHarness invariant gating across active Kaggle competitions."
metadata:
  hardware: AMD Ryzen AI MAX+ 395 (Strix Halo, 128GB UMA)
  tier: Tier 0 CPU / Tier 1 NPU
---

# Kaggle Strix Halo Deterministic Verifier

Ensure 100% mathematical validity, zero GPU VRAM exhaustion, and zero Out-Of-Memory (OOM) crashes prior to any Kaggle submission.

## Architecture

1. **Tier 0 CPU Invariant Verification (16 Zen 5 Cores / 32 Threads)**:
   - Evaluates all AST bytecode invariants, HiGHS MILP point-cloud transshipment calculations, Ledoit-Wolf covariance shrinkage calibrations, and Monte Carlo game simulations purely on CPU.
   - Memory footprint: < 4 GiB standard system RAM, 0 MB GPU GTT / aperture.

2. **Tier 1 NPU Consultation Discipline (AMD XDNA 2 NPU)**:
   - Uses FastFlowLM models (`deepseek-r1-0528-8b-FLM`, `qwen3-4b-FLM`) executing in SRAM (< 2W power, 0 UMA RAM usage) for reasoning without GPU aperture contention.

3. **Zero-Local-Weight Guardrail**:
   - Heavy 3D volumetric deep neural network training (e.g., 3D Swin, CoAtNet-3 on multi-slice MRI or terabyte embryo microscopy) is strictly prohibited from running on local host memory.
   - All deep learning training and large-scale fine-tuning executes exclusively on Kaggle Cloud GPUs (2x T4 or 4x L4).

4. **Preflight Hardware Validation**:
   - Always run `bash scripts/preflight_fleet.sh`.
   - Ensure Available Memory >= 20 GiB, Swap <= 10%, and GPU GTT <= 50 GiB.
   - If memory pressure is detected, invoke `bash scripts/recover_fleet.sh --soft` before launching CPU tasks.

5. **Deterministic Pre-Submission Sanity Checks**:
   - **Biohub 3D Cell Tracking**: Validates AOGM cost asymmetry ($w_{\text{FN}} = 10.0$ vs $w_{\text{EA}} = 1.5$), checks for false-negative dropouts, and verifies temporal monotonicity.
   - **RSNA Knee Abnormality**: Asserts probability boundaries $[\epsilon_j, 1-\delta_j]$ scaled to prevalence $\pi_j$ to prevent $-\ln p \to \infty$, verifies lack of `.rank(pct=True)` distortion, and validates Ledoit-Wolf shrinkage ($\alpha \in [0.03, 0.05]$).
   - **ARC Prize 2026**: Validates Gray-Pratt bit-quad Euler characteristic ($\chi = V - E + F$), $D_4$ dihedral group reflection/rotation symmetry, and Attempt 1 vs 2 diversity (Hamming distance >= 0.15).
   - **Kaggriculture Simulation**: Runs turn-exact order-book simulation, checks 8C/4S Dairy compounding opening, and asserts Turn-28 early dead-stock liquidation.
