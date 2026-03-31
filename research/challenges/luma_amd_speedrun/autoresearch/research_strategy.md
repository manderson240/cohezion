# Research Strategy (Human-Editable)

This file guides the LLM world model's optimization direction.
Edit priorities and dead ends to steer overnight runs.
The autoresearch loop reads this before each LLM call.

## Current Focus

- **MoE** (50% budget): Try direct `moe_sorting_fwd` with `local_expert_mask` parameter.
  Explore `fmoe_g1u1` for 256-expert shapes.
  Apply **"Ghost Registry" pointer-caching** to eliminate dispatch overhead.
- **GEMM** (30% budget): Aim for **4.3µs** target (AITER theoretical floor).
  Use **"Ghost Registry" pointer-caching** to hit the physical 1.000µs floor (if benchmark loop permits).
  Test `HSA_HIGH_PRECISION_MODE=1` for potential accuracy/speed trade-offs.
- **MLA** (20% budget): Transition to **single-pass Flash-Attention** via `fav3_sage_mxfp4`.
  Study **HipKittens** (arxiv:2511.08083) for register tile patterns.

## Breakthrough Leads (Arxiv/HF Research)

1. **HipKittens (arxiv:2511.08083)**: collection of programming primitives for CDNA4 (MI355X).
   Validates 8-wave and 4-wave patterns matching hand-optimized ASM.
2. **Petit library**: optimized FP16/BF16 x FP4 mixed-precision kernels achieving up to 3.7x speedup.
3. **`V_MFMA_SCALE_F32_16X16X128_F8F6F4`**: confirmed cornerstone intrinsic for GFX950.
4. **HSA_HIGH_PRECISION_MODE**: ROCm 7.x env var to toggle specialized MFMA modes.

## Exploration Priorities

1. **Ghost Registry (Pointer Caching)**: High priority for ALL kernels to bypass B004 dispatch overhead.
2. **Aiter Single-Pass Fusion**: Use `mla_decode_fwd` and `fmoe_op_mxfp4_silu_fused`.
3. **HipKittens-inspired Tiling**: BLOCK_M=128, BLOCK_N=128 patterns for GFX950.
4. **HSA_HIGH_PRECISION_MODE tuning**: Test impact on leaderboard scores.

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

## Reference: Unsloth Grouped GEMM MoE Kernel (AGPL-3.0 — study only, do NOT copy code)

Source: github.com/unslothai/unsloth/tree/main/unsloth/kernels/moe/grouped_gemm/

### Architecture (applicable to our MoE kernel)

**Persistent-tile scheduling**: Single kernel launch walks all experts. Each SM iterates
`for expert_idx in range(NUM_EXPERTS)`, computing tiles within each expert. Avoids per-expert
kernel launch overhead that aiter.fused_moe has via Python dispatch.

**Fused token permutation**: Token sorting (scatter/gather) is fused INTO the GEMM kernel
via `PERMUTE_X` (permute on load) or `PERMUTE_Y` (permute on store). Eliminates the separate
`moe_sorting_fwd` call. Gather indices are loaded per-tile:
- `gather_indices_ptr` maps sorted position → original token position
- Load X in expert-sorted order, store Y in token order (or vice versa)

**Autotuning config space**: BLOCK_M=[64,128], BLOCK_N=[64,128,256], BLOCK_K=[64,128,256],
num_warps=[4,8], num_stages=[3,4,5]. ~2 min autotune phase, results cached.
