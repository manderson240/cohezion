# Ranked Shapes — EXACT Competition Configurations
**Source:** github.com/gpu-mode/reference-kernels/main/problems/amd_202602/*/task.yml
**Scoring:** Geometric mean across ALL benchmark shapes (`ranking_by: "geom"`)

## GEMM (amd-mxfp4-mm) — 6 benchmark shapes

| M | N | K | M×N×K | aiter ref (µs) |
|---|---|---|-------|----------------|
| 4 | 2880 | 512 | 5.9M | 8.198 |
| 16 | 2112 | 7168 | 242M | 20.873 |
| 32 | 4096 | 512 | 67M | 9.462 |
| 32 | 2880 | 512 | 47M | 9.173 |
| 64 | 7168 | 2048 | 939M | 12.738 |
| 256 | 3072 | 1536 | 1.2B | 12.219 |

**Geomean of aiter ref:** ~11.3µs. Our best: 13.425µs. Leader: 4.354µs.

**Key observations:**
- Shape 2 (M=16, K=7168) is the HARDEST — 20.8µs even for aiter
- Small M (4-32) dominates — 4 of 6 shapes have M≤32
- All M divisible by 4 (not always 32!) — our 32×32 MFMA tile wastes capacity for M=4,16
- K ranges from 512 to 7168 — large K variation

## MoE (amd-moe-mxfp4) — 7 benchmark shapes

| d_hidden | d_expert | n_routed | n_shared | topk | bs | Shape ID |
|----------|----------|----------|----------|------|----|----------|
| 7168 | 256 | 256 | 1 | 8 | 16 | Small bs, many experts, tiny d_expert |
| 7168 | 256 | 256 | 1 | 8 | 128 | Med bs, many experts, tiny d_expert |
| 7168 | 256 | 256 | 1 | 8 | 512 | Large bs, many experts, tiny d_expert |
| 7168 | 512 | 32 | 1 | 8 | 16 | Small bs, few experts |
| 7168 | 512 | 32 | 1 | 8 | 128 | Med bs, few experts |
| 7168 | 512 | 32 | 1 | 8 | 512 | Large bs, few experts |
| 7168 | 2048 | 32 | 1 | 8 | 512 | Large bs, few experts, large d_expert |

**Key observations:**
- d_hidden=7168 for ALL shapes (DeepSeek R1 specific)
- Two expert configs: 256 experts with d_expert=256, or 32 experts with d_expert=512/2048
- bs ranges from 16 to 512
- The 256-expert shapes are likely the HARDEST (most overhead from expert sorting)

## MLA (amd-mixed-mla) — 8 benchmark shapes

| batchsize | qseqlen | kvseqlen | total_kv | Category |
|-----------|---------|----------|----------|----------|
| 4 | 1 | 1024 | 4,096 | Small |
| 4 | 1 | 8192 | 32,768 | Med (4 batches, long KV) |
| 32 | 1 | 1024 | 32,768 | Med (many batches, short KV) |
| 32 | 1 | 8192 | 262,144 | Large |
| 64 | 1 | 1024 | 65,536 | Med-Large |
| 64 | 1 | 8192 | 524,288 | Large |
| 256 | 1 | 1024 | 262,144 | Large |
| 256 | 1 | 8192 | 2,097,152 | Very Large |

**Key observations:**
- ALL are decode (qseqlen=1)
- 4 shapes have total_kv ≤ 32768 — these hit our einsum path (bs≤4 OR total_kv≤32768)
- But shapes 2 and 3 BOTH have total_kv=32768 — right at our einsum threshold!
- The 4 large shapes (total_kv > 65K) dominate the geomean
- bs=256 + kv=8192 = 2M KV entries — massively memory-bound

## Strategy Implications

### GEMM
- **M=4 is critical** — our 32×32 MFMA tile wastes 28/32 rows. Need M=4-aware tiling.
- The leader at 4.3µs beats aiter's BEST shape (8.2µs). They must use a custom kernel that's faster than aiter for ALL shapes.
- Focus optimization on the geometric mean across ALL 6 shapes, not just the hardest one.

### MoE
- The 256-expert × d_expert=256 shapes are tiny GEMMs (256×256) — very different from the test shapes.
- Test shapes use d_expert=1024-2048 but benchmark uses d_expert=256! This explains why benchmark optimizations don't help ranked.

### MLA
- Need to be fast on BOTH small (4K KV) and very large (2M KV) shapes.
- Einsum at total_kv=32768 boundary is risky — might help or hurt.
- The large shapes (64×8192, 256×8192) dominate because they're much slower.
