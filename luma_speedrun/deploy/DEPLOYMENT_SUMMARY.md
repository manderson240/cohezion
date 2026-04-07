# DEPLOYMENT PACKAGE - FINAL SUMMARY

**Generated:** April 6, 2026  
**Location:** `luma_speedrun/deploy/`  
**Status:** READY FOR DEPLOYMENT

---

## DEPLOYMENT PACKAGE STATISTICS

| Tier | Kernels | READMEs | Total Files | Purpose |
|------|---------|---------|-------------|---------|
| **Tier 1** | 3 | 3 | 6 | Breakthrough candidates (high risk/high reward) |
| **Tier 2** | 7 | 7 | 14 | Best variants (highest probability wins) |
| **Tier 3** | 16 | 0 | 16 | Experimental (if Tier 1/2 exhausted) |
| **Total** | **26** | **10** | **36** | **Complete deployment package** |

---

## TIER 1: BREAKTHROUGH CANDIDATES (3 Kernels)

| File | Size | Strategy | Target | Risk |
|------|------|----------|--------|------|
| `gemm_breakthrough.py` | 5.2 KB | Fused prologue quant | 10 µs | HIGH |
| `moe_breakthrough.py` | 4.0 KB | Fused MoE via load_inline | 120 µs | HIGH |
| `mla_breakthrough.py` | 3.5 KB | Flash Attention approach | 50 µs | HIGH |

**Why Deploy First:**
- Highest potential payoff (10-50% improvements possible)
- Fresh JIT caches = best chance for custom kernels
- May reveal runner policy changes (load_inline availability)

---

## TIER 2: BEST VARIANTS (7 Kernels)

### MoE Kernels (3)

| File | Size | Strategy | Expected | Risk |
|------|------|----------|----------|------|
| `moe_dispatch_policy.py` | 1.4 KB | dispatch_policy=1 | 436 µs worst | LOW |
| `moe_dispatch1_mask.py` | 1.8 KB | Expert masking | 140-150 µs | MEDIUM |
| `moe_baseline.py` | 2.1 KB | Standard fused_moe | 154 µs | LOW |

### MLA Kernels (4)

| File | Size | Strategy | Expected | Risk |
|------|------|----------|----------|------|
| `mla_best_final.py` | 22.9 KB | Three-regime hybrid | <50 µs | LOW-MED |
| `mla_fastmode.py` | 6.1 KB | fast_mode=False | 67.8 µs | LOW |
| `mla_baseline.py` | 15.0 KB | Standard mla_decode_fwd | 69.7 µs | LOW |

### GEMM Kernels (1)

| File | Size | Strategy | Expected | Risk |
|------|------|----------|----------|------|
| `gemm_baseline.py` | 6.6 KB | MFMA FP4 exact layouts | 13.4 µs | LOW |

---

## TIER 3: EXPERIMENTAL (16 Kernels)

### GEMM (5)
- `gemm_loadinline.py` (10.7 KB) - Custom HIP kernel
- `gemm_fp4mfma_v6.py` (6.3 KB) - FP4 native MFMA
- `gemm_mfma_128x128.py` (15.1 KB) - Large tile MFMA
- `gemm_asm_wide_tiles.py` (5.5 KB) - ASM wide tiles
- `gemm_amd_blog_v3.py` (17.3 KB) - AMD blog optimizations

### MLA (5)
- `mla_loadinline.py` (9.6 KB) - Custom MLA kernel
- `mla_direct_ck.py` (17.2 KB) - Direct CK dispatch
- `mla_cudagraph.py` (10.7 KB) - CUDA Graph capture
- `mla_asm_only.py` (5.0 KB) - ASM-only path
- `mla_hybrid_bs4.py` (6.4 KB) - BS4 optimization

### MoE (6)
- `moe_cktile_v2.py` (20.8 KB) - CK-Tile MoE v2
- `moe_blockscale_v3.py` (8.0 KB) - Blockscale quantization
- `moe_sortmask.py` (3.9 KB) - Custom sorting
- `moe_blockm_tuned.py` (2.3 KB) - Block M tuning
- `moe_fmoe_g1u1.py` (1.8 KB) - fmoe variant
- `moe_expert_mask.py` (2.6 KB) - Expert masking

---

## DEPLOYMENT INSTRUCTIONS

### Quick Start
```bash
cd luma_speedrun/deploy
./deploy_all.sh
```

### Deploy by Tier

**Tier 1 (Test First):**
```bash
popcorn run tier1_breakthrough/moe_breakthrough.py --mode test --leaderboard amd-moe-mxfp4
popcorn run tier1_breakthrough/mla_breakthrough.py --mode test --leaderboard amd-mla-decode
popcorn run tier1_breakthrough/gemm_breakthrough.py --mode test --leaderboard amd-mxfp4-mm
```

**Tier 2 (Submit Best):**
```bash
popcorn run tier2_best/moe_dispatch_policy.py --mode leaderboard --leaderboard amd-moe-mxfp4
popcorn run tier2_best/mla_best_final.py --mode leaderboard --leaderboard amd-mla-decode
popcorn run tier2_best/gemm_baseline.py --mode leaderboard --leaderboard amd-mxfp4-mm
```

---

## EXPECTED PERFORMANCE

