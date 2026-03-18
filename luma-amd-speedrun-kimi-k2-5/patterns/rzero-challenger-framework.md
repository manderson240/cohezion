---
type: pattern
name: rzero-challenger-framework
date: 2026-03-17
---

# R-Zero Challenger Framework

## Overview
Systematic approach to generate and evaluate 100+ kernel variants locally before submission.

## Framework Components

### 1. Generation (`generate_challengers.py`)
- **GEMM**: 33 challengers with grid search over:
  - Tile sizes: 32×128 to 256×128 (6 variants)
  - Split-K: 0-4 (5 levels)
  - Shape thresholds: 8, 16, 32, 64
  
- **MoE**: 33 challengers with grid search over:
  - KSPLIT: 1, 2, 3, 4, 6, 8
  - Expert thresholds: (5,15), (10,30), (15,40)
  - OPUS sorting: True/False
  
- **MLA**: 28 challengers with grid search over:
  - num_kv_splits: 1, 2, 4, 8, 16, 32, 64
  - fast_mode: True/False
  - intra_batch_mode: True/False

### 2. Evaluation (`rzero_eval.py`)
- Local testing against reference implementations
- Correctness check: rtol=1e-2, atol=1e-2
- Performance measurement: speedup ratio
- Test shapes: Competition benchmark shapes

### 3. Selection (`rzero_select.py`)
- Tournament selection: Random pairing, winner advances
- Top 20% retention
- Statistics tracking: best, avg, median speedup

### 4. Mutation (`rzero_mutate.py`)
- **GEMM**: Perturb log2_ks (±1), threshold (±1 level)
- **MoE**: Perturb KSPLIT, expert thresholds
- **MLA**: Perturb num_splits (×2 or ÷2)
- Crossover: Combine parameters from two parents

## Key Learnings

### GEMM Optimization Space
- Small M (≤16): Use 32×128/256 tiles with high split-K (3-4)
- Medium M (16-64): Use 128×128 tiles with moderate split-K (1-2)
- Large M (>64): Use 192×128/256×128 tiles with no split-K (0)
- Shape-adaptive dispatch is critical

### MoE Optimization Space
- Sparse workloads (est_m < 5): Higher KSPLIT (4-8)
- Dense workloads (est_m > 30): Lower KSPLIT (1-2)
- OPUS sorting helps routing efficiency
- `doweight_stage1=True` is broken (never use)

### MLA Optimization Space
- num_kv_splits balances parallelism vs overhead
- Formula: minimize (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + 84.1 * i)
- fast_mode=True uses v1_2_device (faster)
- intra_batch_mode=True uses v1_0_device (more flexible)

## Execution

```bash
# Generate 100 challengers
python3 generate_challengers.py

# Evaluate all challengers locally
python3 rzero_eval.py

# Select top performers
python3 rzero_select.py

# Generate mutations
python3 rzero_mutate.py
```

## Results Location
- Challengers: `rzero-challengers/{gemm,moe,mla}/challenger_*.py`
- Results: `rzero-results/results.json`
- Analysis: `rzero-results/`

## Next Steps
1. Run local evaluation on all 100 challengers
2. Identify top 20% performers
3. Generate mutations from winners
4. Iterate until breakthrough achieved
5. Submit only validated winners
