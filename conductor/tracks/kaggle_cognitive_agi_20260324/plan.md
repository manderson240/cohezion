# Implementation Plan: Measuring Progress Toward AGI - Cognitive Abilities Kaggle Competition

## Phase 1: Context & Synthetic Task Generation
- [x] Task: Research existing `kaggle-agi-benchmark/` directory and Kaggle competition dataset constraints.
- [x] Task: Implement `generate_evo_hiho_tasks.py` improvements.
    - [x] Sub-task: Refactor prompt generation for ARC-AGI style grid patterns.
    - [x] Sub-task: Ensure output format strictly matches `kaggle_benchmark.json` schema.
- [x] Task: Write/update tests for synthetic task generator.
- [x] Task: Conductor - User Manual Verification 'Context & Synthetic Task Generation' (Protocol in workflow.md)

## Phase 2: FLUME Evaluation Loop
- [x] Task: Integrate FLUME core with `adversarial_eval_loop.py`.
    - [x] Sub-task: Setup FLUME encoder/decoder for grid states.
    - [x] Sub-task: Implement scoring function comparing predicted vs expected state.
- [x] Task: Write/update tests for adversarial evaluation loop.
    - [x] Sub-task: Test against a known synthetic dataset.
- [x] Task: Conductor - User Manual Verification 'FLUME Evaluation Loop' (Protocol in workflow.md)

## Phase 3: Notebook Pipeline Optimization
- [x] Task: Update `build_notebook.py` for automated dependency inclusion.
    - [x] Sub-task: Ensure Kaggle offline constraints are met (e.g., wheel bundling if needed).
- [x] Task: Refine `pipeline.ipynb` and `evaluator.ipynb` for final execution.
- [x] Task: Test the generated notebooks locally using Jupyter/IPython CLI tools.
- [x] Task: Conductor - User Manual Verification 'Notebook Pipeline Optimization' (Protocol in workflow.md)

## Phase 4: Final Deliverables & Documentation
- [x] Task: Update `format_kaggle_submission.py` to ensure `submission.csv` is correctly shaped.
- [x] Task: Draft `kaggle_writeup.md` documenting methodology, FLUME setup, and empirical findings.
- [x] Task: Final end-to-end dry run of the evaluation loop and submission pipeline.
- [x] Task: Conductor - User Manual Verification 'Final Deliverables & Documentation' (Protocol in workflow.md)

## Phase 5: Leaderboard Optimization & Iterative Refinement
- [~] Task: Execute full-scale synthetic generation (100+ tasks) using `generate_evo_hiho_tasks.py` (Running autonomously in background).
- [x] Task: Create an automated Kaggle submission and leaderboard polling script (`check_leaderboard.py`).
- [ ] Task: Fix `generate_evo_hiho_tasks.py` placeholder output issue.
    - [ ] Sub-task: Refine the `GENERATION_PROMPT` to enforce strict grid arrays instead of string placeholders (`[[...]]`).
    - [ ] Sub-task: Implement a JSON schema validation check before saving tasks to `evo_hiho_benchmark.json`.
- [ ] Task: Run the evaluation notebook on top Kaggle models (e.g., Qwen 2.5 72B, Llama 3) to establish a baseline score.
- [ ] Task: Analyze model failure modes and refine the `GENERATION_PROMPT` to increase trap difficulty without violating logical soundness.
- [ ] Task: Repeat Generation -> Evaluation -> Submission loop until leaderboard target is achieved.