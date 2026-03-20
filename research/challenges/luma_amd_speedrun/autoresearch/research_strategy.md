# Research Strategy (Human-Editable)

This file guides the LLM world model's optimization direction.
Edit priorities and dead ends to steer overnight runs.
The autoresearch loop reads this before each LLM call.

## Current Focus

- **MoE** (50% budget): Try direct `moe_sorting_fwd` with `local_expert_mask` parameter.
  Explore `fmoe_g1u1` for 256-expert shapes (NaN for 32-expert — do NOT try there).
  KSPLIT adaptive strategy: KSPLIT=4 for sparse (>200 experts), KSPLIT=2 otherwise.
- **GEMM** (30% budget): Explore `tritonblas.matmul_fp4` as alternative to `gemm_a4w4`.
  Fused quant+GEMM is the only path below API ceiling (~33µs).
  All tensors MUST be `torch.uint8` views for tritonblas. B layout is [N, K//2] row-major.
- **MLA** (20% budget): At Python dispatch ceiling (~67.8µs vs leader 4.3µs, 15.8x gap).
  Deprioritize unless custom Triton/CK kernel path opens up.
  Three-regime routing (matmul + aiter a16w8 + aiter a8w8) with `fast_mode=False` is optimal.

## Dead Ends (Do NOT retry)

- `gemm_afp4wfp4`: KeyError 'float4_e2m1fn_x2' — MXFP4 not supported in this API
- `mla_decode_fwd` with MXFP4 KV cache: "only support head_size == KV.size(3) for now"
- `get_torch_quant` as drop-in for `get_triton_quant`: produces wrong GEMM results
- `fmoe_g1u1` for 32-expert shapes: produces NaN
- `torch.compile` on ROCm 7.1: blocked by `auto_functionalized_v2`
- Custom HIP compilation: blocked by runner source scanning
- A-quantization caching across iterations: only helps benchmark mode, NOT ranked scoring
- `fast_mode=True` for MLA metadata: SLOWER on MI355X (verified Phase 17)
- Origami XCD remapping for non-divisible tiles: creates non-bijective mapping (silent wrong results)

## Leaderboard Gaps (Updated)

| Kernel | Our Best | Leader | Gap | Path Forward |
|--------|----------|--------|-----|--------------|
| MoE | ~155µs | 145µs | 1.07x | fused_moe tuning, direct CK dispatch |
| GEMM | ~33µs | ~23µs | 1.45x | Fused quant+GEMM (requires custom Triton) |
| MLA | ~67.8µs | 4.3µs | 15.8x | Single fused CK/ASM kernel (moonshot) |

## Exploration Priorities

1. Any strategy that fuses quantization into the GEMM kernel
2. MoE: direct `ck_moe_stage1`/`ck_moe_stage2` calling conventions
3. GEMM: Triton `tl.dot_scaled` with correct scale layout [BLOCK_N, SCALE_PER_K]
4. MLA: FlashAttention-style fused tiling (eliminates 3-stage pipeline overhead)
