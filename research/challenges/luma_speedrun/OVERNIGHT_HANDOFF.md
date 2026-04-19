# Overnight Handoff — Session 90 → 91

## Critical Findings

### BF16 MFMA 16×16 OUTPUT MAPPING (CONFIRMED CORRECT)
```
c_reg[j] → C[(tid/16)*4 + j][tid % 16]
```
4 consecutive ROWS at column tid%16. Verified: passes 4/4 with max error 0.0.
But BF16 MFMA is slower than naive (24.7µs vs 13.4µs) due to FP4→BF16 dequant+LDS overhead.

### FP4 MFMA 32×32 OUTPUT MAPPING (STILL WRONG)
The blog's mapping `c_reg[i*4+j] → C[(tid/32)*4+j+i*8][tid%32]` does NOT work.
The 32×32 FP4 instruction has a DIFFERENT register layout from the 16×16 BF16.
Confirmed: custom kernel runs (verified with print) and fails all tests.

### Rate Limit Management
- 10 submissions/hour rolling window per leaderboard
- RATE LIMITED SUBMISSIONS COUNT toward the limit!
- Must wait FULL interval between attempts, don't retry immediately

## Current Submissions (all working)
- GEMM: `submission_naive_13us.py` → 13.4µs (load_inline naive)
- MoE: `submission.py` → 154µs (fused_moe + KSPLIT + USE_NT)
- MLA: `submission.py` → 69.7µs (3-regime stage1_asm + reduce)

## Files Available
| File | Status | Notes |
|------|--------|-------|
| `submission_fp4mfma_fixed.py` | FAILS | FP4 MFMA wrong output, correct path identification confirmed |
| `submission_bf16mfma_v2.py` | PASSES but slow | 24.7µs (BF16 dequant overhead) |
| `submission_probe.py` | PASSES | Runner environment probe (API map) |
| `submission_fmhav3.py` | PASSES (fallback) | fmha_v3 blocked (head_dim 256 limit) |
| `submit_and_iterate.sh` | Helper | Autonomous submission script |

## Untested Paths for Session 91
1. `per_1x32_f4_quant_hip` — HIP-native quant might be faster than Triton
2. `gemm_a4w4_asm` with `log2_k_split` parameter
3. `ck_moe_stage1` / `ck_moe_stage2` — direct CK MoE dispatch
4. `fmoe_g1u1_a16` — needs pre-sorted inputs from `moe_sorting_fwd`
5. FP4 MFMA with **experimental output mappings** — try permutations of the register layout

## Dead Ends (DO NOT RETRY)
- `asm_moe`: ImportError
- `hipModuleLaunchKernel`: blocked everywhere
- `fmha_v3_varlen_fwd` for MLA: head_dim 256 limit
- `gemm_a4w4_blockscale`: shapes not supported
- Per-scale-group LDS tiling: 15× slower
- FP4 MFMA with blog output mapping: wrong results
- BF16 MFMA: correct but slower than naive due to dequant overhead
