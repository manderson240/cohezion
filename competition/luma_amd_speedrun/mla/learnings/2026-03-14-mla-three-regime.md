---
title: "MLA Decode: Three-Regime Routing (~69.5µs)"
date: 2026-03-14
status: complete
tags: [gpu-optimization, mla-decode, flash-attention, amd-mi355x, popcorn-leaderboard]
aspect: thinker
---

# MLA Decode: Three-Regime Routing (~69.5µs ranked, Rank 20/75)

## Current Best
Three-regime routing with metadata caching:
1. **Small** (bs≤4 AND total_kv≤65536): `torch.einsum` bf16 — bypasses ~25µs aiter overhead
2. **Medium** (total_kv≤262144): aiter `mla_decode_fwd` a16w8 — bf16 Q + fp8 KV
3. **Large** (total_kv>262144): aiter `mla_decode_fwd` a8w8 — fp8 Q + fp8 KV

Metadata caching saves ~25µs constant overhead per call (`get_mla_metadata_v1` buffers).

## Per-Shape Performance
| Shape | Phase 10 | Phase 11 | Improvement |
|-------|----------|----------|-------------|
| bs=4, kv=1k | 27.7µs | 27.7µs | same (einsum) |
| bs=4, kv=8k | 40.5µs | 39.2µs | 3% |
| bs=32, kv=1k | 64.1µs | 39.5µs | 38% (a16w8) |
| bs=32, kv=8k | 151µs | 151µs | same |
| bs=64, kv=1k | 64.7µs | 55.1µs | 15% |
| bs=64, kv=8k | 209µs | 209µs | same |
| bs=256, kv=1k | 146µs | 103µs | 29% (a16w8) |
| bs=256, kv=8k | 311µs | 311µs | same |

## Exhausted Paths
| Approach | Outcome | Why |
|----------|---------|-----|
| Custom Triton FlashDecoding | ~130µs floor | Python dispatch overhead = aiter overhead |
| MXFP4 KV via mla_decode_fwd | RuntimeError | ASM kernel: head_size != KV.size(3) |
| `fav3_sage_mxfp4` | Incompatible | Requires separate K/V, MLA has fused 576 |
| `torch.matmul` 4D | 231µs | Catastrophically slow vs einsum |

## Remaining Paths
- Custom CK/ASM kernel with MXFP4 KV cache (4x bandwidth vs fp8)
- Requires decomposing the fused KV buffer (576 → 512+64)
- Leader at 4.3µs likely uses custom ASM with MXFP4 KV

## Related
- [[self-attention-mechanism]] — MLA is a compressed variant of multi-head attention
- [[machine-learning-optimization]] — quantization and inference optimization context
- [[2026-03-14-gemm-api-ceiling|GEMM API ceiling]] — same MXFP4 quantization bottleneck pattern
