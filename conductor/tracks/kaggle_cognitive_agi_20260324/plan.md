# Implementation Plan: Measuring Progress Toward AGI - Cognitive Abilities Kaggle Competition

## Phase 1: Context & Synthetic Task Generation
- [ ] Task: Research existing `kaggle-agi-benchmark/` directory and Kaggle competition dataset constraints.
- [ ] Task: Implement `generate_evo_hiho_tasks.py` improvements.
    - [ ] Sub-task: Refactor prompt generation for ARC-AGI style grid patterns.
    - [ ] Sub-task: Ensure output format strictly matches `kaggle_benchmark.json` schema.
- [ ] Task: Write/update tests for synthetic task generator.
- [ ] Task: Conductor - User Manual Verification 'Context & Synthetic Task Generation' (Protocol in workflow.md)

## Phase 2: FLUME Evaluation Loop
- [ ] Task: Integrate FLUME core with `adversarial_eval_loop.py`.
    - [ ] Sub-task: Setup FLUME encoder/decoder for grid states.
    - [ ] Sub-task: Implement scoring function comparing predicted vs expected state.
- [ ] Task: Write/update tests for adversarial evaluation loop.
    - [ ] Sub-task: Test against a known synthetic dataset.
- [ ] Task: Conductor - User Manual Verification 'FLUME Evaluation Loop' (Protocol in workflow.md)

## Phase 3: Notebook Pipeline Optimization
- [ ] Task: Update `build_notebook.py` for automated dependency inclusion.
    - [ ] Sub-task: Ensure Kaggle offline constraints are met (e.g., wheel bundling if needed).
- [ ] Task: Refine `pipeline.ipynb` and `evaluator.ipynb` for final execution.
- [ ] Task: Test the generated notebooks locally using Jupyter/IPython CLI tools.
- [ ] Task: Conductor - User Manual Verification 'Notebook Pipeline Optimization' (Protocol in workflow.md)

## Phase 4: Final Deliverables & Documentation
- [ ] Task: Update `format_kaggle_submission.py` to ensure `submission.csv` is correctly shaped.
- [ ] Task: Draft `kaggle_writeup.md` documenting methodology, FLUME setup, and empirical findings.
- [ ] Task: Final end-to-end dry run of the evaluation loop and submission pipeline.
- [ ] Task: Conductor - User Manual Verification 'Final Deliverables & Documentation' (Protocol in workflow.md)