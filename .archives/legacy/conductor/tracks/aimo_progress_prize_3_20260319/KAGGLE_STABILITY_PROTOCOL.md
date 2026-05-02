# Kaggle Code Competition Stability Protocol

This document codifies best practices for surviving the hidden test set rerun in Kaggle code competitions, specifically applied to the **AIMO 3 Mathematical Reasoning Swarm**.

## 1. Common Failure Modes & Mitigations

| Error Class | Root Cause | Cohezion v38 Mitigation |
| :--- | :--- | :--- |
| **Notebook Threw Exception** | Unhandled edge cases in hidden LaTeX problems. | **Fortress Firewall**: Wrapped `predict` in global `try/except` returning scalar `0`. |
| **Submission Scoring Error** | Format mismatch (e.g., stringified Polars Series). | **Polars Scalar Fix**: Forced `problem_df[0]` to extract raw text only. |
| **Notebook Timeout** | Slow inference on complex problems (9h total limit). | **Adaptive Throttling**: System skips secondary audit if per-problem budget < 220s. |
| **Memory Error (OOM)** | KV cache accumulation or large model loading. | **Hard VRAM Resets**: Explicit `gc.collect()` and `torch.cuda.empty_cache()` between every problem. |
| **Out of Disk** | Redundant wheel installs or bloated `/kaggle/working`. | **One-Time Install**: Flag-gated installation with immediate `/root/.cache/pip` cleanup. |

## 2. The "Fortress" Verification Suite
Before the competition API starts, the following TDD suite MUST pass:
1.  **Hardware Lock**: Verify H100 availability.
2.  **Environment Check**: Verify all `cp312` wheels are imported correctly.
3.  **Symbolic Sanity**: Run a dummy equation solve via SymPy.
4.  **Dummy Inference**: Run a full "Proposer + Advocate" cycle on a mock problem.

## 3. Bidirectional References
- **Implementation**: [sandbox/aimo/kaggle_kernel/submission_transformers.py](../../../sandbox/aimo/kaggle_kernel/submission_transformers.py)
- **Project Plan**: [conductor/tracks/aimo_progress_prize_3_20260319/plan.md](plan.md)
- **SOTA Synthesis**: [conductor/tracks/aimo_progress_prize_3_20260319/SOTA_2026_SYNTHESIS.md](SOTA_2026_SYNTHESIS.md)

## 4. Maintenance
This protocol is updated after every failed Kaggle "Save" or "Submission" run. Current version: **April 6, 2026**.
