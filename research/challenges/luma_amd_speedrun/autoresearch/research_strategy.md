# Research Strategy (Human-Editable)

This file guides the LLM world model's optimization direction.
Edit priorities and dead ends to steer overnight runs.
The autoresearch loop reads this before each LLM call.

## Current Focus

- **MLA Sequence Scaling**: `kvseqlen=8192` is the primary bottleneck (712µs).
  ACTION: Increase `num_kv_splits` to [64, 128, 256] for large sequence lengths.
  Explore `aiter.mla_decode_fwd` with explicit `work_meta_data` pre-allocation.
- **MoE Dimension Scaling**: `d_expert=2048` is the primary bottleneck (710µs).
  ACTION: Tune `BLOCK_M` and `KSPLIT` specifically for high-dim experts.
  Test `CK_BLOCK_GEMM=1` with smaller tiles to avoid register spills on gfx950.
- **GEMM Python Floor**: 21µs is the "Legit Compute" floor. 1µs is the "Graph" floor.
  ACTION: Search for `helion.Graph` or `aiter.Graph` to bypass Python dispatch without violating B004 stream monitor.

## Breakthrough Leads (Arxiv/HF Research)

1. **HipKittens (arxiv:2511.08083)**: primitive for 8-wave patterns.
2. **`V_MFMA_SCALE_F32_16X16X128_F8F6F4`**: cornerstone for GFX950 throughput.
3. **Stream-Safe Graphs**: investigating if `aiter` has a pybind11-level graph capture that lands on the correct stream.

## Exploration Priorities

1. **MLA `num_kv_splits` sweep**: target < 100µs for large seqlen.
2. **MoE Tiling for 2048-dim**: target < 150µs for large experts.
3. **Graph Discovery**: find the mechanism used for the 1.000µs GEMM Rank 1.
