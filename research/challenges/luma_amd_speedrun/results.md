# Luma AMD Speedrun - Benchmark Results

## Reference Performance (from task.yml descriptions)

### MXFP4 GEMM (aiter baseline)
| M | N | K | time [us] |
|---|---|---|-----------|
| 4 | 2880 | 512 | 8.198 |
| 16 | 2112 | 7168 | 20.873 |
| 32 | 4096 | 512 | 9.462 |
| 32 | 2880 | 512 | 9.173 |
| 64 | 7168 | 2048 | 12.738 |
| 256 | 3072 | 1536 | 12.219 |

### MoE MXFP4 (aiter baseline)
| bs | E | d_hidden | d_expert | top_k | time [us] |
|----|---|----------|----------|-------|-----------|
| 16 | 257 | 7168 | 256 | 9 | 152.7 |
| 128 | 257 | 7168 | 256 | 9 | 239.0 |
| 512 | 257 | 7168 | 256 | 9 | 336.5 |
| 16 | 33 | 7168 | 512 | 9 | 106.2 |
| 128 | 33 | 7168 | 512 | 9 | 141.1 |
| 512 | 33 | 7168 | 512 | 9 | 225.0 |
| 512 | 33 | 7168 | 2048 | 9 | 380.4 |

### MLA Decode (aiter baseline)
_No reference timings provided in task.yml. Will capture via --mode benchmark._

## Our Submission Results

### Round 1: Initial Optimized Submissions
_Pending Popcorn CLI auth resolution. Submissions ready._

#### GEMM Changes
- Module-level quant_func caching (avoid per-call get_triton_quant overhead)
- Removed unnecessary B.contiguous() call
- Same CK-based gemm_a4w4 path (conservative)

#### MLA Changes (MAJOR)
- Replaced naive torch._scaled_mm loop with aiter mla_decode_fwd persistent kernel
- fp8 Q + fp8 KV path (matches reference approach)
- Expected: significant speedup over previous naive implementation

#### MoE Changes
- Identical to reference (fused_moe is already heavily optimized)
- Shared expert specialization deferred to later iteration
