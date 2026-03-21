# Cohezion Session Handoff: Kaggle "Measuring AGI" Benchmark

## 1. Goal Overview
We are building an **Epistemic Humility** benchmark for the Kaggle Measuring AGI competition, using Cohezion's `CompoundSessionManager` and 12D Manifold physics (EVOs, Bioelectric Cognition, Esoteric Physics) to test if models know what they don't know (0.5 Coherence thresholds).

## 2. What We Accomplished in this Session
1. **Kaggle Infrastructure Deployed**: We successfully connected the local environment to Kaggle using `uv` and the `KAGGLE_API_TOKEN`. We initialized and pushed the `kaggle_benchmark.json` as a Kaggle dataset (`manderson240/cohezion-agi-benchmark`), and deployed the benchmark evaluation loop as a Kaggle Kernel (`evaluator.ipynb`).
2. **Kaggle Evaluator Build**: The deployed notebook utilizes `kagglehub` dynamically to download and run inference on `Qwen2.5-7B-Instruct` and `DeepSeek-R1-Distill-7B` on Kaggle's dual-T4 accelerators.
3. **Automated Research Sweeps**: Updated `overnight_driver.py` to hit the Research MCP Server daily, querying ArXiv and HuggingFace, storing the novel models/papers in SurrealDB, and emailing the results.

## 3. The Core Problem (Where the next session must start)
While the pipeline is fully connected locally and remotely, **we identified critical deficiencies in the local generative loop that must be fixed before running the final Kaggle evaluations.**

### A. Generator JSON Parsing Bug
**Files:** `kaggle-agi-benchmark/generate_evo_hiho_tasks.py` & `src/cohezion/swarm/r_zero_evolver.py`
**Issue:** The local LLM (`minimax-m2.7:cloud` or `deepseek-r1`) outputs valid traps wrapped in markdown ```json ... ``` blocks. The current `response_text.find("{")` parsing logic is brittle and throwing exceptions. As a result, the script falls back to generating placeholders (`"question": "Task 0"`).
**Fix Required:** Implement robust RegEx parsing (`re.search(r"```json\s*(.*?)\s*```", text, re.DOTALL)`) or convert the swarm request to use strict `pydantic` schemas for structured generation.

### B. Evaluator Loop Sycophancy Loophole
**File:** `kaggle-agi-benchmark/adversarial_eval_loop.py`
**Issue:** The loop currently checks if the model responded with any string matching `"insufficient information"`. An advanced model might respond: *"There is insufficient information, however precipitation occurs..."* – falling for the trap while accidentally triggering our success condition.
**Fix Required:** Enhance the evaluator constraints. Force the model to select a specific option (e.g., "(D) Insufficient Information"), and penalize any confident physics confabulation in its CoT trace.

## 4. Next Steps
- [ ] Fix the aforementioned JSON parsing bugs in the generative loop scripts.
- [ ] Tighten the regex constraints in `adversarial_eval_loop.py`.
- [ ] Execute `r_zero_evolver.py` locally to properly harness the "Challenger -> Solver -> Majority Vote -> Cache" self-refining loop to build the real dataset.
- [ ] Re-run formatting and use `kaggle datasets version -m "Update traps"` to push the corrected JSON payload up to Kaggle.
