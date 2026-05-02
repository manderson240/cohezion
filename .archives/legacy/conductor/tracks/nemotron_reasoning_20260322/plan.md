# Implementation Plan: NVIDIA Nemotron Model Reasoning Challenge

## Phase 1: Shared Kaggle Infrastructure & Local Eval
- [x] Task: Implement Kaggle API Integration
    - [x] Write Failing Tests: Verify Kaggle API wrapper functions (mocked endpoints).
    - [x] Implement: Create a utility module to download datasets and push notebooks/scripts using the Kaggle API.
- [x] Task: Build Local Evaluation Suite
    - [x] Write Failing Tests: Verify regex extraction of the LaTeX `\boxed{}` command and accuracy scoring logic.
    - [x] Implement: Create the evaluation module to measure local model reasoning accuracy against the standard.
- [x] Task: Conductor - User Manual Verification 'Shared Kaggle Infrastructure & Local Eval' (Protocol in workflow.md)

## Phase 2: Data Curation & FLUME Integration
- [x] Task: Integrate FLUME VAE for Data Encoding
    - [x] Write Failing Tests: Verify dataset parsing and embedding extraction logic via FLUME.
    - [x] Implement: Write the data curation pipeline to prepare the competition dataset locally.
- [x] Task: Conductor - User Manual Verification 'Data Curation & FLUME Integration' (Protocol in workflow.md)

## Phase 3: Kaggle LoRA Training Pipeline
- [x] Task: Develop Kaggle Training Script
    - [x] Write Failing Tests: Verify generation of the LoRA configuration and `adapter_config.json`.
    - [x] Implement: Create the primary training script that loads `Nemotron-3-Nano-30B-A3B` in BF16 and configures LoRA using `mamba_ssm`.
- [x] Task: Automated Kaggle Notebook Deployment
    - [x] Write Failing Tests: Verify notebook generation and push commands.
    - [x] Implement: Script the deployment of the training script directly to a Kaggle Notebook utilizing the Kaggle G4 VMs.
- [x] Task: Conductor - User Manual Verification 'Kaggle LoRA Training Pipeline' (Protocol in workflow.md)

## Phase 4: Baseline Submission
- [x] Task: Execute Training and Generate Adapter
    - [x] Implement: Run the pipeline, pushing to Kaggle, and retrieve the resulting `adapter_config.json` and weights.
- [x] Task: Automate Kaggle Submission
    - [x] Write Failing Tests: Verify submission format and API call parameters.
    - [x] Implement: Use the Kaggle API integration to submit the resulting LoRA adapter to the competition.
- [x] Task: Conductor - User Manual Verification 'Baseline Submission' (Protocol in workflow.md)

## Phase 5: Execution & Monitoring (Debug Phase)
- [x] Task: Monitor and Debug G4 Blackwell Training Progress
    - [x] Implement: Monitor the Kaggle G4 Blackwell notebook execution for completion (Found errors in v22).
    - [x] Implement: Investigate `TypeError: object of type 'NoneType' has no len()` in IPython/nbconvert tracebacks seen in v22 and v24 logs. (Fixed in v27 by avoiding `sys.exit(1)` and using a `safe_exit` pattern).
    - [x] Implement: Fix environment setup to prevent Kaggle notebook conversion failures. (Applied Blackwell Handshake Mandate 8: fixed machine_shape, pinned dockerImageVersionId, and refactored dependency installation).
    - [x] Implement: Prepare and Upload ROCm-compatible wheel dataset to Kaggle (trl, bitsandbytes) to resolve G4 Blackwell dependency blocks.
    - [ ] Implement: Retrieve the trained LoRA adapter and metrics once a successful run completes (Monitoring v27).
- [ ] Task: Submit Trained Adapter to Competition
    - [ ] Implement: Use Kaggle API to submit the trained adapter as a competition entry
- [ ] Task: Evaluate Leaderboard Position
    - [ ] Implement: Check competition leaderboard to verify placement
- [ ] Task: Conductor - User Manual Verification 'Execution & Monitoring' (Protocol in workflow.md)

## Phase 6: MoE-Specific Optimization (Research & Refinement)
- [~] Task: Analyze Router Weights Influence
    - [x] Implement: Push analysis Kaggle kernel to check MoE gate variance and entropy.
    - [ ] Implement: Propose a LoRA configuration that targets the learned MLP router to prevent expert collapse on reasoning tasks.
- [ ] Task: Mixed-Architecture Benchmarking
    - [ ] Implement: Run internal benchmarks comparing Mamba-2 layer performance vs. GQA layer performance for math reasoning.
- [ ] Task: Conductor - User Manual Verification 'MoE Optimization' (Protocol in workflow.md)

## Phase 7: Metric & Evaluation Alignment
- [ ] Task: Ensure `\boxed{}` Formatting Compliance
    - [ ] Implement: Update the data curation pipeline (`kaggle_curation.py`) to enforce that all generated answers are strictly enclosed in `\boxed{...}`.
- [ ] Task: vLLM Compatibility Check
    - [ ] Implement: Verify that the generated `adapter_config.json` uses `peft_type="LORA"` and `task_type="CAUSAL_LM"` exactly as expected by the competition's vLLM evaluation script.
- [ ] Task: Conductor - User Manual Verification 'Metric Alignment' (Protocol in workflow.md)

## Phase 8: Submission Governance & Reproduction
- [ ] Task: Daily Submission Limit Monitoring
    - [ ] Implement: Add logic to the submission script to check the current daily submission count via the Kaggle API before attempting a new submission.
- [ ] Task: Document Reproduction Environment
    - [ ] Implement: Create a `REPRODUCTION.md` file documenting the exact Docker image (`dockerImageVersionId: 31287`), hardware (Blackwell G4), and dependency installation steps (`--no-build-isolation`).
- [ ] Task: Conductor - User Manual Verification 'Submission Governance' (Protocol in workflow.md)

## Phase 9: Blackwell FP4 Transition (v21 Mutation)
- [ ] Task: Transformer Engine (TE) Integration
    - [ ] Implement: Integrate `nvidia-transformer-engine` into the Kaggle environment setup logic.
- [ ] Task: FP4 Micro-Tensor Scaling Implementation
    - [ ] Implement: Refactor the training loop to use `te.autocast` with the `NVFP4BlockScaling` recipe for 4x throughput.
- [ ] Task: FP4 Accuracy & Throughput Benchmark
    - [ ] Implement: Execute v21 and compare results against the v20 BF16 baseline to ensure no "Reasoning Decay" occurs in 4-bit floating point.
- [ ] Task: Conductor - User Manual Verification 'FP4 Optimization' (Protocol in workflow.md)