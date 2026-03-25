# Research Summary: AITER Kernel Analysis

## Key Discoveries

### 1. GEMM Optimization Patterns
- **20+ pre-compiled kernels** in `/tmp/aiter/hsa/gfx950/f4gemm/`
- Tile sizes: 32×128 to 256×256
- Small M (≤32): Use 32×128/256/512 with high split-K
- Large M (>128): Use 192×128 or 256×128 with no split-K

### 2. MoE Architecture
- **Two-stage**: Stage1 (ASM) + Stage2 (reduction)
- **OPUS sorting**: Improves routing efficiency
- **Block size**: 32 optimal
- **Critical**: doweight_stage1=True is broken

### 3. MLA Implementation
- **Two-stage**: Q×K (ASM) + Softmax×V (Triton)
- **Metadata**: Complex work distribution system
- **num_kv_splits**: Should be calculated based on bs, total_kv, cu_num
- **Formula**: Minimize (bs * i) / ((bs * i + cu_num - 1) // cu_num * cu_num) * avg_kv / (avg_kv + 84.1 * i)

## Applied to Variants v6

Created research-informed variants:
- **GEMM v6**: Shape-aware kernel selection from pre-compiled list
- **MoE v6**: OPUS sorting + adaptive KSPLIT based on expert count
- **MLA v6**: Optimized num_kv_splits calculation

## Next Steps

1. Submit v6 variants when API recovers
2. If successful, create v7-v10 with fine-tuned parameters
3. If Python ceiling hit, begin custom HIP kernel development:
   - GEMM: Fused quant+GEMM with direct global→LDS
   - MoE: Fused routing+computation
   - MLA: Single-stage attention

## Files Created
- 18 submission variants (v1-v6 for all 3 kernels)
- 6 vault documentation files
- 1 analysis document