| Kernel | Baseline | Leader | Gap | Tier 1 Target | Tier 2 Target |
|--------|----------|--------|-----|---------------|---------------|
| **MoE** | 154 µs | 109 µs | 1.4x | 120 µs | 140 µs |
| **MLA** | 69.7 µs | 33 µs | 2.1x | 50 µs | 65 µs |
| **GEMM** | 13.4 µs | 4.3 µs | 3.1x | 10 µs | 13 µs |

---

## DOCUMENTATION INCLUDED

### Main Documentation
- `README.md` - Master deployment guide
- `deploy_all.sh` - Automated test script
- `results.log` - Results tracking template

### Kernel Documentation (10 READMEs)

**Tier 1:**
- README_moe_breakthrough.md
- README_mla_breakthrough.md
- README_gemm_breakthrough.md

**Tier 2:**
- README_moe_dispatch_policy.md
- README_moe_dispatch1_mask.md
- README_moe_baseline.md
- README_mla_best_final.md
- README_mla_fastmode.md
- README_mla_baseline.md
- README_gemm_baseline.md

---

## SUCCESS CRITERIA

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

## FILE INVENTORY

```
luma_speedrun/deploy/
├── README.md                          [6.5 KB]  Master deployment guide
├── deploy_all.sh                      [4.1 KB]  Automated test script
├── results.log                        [3.5 KB]  Results template
├── DEPLOYMENT_SUMMARY.md              [This file]
│
├── tier1_breakthrough/
│   ├── gemm_breakthrough.py           [5.2 KB]  Fused prologue quant
│   ├── moe_breakthrough.py            [4.0 KB]  Fused MoE via load_inline
│   ├── mla_breakthrough.py            [3.5 KB]  Flash Attention approach
│   ├── README_gemm_breakthrough.md    [1.3 KB]  Strategy doc
│   ├── README_moe_breakthrough.md     [1.4 KB]  Strategy doc
│   └── README_mla_breakthrough.md     [1.4 KB]  Strategy doc
│
├── tier2_best/
│   ├── gemm_baseline.py               [6.6 KB]  MFMA FP4 exact layouts
│   ├── moe_baseline.py                [2.1 KB]  Standard fused_moe
│   ├── moe_dispatch_policy.py         [1.4 KB]  dispatch_policy=1
│   ├── moe_dispatch1_mask.py          [1.8 KB]  Expert masking
│   ├── mla_baseline.py                [15.0 KB] Standard mla_decode_fwd
│   ├── mla_fastmode.py                [6.1 KB]  fast_mode=False
│   ├── mla_best_final.py              [22.9 KB] Three-regime hybrid
│   ├── README_gemm_baseline.md        [1.0 KB]  Strategy doc
│   ├── README_moe_baseline.md         [1.0 KB]  Strategy doc
│   ├── README_moe_dispatch_policy.md   [1.4 KB]  Strategy doc
│   ├── README_moe_dispatch1_mask.md  [1.2 KB]  Strategy doc
│   ├── README_mla_baseline.md         [0.9 KB]  Strategy doc
│   ├── README_mla_fastmode.md         [1.1 KB]  Strategy doc
│   └── README_mla_best_final.md      [1.4 KB]  Strategy doc
│
└── tier3_experimental/
    ├── gemm_amd_blog_v3.py            [17.3 KB] AMD blog optimizations
    ├── gemm_asm_wide_tiles.py         [5.5 KB]  ASM wide tiles
    ├── gemm_fp4mfma_v6.py             [6.3 KB]  FP4 native MFMA
    ├── gemm_loadinline.py             [10.7 KB] Custom HIP kernel
    ├── gemm_mfma_128x128.py           [15.1 KB] Large tile MFMA
    ├── mla_asm_only.py                [5.0 KB]  ASM-only path
    ├── mla_cudagraph.py               [10.7 KB] CUDA Graph capture
    ├── mla_direct_ck.py               [17.2 KB] Direct CK dispatch
    ├── mla_hybrid_bs4.py              [6.4 KB]  BS4 optimization
    ├── mla_loadinline.py              [9.6 KB]  Custom MLA kernel
    ├── moe_blockm_tuned.py            [2.3 KB]  Block M tuning
    ├── moe_blockscale_v3.py           [8.0 KB]  Blockscale quantization
    ├── moe_cktile_v2.py               [20.8 KB] CK-Tile MoE v2
    ├── moe_expert_mask.py             [2.6 KB]  Expert masking
    ├── moe_fmoe_g1u1.py               [1.8 KB]  fmoe variant
    └── moe_sortmask.py                [3.9 KB]  Custom sorting
```

---

## TOTAL PACKAGE SIZE

- **Python Kernels:** 26 files
- **Documentation:** 10 READMEs
- **Scripts:** 1 deployment script
- **Templates:** 1 results log
- **Total Files:** 38 files
- **Total Size:** ~320 KB

---

## DEPLOYMENT READY

✅ **3** Tier 1 breakthrough candidates organized  
✅ **7** Tier 2 best variants organized  
✅ **16** Tier 3 experimental kernels organized  
✅ **10** README files with strategy and test commands  
✅ **1** Master deployment script (deploy_all.sh)  
✅ **1** Results tracking template (results.log)  
✅ **1** Master deployment guide (README.md)  

---

**STATUS: 26 KERNELS ORGANIZED AND READY FOR DEPLOYMENT**

**NEXT ACTION:** Run `./deploy_all.sh` to begin testing
