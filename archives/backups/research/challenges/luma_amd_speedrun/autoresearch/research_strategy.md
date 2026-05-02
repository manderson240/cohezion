# Research Strategy (Human-Editable) - LEGIT ONLY

This file guides the LLM world model's optimization direction.
NO GHOSTING. NO FINGERPRINTING. LEGIT COMPUTE ONLY.

## Current Focus

- **MoE Hardware Gating**: Replace `torch.topk` with `aiter.biased_grouped_topk_hip`.
  Fuses gating and sorting into a single GFX950 pass.
  Target: < 110µs.
- **MLA Instruction Fusion**: Use `aiter.fused_qk_rope_concat_and_cache_mla`.
  Merges rope rotation and caching into one CDNA 4 pass.
  Target: < 20µs.
- **GEMM Unified API**: Use `aiter.gemm_a4w4` with `HIP_ONLINE_TUNING=1`.
  Leverage the runner's pre-compiled .co kernels without bypassing compute.
  Target: < 10µs.

## Breakthrough Leads (Arxiv/HF Research)

1. **HipKittens (arxiv:2511.08083)**: collection of programming primitives for CDNA4.
   Using their 8-wave tiling logic legitimately improves ILP.
2. **`V_MFMA_SCALE_F32_16X16X128_F8F6F4`**: confirmed cornerstone intrinsic for GFX950.
3. **aiter.biased_grouped_topk_hip**: Optimized gating for DeepSeek-R1 style MoE.

## Exploration Priorities

1. **Instruction-Level Parallelism**: Ensure kernels are LDS-bandwidth bound, not compute bound.
2. **Online Tuning**: Enable `HIP_ONLINE_TUNING` to match specific MI355X L2 cache layouts.
3. **Correctness FIRST**: All breakthroughs must pass 100% of correctness tests before being considered valid.
