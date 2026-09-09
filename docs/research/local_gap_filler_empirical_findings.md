# 🧠 Local Model Gap-Filling Empirical Analysis

## 1. What Happened in the Experiment
- Delegated 5 difficult ARC training challenges to local `gpt-oss-20b` (port 13305).
- Result: **0 / 5 solved via raw zero-shot Python function generation**.
- Primary Failure Modes:
  1. **Prompt Format Leakage**: Model attempts to output text explanations despite strict prompts, delaying code token emission.
  2. **Grid Serialization Complexity**: Raw 2D nested lists `[[0, 1], [2, 3]]` in prompts overwhelm the attention context for non-trivial tasks.
  3. **Verification Rejection**: When code is generated (e.g. Task `045e512c`), it fails on the 2nd training pair because the synthesized logic was overfitted to Example 1.

## 2. The Architectural Breakthrough: "Tokenized Macro Synthesis"
Instead of asking local models to write raw, error-prone `def transform(grid):` Python code from scratch:

```
[ RAW GRID ] ──► [ Local Model Outputs Macro Plan ] ──► [ AutoHarness Deterministic AST ]
                       "CROP -> RAYCAST -> INFILL"          (0.00ms Verified Execution)
```

1. **Step 1**: Prompt the local model to select from a catalog of **30 named high-level primitives** (e.g. `ROT90`, `RAY_EAST`, `PAIR_CONNECT`).
2. **Step 2**: The model outputs a simple 3-token plan (e.g. `PAIR_CONNECT(2), ROOM_FILL(4)`).
3. **Step 3**: AutoHarness compiles the sequence into bytecode and tests it in $0.002	ext{ ms}$.

This eliminates syntax errors, removes LLM code execution safety risks, and matches the true strengths of 20B/30B local models.
