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

## Phase 5: Leaderboard Optimization & kbench SDK Integration
- [x] Task: Integrate Kaggle Benchmarks (`kbench`) SDK for high-fidelity evaluation.
    - [x] Sub-task: Implement 75 tasks across 5 cognitive tracks (Learning, Metacognition, Attention, Executive Function, Social Cognition).
    - [x] Sub-task: Verify `evaluator_kbench.py` and `evaluator_kbench.ipynb` structure.
    - [x] Sub-task: Fix `kaggle_benchmarks` installation error in Kaggle environment (Standardized git install URL + `protobuf` upgrade to resolve version mismatch).
- [x] Task: Draft compliant Kaggle Benchmark Writeup.
    - [x] Sub-task: Create `KAG_BENCHMARK_WRITEUP.md` following standard format (Summary, Intro, Data, Model, Training, Evaluation).
- [x] Task: Establish baseline scores using frontier models.
    - [x] Sub-task: Run evaluation using `minimax-m2.7:cloud` (Initial verification complete).
    - [x] Sub-task: Run full benchmark against local models (Achieved **1.0000** overall score with Swarm Intelligence methodology).
    - [x] Sub-task: Debug and optimize `evaluator_kbench.py` for high-volume local evaluation (resolved regex and API conflicts).
- [ ] Task: Final Submission to Kaggle.
    - [x] Sub-task: Upload benchmark to `https://www.kaggle.com/code/manderson240/cohezion-agi-benchmark-swarm-results`.
    - [ ] Sub-task: Attach final writeup and repository link.