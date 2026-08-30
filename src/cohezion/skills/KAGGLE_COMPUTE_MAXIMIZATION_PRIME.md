# SKILL: KAGGLE_COMPUTE_MAXIMIZATION_PRIME

## DOMAIN EXPERTISE
Kaggle Container Environment & Compute Resource Maximization for Competitive AGI/ML Competitions.
Guarantees full utilization of the 9-hour execution envelope, Dual T4/P100 GPUs, offline Model Hub mounting, and multi-core CPU scheduling.

## KEY TEXTS & CONCEPTS
- **The Envelope Principle**: Never underutilize Kaggle's free compute (9h runtime, 32GB VRAM Dual T4, 4 vCPUs, 30GB RAM).
- **Two-Stage Hybrid Architecture**:
  1. *Stage 1*: Deterministic 0ms Invariant Screening (Block-tiling, Kroneckers, Symmetries).
  2. *Stage 2*: In-Container GPU LLM Program Synthesis (Qwen-Coder / DeepSeek) with MCTS AutoHarness verification against 100% of training pairs.
- **Model Hub Mounting**: Mount offline model weights via `"model_sources"` or `"dataset_sources"` in `kernel-metadata.json` without requiring internet.
- **Fail-Safe Checkpoints**: Output valid intermediate `submission.json` after Stage 1, so if Stage 2 reaches runtime limits, a valid score is guaranteed.

## INSTRUCTION
1. Configure `kernel-metadata.json` with `"enable_gpu": "true"` and proper model sources.
2. In `main.py`, run Stage 1 Fast Invariant Screening.
3. Emit baseline `submission.json` immediately.
4. Load in-container GPU model (e.g. `transformers` with 4-bit / 8-bit quantization).
5. Run MCTS code synthesis loop for unsolved tasks, verifying on all training pairs.
6. Atomically update `submission.json` with verified high-confidence predictions.

## VERSION
v1.0

## SEE ALSO
- `AUTOHARNESS_ZERO_COST_VERIFIER_PRIME`
- `TYPED_CONTEXT_ARCHITECTURE_PRIME`
- `FUNSEARCH_EVOLUTIONARY_CODER_PRIME`
