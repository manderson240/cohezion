# SKILL: AMD_MLA_DECODE_PRIME

## DOMAIN EXPERTISE
DeepSeek MLA (Multi-head Latent Attention) decode optimization for AMD MI355X. Target: <50us from 69.7us.

## KEY FACTS
* Current best: 69.7us. Leader: 33us. Gap: 2.1x.
* Python dispatch floor: ~20-25us per torch op. Leader uses single fused CK/ASM kernel.
* K=576, V=512 latent split from unified KV buffer (unique to DeepSeek R1 MLA).
* 13 untested attention APIs in aiter (pa_ps_fwd_asm most promising).
* 3-regime routing: matmul (small) + aiter a16w8 (medium) + aiter a8w8 (large).
* fast_mode=False is FASTER on MI355X (verified).

## INSTRUCTION
1. FIRST: Systematically test 13 untested APIs before writing custom kernels:
   - pa_ps_fwd_asm (persistent ASM attention)
   - fmha_v3_varlen_fwd (FlashMHA v3)
   - flash_attn_varlen_func with padded V
2. If untested API works: optimize parameters and submit
3. If not: create load_inline attention kernel with:
   - HipKittens attention tile primitives (500 LOC, outperforms AITER ASM)
   - 576/512 K/V split: load 576 dims for QK dot product, 512 dims for V accumulation
   - Persistent shared memory for KV cache pre-loading

## DEAD ENDS
- mla_decode_fwd parameter tuning (num_kv_splits, fast_mode) — EXHAUSTED
- A16W8 threshold tuning — 262144 is optimal
- MXFP4 KV cache — "only support head_size == KV.size(3)"
- ctypes/CUDA graphs — blocked by runner

## VERSION
v1.0.0
