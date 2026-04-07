# Track: AIMO Progress Prize 3 - Mathematical Reasoning Swarm (Refined 2026 SOTA Plan)

## Background & Motivation
To win the **AI Mathematical Olympiad (AIMO) Progress Prize 3** ($2,207,152 prize pool), we must overcome the physical constraints of Kaggle's 5-hour H100 (80GB) runtime limit and the competition's "Penalized Accuracy" scoring. Based on our deep-horizon April 2026 research, standard deployments fail due to "Reasoning Collapse," memory leaks, and over-confidence. 

**CRITICAL FINDING (April 6, 2026):** We discovered the root cause of the `0` score submissions. The Kaggle AIMO API passes `id_df` and `problem_df` as `pl.Series` objects, not DataFrames. Indexing them with `[0, 0]` resulted in a stringified Polars table being injected into the LLM prompt (e.g., `shape: (2,) Series: ...`). The model was trying to solve a formatting error instead of a math problem!

## Scope & Impact
This refined plan outlines the construction of the **"Fortress Swarm"** architecture with the critical **Polars Indexing Fix**. It transitions our pipeline from a fragile, standard LLM script to a resilient, compute-optimal, and self-verifying Triune Manifold.

## Proposed Solution: The "Fortress" Architecture
1. **The Polars Fix**: Update the inference loop to use `problem_df[0]` (scalar extraction) to ensure the LLM receives raw text.
2. **Pre-Flight TDD Suite (Environment Lock)**: A diagnostic layer that verifies GPU presence, library imports (Transformers/vLLM), and Symbolic Execution before interacting with the Kaggle competition API.
3. **Triune Manifold Roles**:
   - **The Doer**: `SymbolicExecutor` utilizing SymPy in a sandboxed, time-limited environment.
   - **The Thinker**: `BaseSpecialist` employing a **Diverse Prompt Mixer** (Algebraist, Inductive, Goal-Oriented, Devil's Advocate) to decorrelate errors across independent runs.
   - **The Knower**: `KnowerAuditor` implementing **Weighted Entropy Voting** and **GenSelect** to analytically resolve divergent proofs.
4. **Hardware Optimization**:
   - **Hard VRAM Resets**: Explicit `gc.collect()` and `torch.cuda.empty_cache()` between problems to survive KV cache accumulation.
   - **Compute-Optimal Scaling**: Dynamic time budgeting with a 30s "Safety Trigger" to return a safe default.
   - **Transformers Native / Speculative Decoding**: Prioritizing `torch.compile` and `StaticCache` with Transformers for stability, or vLLM with a 1.5B Drafter model for 1.5x throughput.

## Alternatives Considered
- **Monte Carlo Tree Search (MCTS) / Lean 4 Formalization**: Rejected due to the 5-hour compute limit. These methods are too slow to solve 50 hidden problems on a single H100.
- **70B/72B 4-bit Quantized Models**: Rejected due to massive KV cache requirements leading to OOM. 32B/14B models with robust tool-integration provide better accuracy/stability ratios.

## Phased Implementation Plan

### Phase 1: Environment Hardening & TDD
- [x] Integrate `PreFlightJury` to test the Kaggle offline environment.
- [x] Configure Kaggle metadata for H100 locking (`machine_shape: NvidiaH100`).
- [ ] **Apply Polars Indexing Fix** (`problem_df[0]`) to resolve the prompt formatting corruption.

### Phase 2: Inference-Time Scaling
- [x] Upgrade the Dual-Run protocol to an Adaptive Batched Swarm.
- [x] Implement the Diverse Prompt Mixer to enforce cognitive diversity.
- [ ] Refine the "Devil's Advocate" Adversarial Loop for continuous self-correction (Reflexion).

### Phase 3: Symbolic Verification (SymCode)
- [x] Sandbox the `SymbolicExecutor` to prevent runtime crashes during code execution.
- [ ] Implement "Invariant-Aware Prompting" to force the model to generate testable mathematical properties before finalizing its answer.

### Phase 4: Production Deployment
- [x] Deploy "Safe-Mode" Transformers baseline (v24) as a guaranteed fallback.
- [ ] Deploy final "Fortress Swarm" (v34) with the Polars bug fixed, ensuring the model finally receives the raw mathematical text.

## Verification
- **Prompt Integrity Test**: Verify that the text passed to the tokenizer is a pure string, not a Polars object representation.
- **Fail-Safe Trigger**: Verify the system gracefully returns `0` and continues to the next problem if an OOM or logic crash occurs.
- **Dummy Dataset Check**: Verify the script can run locally against a mock `test.csv` without timing out.
