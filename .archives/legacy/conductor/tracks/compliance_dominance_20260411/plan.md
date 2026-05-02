# Compliance & Leaderboard Dominance Plan (Multi-Agent Swarm)

## Objective
To deploy specialized agent teams (BMAD Party Mode / Subagents) to rapidly resolve compliance risks across four active Kaggle competitions and solidify our top leaderboard positions. The focus is on strictly adhering to competition constraints (hardware, licenses, API quotas, parameter limits) while leveraging the unique strengths of our `gemini-architect-2m`, `gemini-coder-1m`, and local Ollama specialists.

## Background & Motivation
An audit of our recent breakthroughs revealed several critical compliance risks:
- **BirdCLEF 2026:** Submissions must be CPU-only ($\le$ 90 mins). Our current ROCm optimization strategy is invalid for the scoring run.
- **Nemotron Reasoning:** Strict LoRA rank 32 limit and a prohibition against distilling proprietary models (must use open-weight teacher traces).
- **Measuring AGI:** A valid benchmark submission requires evaluation across at least 5 different models. We currently only have `phi4` and `qwen3-coder`.
- **AIMO:** Open-weight mandate and a strict pre-March 15, 2026 release date constraint for any runtime models.

To resolve these simultaneously without exceeding time budgets, we must parallelize the fixes using distinct, specialized AI agents.

## The Multi-Agent Orchestration Plan

### Phase 1: BirdCLEF CPU Pivot (The Optimization Team)
- **Agent Assigned:** `gemini-coder-1m` (Code Specialist) + `phi4-256k` (Math/Algo Specialist).
- **Action:** Refactor `src/cohezion/models/birdclef_baseline.py` and `sandbox/birdclef/inference.py`. Strip out PyTorch/ROCm GPU dependencies and replace them with **ONNX Runtime (CPU provider)** or **OpenVINO**.
- **Constraint Check:** Ensure audio spectrogram processing (librosa/torchaudio) runs entirely in RAM within the 90-minute limit.

### Phase 2: Measuring AGI Quota Scaling (The API Integration Team)
- **Agent Assigned:** `gemini-architect-2m` (System Architect) + `glm-4.7-flash-256k` (Prototyping Specialist).
- **Action:** Update `kaggle-agi-benchmark/evaluator_kbench.py`. Integrate the `AI Models API` (using the designated $50/day quota) to run the 75-task benchmark against three additional frontier models: `Gemini 1.5 Pro`, `Claude 3.5 Haiku`, and `Llama-3-70b-Instruct`.
- **Validation:** Aggregate the scores from all 5 models into a new leaderboard output and update the Kaggle writeup.

### Phase 3: Nemotron Trace Generation & Rank Enforcement (The Training Team)
- **Agent Assigned:** `gemini-coder-1m` (Code Specialist).
- **Action:** 
  1. Inspect `sandbox/aimo/kaggle_kernel/nemotron_lora_training_v29.py` to confirm `r=32` and `lora_alpha=32` (or 64, verifying standard practice for this competition) are hardcoded.
  2. Implement an open-weight teacher trace generation script (`sandbox/nemotron/generate_traces.py`) using `DeepSeek-R1-Distill-Qwen-32B` to ensure compliance with the distillation rules.

### Phase 4: AIMO Open-Weight Audit (The Compliance Guard)
- **Agent Assigned:** `codebase_investigator` (Sub-agent).
- **Action:** Audit the `submission_v43_fortress.py` script. Verify that `Qwen2.5-Math-7B-Instruct` (the primary fallback) was released prior to March 15, 2026, and uses an OSI-approved license.

## Verification
- Submit the refactored BirdCLEF notebook to Kaggle to confirm the CPU-only execution passes.
- Push the expanded AGI benchmark notebook to Kaggle and verify it generates a 5-model leaderboard.
- Validate that the Nemotron adapter compiles successfully with Rank 32.
