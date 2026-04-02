# AMD Speedrun Test Results Summary

## MLA (amd-mixed-mla)

### Working Variants (Status: done)
1. **submission_aggressive.py** ✅
   - bs<=8 OR total_kv<=65536
   - Expected: ~70µs
   
2. **submission_fastmode.py** ✅
   - fast_mode=True variant
   - Testing if fast_mode helps
   
3. **submission_sdpa.py** ✅
   - F.scaled_dot_product_attention for small shapes
   
4. **submission_triton_cdna4.py** ⚠️
   - May have "work on another stream" error
   - Triton kernels blocked by runner

5. **submission.py (aggressive)** ✅
   - Current active submission

### Failed Variants
- submission_ultra.py ❌ (work on another stream)
- submission_direct_ck.py ❌ (work on another stream)
- submission_cudagraph.py ❌ (work on another stream)
- submission_ultra_aggressive.py ❌ (work on another stream)

**Pattern:** Any custom kernel dispatch (ctypes, CUDA graphs, Triton) is blocked.

## MoE (amd-moe-mxfp4)

### Tested
- submission.py (original) ✅
- submission_asm_moe.py ⏳ (pending results)
- submission_fp8_blockscale.py ⏳ (pending results)

## GEMM (amd-mxfp4-mm)

### Tested
- submission.py ✅
- submission_ultra.py ⏳ (pending results)

## Rate Limit
- 6 test submissions per hour
- Current limit exceeded
- Next available: ~30+ minutes

## Working Strategy
Only API-level optimizations work (no custom kernels):
1. Wider matmul regimes
2. Batch size thresholds
3. Pre-allocated buffers
4. Minimal torch operations

Custom kernels (Triton, HIP, ctypes) all fail with "work on another stream".
