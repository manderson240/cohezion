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
   - Uses FastFlowLM models (`llama3.2-1b-FLM`, `qwen3.5-4b-FLM`) executing directly on AMD XDNA 2 SRAM (< 2W power, 0 UMA RAM usage) exclusively through Port 13305 Admission Gate for low-latency (<1s) reasoning without GPU aperture contention.

3. **Zero-Local-Weight & ApertureGuard Mandate**:
   - Heavy deep learning training, multi-file heavy refactoring, and large GGUFs (>4GB) are strictly prohibited on Tier 1 local hardware.
   - All large model workloads are offloaded to Tier 2 (Ollama Cloud / Headless Claude), and all heavy training executes exclusively on Kaggle Cloud GPUs (2x T4 or 4x L4).

4. **Preflight Hardware Validation**:
   - Always run `bash scripts/preflight_fleet.sh`.
   - Ensure Available Memory >= 24 GiB, Swap < 20%, and GPU GTT <= 50 GiB.
   - If memory pressure is detected, invoke `bash scripts/recover_fleet.sh --soft` before launching CPU tasks.

5. **Deterministic Pre-Submission Sanity Checks (Active Competitions Only)**:
   - **RSNA Knee Abnormality**: Asserts probability boundaries $[\epsilon_j, 1-\delta_j]$ scaled to prevalence $\pi_j$ to prevent $-\ln p \to \infty$, verifies lack of `.rank(pct=True)` distortion, validates Ledoit-Wolf shrinkage ($\alpha \in [0.03, 0.05]$), and enforces Kolmogorov monotonicity $P(\text{Abnormal}) \ge \max_k P_k$.
   - **ARC Prize 2026 (ARC-AGI-2 & ARC-AGI-3)**: Validates Gray-Pratt bit-quad Euler characteristic ($\chi = V - E + F$), $D_4$ dihedral group reflection/rotation symmetry, and non-destructive attempt-2 DSL injection.
   - **Enveda CASMI26 Molecule ID**: Validates GBDT 0.35 + cleavage 0.25 + entropy 0.15 ensemble with RDKit Tautomer Canonicalization, eliminating Gaussian $w_{\text{ppm}}$ penalty noise.
   - **Google Gemma 4 Developer Agent**: Validates fast-inference container parity, 240s pytest timeout enforcement, token-insulated execution graphs, and AST patch verification.
   - **NFL Big Data Bowl 2027**: Validates Voronoi field-control kinematic invariants, coordinate normalization, and $D_4$ player orientation equivariance.

6. **Deterministic Submission Protocol**:
   - All code competitions strictly require dispatch through `scripts/kaggle/kaggle_submit.py --mode notebook` via `competition_submit_code(kernel_version=...)`. Local file uploads return HTTP 400.

