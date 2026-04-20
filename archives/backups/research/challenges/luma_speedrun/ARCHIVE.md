# AMD Speedrun Submission Archive

## Session Summary
**Date:** 2026-03-31  
**Runtime:** ~19+ hours  
**Status:** Continuous submission pipeline completed

## Final Submissions

### MLA (amd-mixed-mla)
Latest: 677959 - submission.py (done)
Previous: 677923, 677851, 677823, 677034

### MoE (amd-moe-mxfp4)  
Latest: 677786 - submission.py (done)
Previous: 677711, 677073, 676985, 674964

### GEMM (amd-mxfp4-mm)
Latest: 677637 - submission.py (done)
Previous: 677581, 677520, 677449, 677407

## Key Variants Created

### MLA Variants:
- submission_aggressive.py - bs≤8, total_kv≤65536
- submission_hyper.py - bs≤32, total_kv≤262144
- submission_no_cache.py - Disable metadata caching
- submission_sdpa.py - SDPA fusion
- submission_fastmode.py - fast_mode=True
- submission_triton_cdna4.py - CDNA 4 Triton (blocked)

### MoE Variants:
- submission_minimal.py - Reduced Python overhead
- submission_ultra_sorting.py - Larger sorting blocks
- submission_asm_moe.py - ASM path
- submission_fp8_blockscale.py - FP8 block-scale

### GEMM Variants:
- submission_inline.py - Inline quantization
- submission_prealloc.py - Pre-allocated output
- submission_loadinline.py - Load inline
- submission_tritonblas.py - TritonBLAS

## Scripts Created:
- autosubmit.py - Continuous submission pipeline
- batch_submit.sh - Batch variant submission
- rotate_submit.sh - Rotation submission
- monitor.sh - Monitor submissions
- watch.sh - Watch until 7 AM

## Key Learnings:
1. Custom kernels (Triton/HIP/ctypes) blocked by runner
2. Only API-level optimizations work
3. Rate limit: 6 submissions/hour
4. MoE has smallest gap to leader (1.6x)
5. At API ceiling for all kernels

## Next Steps:
- Check leaderboard rankings
- Analyze timing results
- Continue parameter sweeps if needed
- Focus on MoE (closest to leader)

## Files Location:
/home/mike-anderson/dev/cohezion/luma_speedrun/
├── amd-mixed-mla/ (13 submission variants)
├── amd-moe-mxfp4/ (7 submission variants)
├── amd-mxfp4-mm/ (6 submission variants)
├── autoresearch/ (K-Search infrastructure)
└── variants/ (parameter sweep variants)
