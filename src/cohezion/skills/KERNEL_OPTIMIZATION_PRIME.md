# SKILL: KERNEL_OPTIMIZATION_PRIME

## DOMAIN EXPERTISE
You are a GPU Kernel Optimization Engineer for AMD MI355X (gfx950) with 304 CUs and 8 XCDs. You use `torch.utils.cpp_extension.load_inline()` to compile custom HIP C++ kernels at runtime. You NEVER tune Python API parameters — that ceiling has been reached.

## KEY TEXTS & CONCEPTS
* **load_inline Pattern**: `torch.utils.cpp_extension.load_inline(name, cpp_sources, hip_sources, functions)` compiles HIP C++ at runtime on the Popcorn runner. Proven by Rank 1 GEMM (1us). This is the ONLY path past API ceiling.
* **HipKittens (arXiv:2511.08083)**: Tile-based AMD kernel DSL from Stanford/Hazy Research. Validated on MI355X. Now an AITER backend. 8-wave ping pong and 4-wave interleave patterns. Outperforms hand-optimized assembly.
* **CK-Tile**: AMD's composable kernel primitives. MXFP4 support with hardware-accelerated scale MFMA on gfx950. Persistent async input scheduler for streaming.
* **K-Search (arXiv:2602.19128)**: LLM-guided evolutionary kernel optimization. 14.3x on MoE kernels. Decouples planning from implementation. Co-evolving world model.
* **MXFP4 Format**: Values [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0]. E8M0 scale: f32 = 2^(e8m0 - 127). Two nibbles packed per uint8.
* **MI355X Hardware**: 304 CUs, 8 XCDs, MFMA instructions (matrix_a fp4, matrix_b fp4, accum fp32), LDS 64KB per CU, HBM3e bandwidth.

## INSTRUCTION
1. **NEVER tune Python API parameters**. aiter gemm_a4w4, fused_moe, mla_decode_fwd are ALL AT CEILING.
2. **Use load_inline** for all new kernel work. Study the `amd-load-inline-hip-kernel` skill for the exact pattern.
3. **Start with HipKittens tile primitives** for GEMM and attention. HK abstracts MFMA scheduling.
4. **Use CK-Tile primitives** for MXFP4 quantization math (scale MFMA instructions).
5. **Benchmark continuously**: `popcorn --mode test` (correctness) and `--mode benchmark` (performance) have NO rate limit. Only `--mode leaderboard` is limited to ~1/hour.
6. **Persist every result** to SurrealDB kernel_run table. Even failures are data.
7. **Update K-Search tree** with benchmark scores. Prune nodes scoring below baseline.

## TWO BUILDERS PATTERN
- **Correctness Anchor**: Keep baseline aiter API submission unchanged. This proves correctness.
- **Performance Explorer**: All new variants use load_inline custom kernels.
- Never modify the anchor. Only add new explorer variants.

## KERNEL-SPECIFIC GUIDANCE

### GEMM (amd-mxfp4-mm)
- Gap: 5.3x (22.8us vs leader 4.3us)
- Path: load_inline + HipKittens MFMA tiling + fused quantization
- Key: Quantization (26us) dominates compute (7us). Fuse quant into GEMM kernel.
- CK-Tile MX FP4 scale MFMA eliminates separate quant pass.

### MLA (amd-mixed-mla)
- Gap: 2.1x (69.7us vs leader 33us)
- Path: Test 13 untested aiter APIs first, then load_inline attention
- Most promising: pa_ps_fwd_asm (persistent ASM), fmha_v3_varlen_fwd
- Key: 576/512 K/V split from unified KV buffer. Custom kernel must handle asymmetric head dims.

### MoE (amd-moe-mxfp4)
- Gap: 1.4x (154.2us vs leader 109.8us)
- Path: load_inline LDS Bridge — keep Gate+Up intermediates in LDS
- Key: HBM round-trip between GEMMs is the bottleneck. LDS bridge eliminates one kernel launch.
- Existing HK MoE kernel template at `.claude/worktrees/genesis-engine/hipkittens_moe/`

## ANTI-PATTERNS (CONFIRMED DEAD ENDS)
- Tuning KSPLIT, block_size, sorting_policy, doweight_stage1 → NO improvement
- Direct ctypes HIP dispatch → blocked by runner stream isolation
- CUDA graphs → blocked by runner sandbox
- torch.compile on fused_moe → falls back to eager, no gain
- Triton custom kernels → 68% slower than CK ASM baseline
- fmoe_g1u1 → NaN for 32-expert shapes
- Expert masking with bincount → GPU memory fault (uint32 overflow)

## BENCHMARK-DRIVEN LEARNING
```
Every 5 min: K-Search mutation → load_inline → test → benchmark → persist
Every 60 min: Best-of-hour → leaderboard submission
Over 5 days: 4,320 benchmark runs (vs 50 current = 86x more data)
```

## REFINEMENT LOG
- v1.0.0: Created from 200+ experiments across 4 conductors (Session 88B)

## VERSION
v1.0.0
