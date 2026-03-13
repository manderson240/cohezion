---
type: antigravity-artifact
session_id: ada764e1-6829-4b4c-a85a-e111080303ad
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.55
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---


# Walkthrough: VLIW Kernel Optimization (2088 Cycles)

We achieved a **70x speedup** (2,088 cycles vs 147,734 baseline) on the Anthropic Challenge kernel by leveraging VLIW parallelism, vectorization, and dependency optimization.

## Key Optimizations

### 1. Pure Vector Architecture (18 Windows)
We abandoned the "Hybrid" Scalar/Vector approach in favor of a robust **Pure Vector** architecture using 18 concurrent Register Windows.
- **Why**: Maximizes memory bandwidth saturation. 18 windows effectively hide the 4-cycle memory latency.
- **Config**: `N_VEC=18`, `N_SCAL=0`. Fits within 1536-word scratchpad by careful constant management.

### 2. VLIW Dependency Tuning
A critical performance regression (3456 cycles) was traced to overly conservative dependency checking in our custom `VLIWPacker`.
- **Fix**: Allowed Write-After-Read (WAR) operations to occur in the *same cycle* (Strict vs Loose dependency tracking).
- **Result**: Immediate 1.7x speedup (3456 -> 2088 cycles).

### 3. Smart Load Logic
We optimized the top of the tree (Rounds 0, 1) by bypassing memory loads:
- **Round 0 (1 Node)**: Broadcast value directly.
- **Round 1 (2 Nodes)**: Arithmetic Mux (vselect).
- **Round 2+**: Falls back to Standard Gather (Memory Load) as Mux overhead exceeds Load throughput at 4+ nodes.

### 4. Bitwise Branchless Logic
Replaced complex control flow with bitwise arithmetic:
```python
idx = 2 * idx + 1 + (val & 1)  # Replaces 'if even/odd' branch
idx = vselect(idx < n_nodes, idx, 0) # Wrap logic
```

## Performance & Robustness

- **Final Cycles**: 2,088. (Goal: < 3,000).
- **Correctness**: Verified on standard test suite.
- **Limitations**:
    - **Batch Alignment**: processing logic assumes `batch_size % VLEN (8) == 0`. Unaligned batches (e.g., 255) will ignore tail elements.
    - **Recursion Depth**: tested robustly up to 16 rounds. Extremely high round counts (100+) may hit scratch limits depending on constant cache efficiency.

## Journey Log
1. **Baseline**: 147k cycles.
2. **Vectorization**: dropped to ~10k cycles.
3. **Windowing (12/3 Hybrid)**: hit 2021 cycles but unstable (scratch overflow).
4. **Regression**: Logic fix attempt spiked to 3456 cycles due to dependency bug.
5. **Recovery**: Fixed dependency logic and restored Pure Vector 18 config to hit 2088 cycles.

