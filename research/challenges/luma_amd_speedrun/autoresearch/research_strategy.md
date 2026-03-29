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
2. **MoE: Custom Triton with fused permutation (Unsloth-inspired)** — see below
3. MoE: direct `ck_moe_stage1`/`ck_moe_stage2` calling conventions
4. GEMM: Triton `tl.dot_scaled` with correct scale layout [BLOCK_N, SCALE_PER_K]
5. MLA: FlashAttention-style fused tiling (eliminates 3-stage pipeline overhead)

## Reference: Unsloth Grouped GEMM MoE Kernel (AGPL-3.0 — study only, do NOT copy code)

Source: github.com/unslothai/unsloth/tree/main/unsloth/kernels/moe/grouped_gemm/

### Architecture (applicable to our MoE kernel)

**Persistent-tile scheduling**: Single kernel launch walks all experts. Each SM iterates
`for expert_idx in range(NUM_EXPERTS)`, computing tiles within each expert. Avoids per-expert
kernel launch overhead that aiter.fused_moe has via Python dispatch.

```
# Pseudocode (NOT Unsloth code — our own interpretation of the pattern)
for expert in range(NUM_EXPERTS):
    m_size = token_counts[expert]        # tokens routed to this expert
    num_tiles = cdiv(m_size, BLOCK_M) * cdiv(N, BLOCK_N)
    while my_tile_id in range(processed, processed + num_tiles):
        # compute GEMM tile for this expert
        processed += num_tiles
```

**Fused token permutation**: Token sorting (scatter/gather) is fused INTO the GEMM kernel
via `PERMUTE_X` (permute on load) or `PERMUTE_Y` (permute on store). Eliminates the separate
`moe_sorting_fwd` call. Gather indices are loaded per-tile:
- `gather_indices_ptr` maps sorted position → original token position
- Load X in expert-sorted order, store Y in token order (or vice versa)

**Autotuning config space**: BLOCK_M=[64,128], BLOCK_N=[64,128,256], BLOCK_K=[64,128,256],
num_warps=[4,8], num_stages=[3,4,5]. ~2 min autotune phase, results cached.

### What We Can Apply on AMD MI355X

| Unsloth Technique | AMD Adaptation | Expected Impact |
|-------------------|----------------|-----------------|
| Persistent tiles | Same pattern in Triton (works on HIP) | Eliminates per-expert dispatch (~5-10µs) |
| Fused permutation | Replace `moe_sorting_fwd` + `fused_moe` with single kernel | Saves one kernel launch + memory round-trip |
| Autotuned tile sizes | Adapt for gfx950 XCD topology (8 compute dies) | May need XCD-aware remapping (see dead ends) |
| `tl.dot_scaled` for MXFP4 | Use instead of `tl.dot` for native FP4 support | Hardware MXFP4 acceleration on MI355X |

### What Does NOT Transfer

- **TMA descriptors**: Hopper-only (SM90+), not on AMD. Use standard `tl.load`/`tl.store`.
- **Split LoRA**: Training optimization, irrelevant for inference kernels.
- **`torch._grouped_mm`**: CUDA-only backend, not available on ROCm.

### Implementation Sketch (for K-Search world model)

A custom Triton MoE kernel for MI355X would:
1. Accept pre-sorted tokens + expert counts (from `moe_sorting_fwd` or custom sort)
2. Use persistent-tile loop over experts (avoid per-expert kernel launch)
3. Use `tl.dot_scaled` for native MXFP4 GEMM (see `amd-gfx950-tl-dot-scaled-constraints`)
4. Fuse the gate weight multiplication into the store phase (`FUSE_MUL_POST`)
5. Handle XCD remapping carefully (see `tritonblas-origami-xcd-remapping-bug` skill)

Risk: Custom Triton MoE was previously 68% slower than CK ASM (dead end). The difference
now is (a) fused permutation was not tried, (b) `tl.dot_scaled` for MXFP4 was not used,
and (c) persistent-tile scheduling was not applied. These three combined may close the gap.
