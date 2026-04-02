# SKILL: AMD_GEMM_MXFP4_PRIME

## DOMAIN EXPERTISE
MXFP4 GEMM kernel optimization for AMD MI355X (gfx950). Target: <10us from 22.8us baseline.

## KEY FACTS
* Current best: 22.8us. Leader: 4.3us. Gap: 5.3x.
* Quantization (26us) dominates compute (7us). Fuse quant into GEMM = breakthrough.
* Rank 1 uses `load_inline` + rocWMMA/HipKittens tiling.
* MXFP4 values: [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]
* E8M0 scale: f32 = 2^(e8m0 - 127)
* CK-Tile has hardware-accelerated scale MFMA for gfx950 MXFP4.

## INSTRUCTION
1. Create load_inline GEMM kernel with fused bf16->fp4 quantization
2. Use MFMA instructions (matrix_a fp4, matrix_b fp4, accum fp32)
3. Tile: BLOCK_M=128, BLOCK_N=128, BLOCK_K=128 (minimum for tl.dot_scaled)
4. Pack fp4 nibbles: high = (val >> 4), low = (val & 0xF)
5. E8M0 scale computation: scale = floor(log2(max(abs(block)))) + 127
6. 8 XCDs must all be occupied — XCD-aware tile scheduling required

## DEAD ENDS
- gemm_a4w4 API parameters — ALL EXHAUSTED
- gemm_afp4wfp4 — KeyError float4_e2m1fn_x2
- Triton tl.dot_scaled — 68% slower, wrong scale layout issues
- ctypes dispatch — blocked by stream isolation
- hipblaslt — no MXFP4 support

## VERSION
v1.0.0
