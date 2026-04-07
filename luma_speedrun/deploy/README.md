# FINAL DEPLOYMENT PACKAGE - Luma AMD Speedrun

**Generated:** April 6, 2026  
**Competition:** Luma AMD Speedrun (April 2026)  
**Hardware:** AMD MI355X (gfx950)

---

## Package Overview

| Tier | Count | Description |
|------|-------|-------------|
| **Tier 1** | 3 | Breakthrough candidates (high risk/high reward) |
| **Tier 2** | 6 | Best known variants (highest probability wins) |
| **Tier 3** | 16+ | Experimental approaches (if Tier 1/2 exhausted) |
| **Total** | **25+** | Kernels ready for deployment |

---

## Directory Structure

```
deploy/
├── README.md                    # This file
├── deploy_all.sh               # Master deployment script
├── results.log                 # Results template
│
├── tier1_breakthrough/          # 3 candidates
│   ├── gemm_breakthrough.py    # Fused prologue quant
│   ├── moe_breakthrough.py     # Fused MoE via load_inline
│   ├── mla_breakthrough.py     # Flash Attention approach
│   └── README_*.md             # Strategy docs
│
├── tier2_best/                  # 6 variants
│   ├── gemm_baseline.py        # Proven aiter gemm_a4w4
│   ├── moe_baseline.py         # Standard fused_moe
│   ├── moe_dispatch_policy.py  # dispatch_policy=1
│   ├── moe_dispatch1_mask.py   # Expert masking
│   ├── mla_baseline.py         # Standard mla_decode_fwd
│   ├── mla_fastmode.py         # fast_mode=False
│   ├── mla_best_final.py       # Three-regime hybrid
│   └── README_*.md             # Strategy docs
│
└── tier3_experimental/          # 16+ experiments
    ├── gemm_loadinline.py      # Custom HIP GEMM
    ├── gemm_fp4mfma_v6.py      # FP4 native MFMA
    ├── gemm_mfma_128x128.py    # Large tile MFMA
    ├── gemm_asm_wide_tiles.py  # ASM wide tiles
    ├── gemm_amd_blog_v3.py     # AMD blog optimizations
    ├── mla_loadinline.py       # Custom MLA kernel
    ├── mla_direct_ck.py        # Direct CK dispatch
    ├── mla_cudagraph.py        # CUDA Graph capture
    ├── mla_asm_only.py         # ASM-only path
    ├── mla_hybrid_bs4.py       # BS4 optimization
    ├── moe_cktile_v2.py        # CK-Tile MoE
    ├── moe_blockscale_v3.py    # Blockscale quantization
    ├── moe_sortmask.py         # Custom sorting
    ├── moe_blockm_tuned.py     # Block M tuning
    ├── moe_fmoe_g1u1.py        # fmoe variant
    └── moe_expert_mask.py      # Expert masking
```

---

## Quick Start

### 1. Navigate to Deployment Package
```bash
cd luma_speedrun/deploy
```

### 2. Run All Tests (Recommended First Step)
```bash
./deploy_all.sh
```

### 3. Deploy by Tier

**Tier 1 (Breakthrough First):**
```bash
popcorn run tier1_breakthrough/moe_breakthrough.py --mode test --leaderboard amd-moe-mxfp4
popcorn run tier1_breakthrough/mla_breakthrough.py --mode test --leaderboard amd-mla-decode
popcorn run tier1_breakthrough/gemm_breakthrough.py --mode test --leaderboard amd-mxfp4-mm
```

**Tier 2 (Best Variants):**
```bash
popcorn run tier2_best/moe_dispatch_policy.py --mode leaderboard --leaderboard amd-moe-mxfp4
popcorn run tier2_best/mla_best_final.py --mode leaderboard --leaderboard amd-mla-decode
popcorn run tier2_best/gemm_baseline.py --mode leaderboard --leaderboard amd-mxfp4-mm
```

---

## Deployment Strategy

### Phase 1: Test All Tier 1 (First 2 Hours)
- Deploy breakthrough candidates first
- Fresh JIT caches = best chance for custom kernels
- Document any failures immediately

### Phase 2: Benchmark Successful (Next 2 Hours)
- Run benchmark mode on passing kernels
- Compare to baselines
- Select best performers for leaderboard

### Phase 3: Leaderboard Submit (Final Phase)
- Submit proven improvements
- Record all results in results.log
- Document findings for future sessions

---

## Expected Performance Targets

| Kernel | Current | Leader | Gap | Tier 1 Target | Tier 2 Target |
|--------|---------|--------|-----|---------------|---------------|
| **MoE** | 154 µs | 109 µs | 1.4x | 120 µs | 140 µs |
| **MLA** | 69.7 µs | 33 µs | 2.1x | 50 µs | 65 µs |
| **GEMM** | 13.4 µs | 4.3 µs | 3.1x | 10 µs | 13 µs |

---

## Critical Constraints

### GEMM
- `BLOCK_K >= 128` for Triton FP4 (mandatory)
- Quantization (~26 µs) dominates actual GEMM (~7 µs)
- Only fused quant+GEMM can beat API ceiling

### MoE
- `doweight_stage1=False` required for correctness
- `moe_sorting_dispatch_policy=1` reduces worst-case 37%
- At API ceiling with fused_moe (~155 µs vs leader 145 µs)

### MLA
- `fast_mode=False` is FASTER on MI355X (verified)
- 576/512 latent split requires custom handling
- A16W8 threshold = 262144 tokens

---

## Success Criteria

### Minimum (Must Achieve)
- [ ] At least 1 Tier 1 kernel passes correctness test
- [ ] At least 3 Tier 2 kernels pass correctness test
- [ ] No regressions from previous best

### Target (Aim For)
- [ ] 3+ kernels show improvement in benchmark
- [ ] At least 1 ranked submission with measurable score
- [ ] MoE within 1.2x of leader (<130 µs)

### Stretch (Aspire To)
- [ ] Top 10 ranking on any kernel
- [ ] Breakthrough improvement (>20%)
- [ ] Custom kernel via load_inline successfully ranked

---

## Troubleshooting

### Common Errors

| Error | Cause | Fix |
|-------|-------|-----|
| `KeyError: 'float4_e2m1fn_x2'` | Using aiter MXFP4 API | Use tritonblas or ref_kernel fallback |
| Silent wrong results (80% match) | Triton JIT callsite issue | Match reference.py call pattern exactly |
| `doweight_stage1` NaN | Correctness-breaking flag | Set `doweight_stage1=False` |
| Column 0 correct, col 1+ wrong | MFMA register layout | Use column-major output mapping |
| BLOCK_K < 128 with FP4 | Hardware constraint | Use BLOCK_K >= 128 |
| fast_mode slower | MI355X quirk | Use fast_mode=False |

---

## Files Generated

- `deploy/tier1_breakthrough/` - 3 breakthrough candidates + 3 READMEs
- `deploy/tier2_best/` - 6 best variants + 7 READMEs
- `deploy/tier3_experimental/` - 16+ experimental kernels
- `deploy/README.md` - This documentation
- `deploy/deploy_all.sh` - Master test script
- `deploy/results.log` - Results template

**Total: 25+ kernels organized and ready for deployment**

---

## Next Steps

1. Run `./deploy_all.sh` to test all Tier 1 and Tier 2 kernels
2. Document results in `results.log`
3. Submit passing kernels to leaderboard
4. Iterate on failures using Tier 3 experiments
5. Update this README with final results

**Ready for deployment!**
