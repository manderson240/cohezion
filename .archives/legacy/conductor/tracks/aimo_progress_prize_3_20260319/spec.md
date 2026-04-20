# SPECIFICATION_PRIME: AIMO Mathematical Reasoning Swarm (MRS)

## 1. Objective
To achieve a score of ≥47/50 on the AIMO Progress Prize 3 leaderboard by deploying a sovereign reasoning swarm that treats mathematical proofs as stable trajectories in a high-dimensional manifold.

## 2. Architectural Pillars

### 2.1 The Doer (Perception & Execution)
- **Input**: LaTeX string from AIMO API.
- **Output**: 12D Problem State Vector + Symbolic Constraints.
- **Tools**: `MathParser` (Regex/NLP), `SymPy` (Symbolic Math), `NumPy` (Numerical validation).

### 2.2 The Thinker (Reasoning & Interpolation)
- **Input**: 12D State Vector.
- **Process**:
    - **Domain Routing**: Assigns the problem to one of four specialists: Algebra, Geometry, Number Theory, or Combinatorics.
    - **Long-Horizon Chain-of-Thought (CoT)**: Uses `DeepSeek-R1-32B` to generate step-by-step proofs.
    - **FLUME Encoding**: Maps proof steps to latent vectors to identify "logical drift."

### 2.3 The Knower (Validation & Stability)
- **Input**: Dual-run proof results.
- **Process**:
    - **Consistency Check**: Compares Run 1 and Run 2. If they differ, the problem is flagged for "High Ambiguity."
    - **Adversarial Review**: A secondary agent (e.g., `Phi-4`) reviews the proof for common "hallucination" patterns (e.g., sign errors, division by zero).
    - **Stability Score**: Calculates a confidence metric for the final integer answer.

## 3. Data Architecture & Ingestion

### 3.1 Dataset Manifest
| File | Path | Role |
|------|------|------|
| `reference.csv` | `/kaggle/input/ai-mathematical-olympiad-progress-prize-3/reference.csv` | 10 high-quality benchmark problems with ground truth. |
| `test.csv` | `/kaggle/input/ai-mathematical-olympiad-progress-prize-3/test.csv` | 50 placeholder problems (Public) / 50 hidden problems (Private). |
| `sample_submission.csv` | `/kaggle/input/ai-mathematical-olympiad-progress-prize-3/sample_submission.csv` | Template for the final prediction format (`id`, `answer`). |

### 3.2 Ingestion Protocol
The system must utilize the official `aimo` Python API to iterate through the `test.csv` records. The **Doer** layer will read each problem string sequentially from the `test` DataFrame provided by the API.

### 3.3 Iterative Guardrails (Log Insights)
- **Single-Row Constraint**: The `aimo` API yields exactly one row per `iter_test()` iteration. Batch processing is impossible.
- **Stateful Validation**: `env.predict()` must be called exactly once per row. Calling it multiple times or out of order will cause an `AssertionError` and terminate the submission.
- **Progress Tracking**: Since the API is "quiet," the **Coordinator** must maintain internal telemetry (Problem X/110, Time elapsed, Avg latency) to avoid timeout.

## 4. Resource Management & Guardrails

### 3.1 Memory Safety (128GB RAM / 12GB VRAM)
- **Sequential Execution**: Only one large model (≥30B) loaded at a time.
- **Memory Flushing**: Use Ollama's `keep_alive: 0` or explicit model unloading between problems.
- **Quantization**: Primary models must be Q5_K_M or Q6_K to balance accuracy and memory.

### 3.2 Time Budgeting
- **Total Time**: 5 hours (18,000 seconds).
- **Target Problems**: 110.
- **Allocated Time per Problem**: 150 seconds.
- **Safety Margin**: 15 seconds per problem for overhead/I/O.

## 4. Model Selection (Pre-March 15, 2026 Cutoff)

| Role | Primary Model | Alternative |
|------|---------------|-------------|
| **Lead Reasoner** | `DeepSeek-R1-Distill-Qwen-32B` | `Qwen2.5-Math-72B-Instruct-Q4` |
| **Logic Verifier** | `Phi-4-7B` | `Mistral-7B-Instruct-v0.3` |
| **Code Executor** | `Qwen2.5-Coder-14B` | `DeepSeek-Coder-V2-Lite` |

## 5. Evaluation Loop
- **Benchmark**: 10 official AIMO reference problems.
- **Success Metric**: 100% accuracy on reference problems with <10% variance in dual-run consistency.
- **Stability Threshold**: ≥0.95 (Ratio of consistent runs to total runs).

## 6. Compliance & Ethics
- **Licensing**: All generated code and datasets to be released under **CC-BY 4.0**.
- **Rule Adherence**: No internet access during runtime. No human hand-labeling of test data.
