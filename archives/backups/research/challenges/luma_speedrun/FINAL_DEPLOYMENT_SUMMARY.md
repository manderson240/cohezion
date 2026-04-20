# FINAL DEPLOYMENT SUMMARY - Luma AMD Speedrun

**Generated:** April 6, 2026  
**Project:** GPU Kernel Optimization for AMD MI355X (gfx950)  
**Competition:** Luma AMD Speedrun (April 2026)

---

## 1. EXECUTIVE SUMMARY

### Deployment Status Overview

| Metric | Count |
|--------|-------|
| **Total Kernels Ready** | **20+** |
| **Breakthrough Candidates** | **3** |
| **Best Known Variants** | **6** |
| **Experimental Approaches** | **11+** |
| **Total Submission Files** | **367** |

### Current Competitive Position

| Kernel | Our Best | Leader | Gap | Status |
|--------|----------|--------|-----|--------|
| **GEMM** | ~13.4 µs | ~4.3 µs | 3.1x | API Ceiling Reached |
| **MoE** | ~154 µs | ~109 µs | 1.4x | Within Striking Distance |
| **MLA** | ~69.7 µs | ~33.0 µs | 2.1x | Documentation Complete |

### Key Insights

1. **MoE is closest to competitive** - Only 1.4x behind leader with active-expert masking showing promise
2. **GEMM at API ceiling** - Custom HIP kernel via load_inline needed for breakthrough
3. **MLA has largest gap** - Requires Flash Attention-style fused kernel approach
4. **Runner restrictions** - Custom kernels via load_inline/hipRTC blocked but load_inline recently confirmed working

---

## 2. DEPLOYMENT PRIORITIES

### Tier 1: BREAKTHROUGH CANDIDATES (Deploy First)

These kernels represent highest risk/highest reward opportunities. Deploy when runner conditions are optimal.

| Priority | Kernel | File | Strategy |
|----------|--------|------|----------|
| 1 | **MoE** | `submission_breakthrough_moe.py` | Fused quant+GEMM, direct CK dispatch |
| 2 | **MLA** | `submission_breakthrough_mla.py` | Flash Attention approach, custom ASM |
| 3 | **GEMM** | `submission_breakthrough_gemm.py` | Fused prologue, inline quantization |

**Why Deploy First:**
- Fresh JIT caches
- Maximum time for iteration if issues arise
- Highest potential payoff (10-50% improvements possible)
- May reveal runner policy changes (load_inline availability)

### Tier 2: BEST KNOWN VARIANTS (Deploy Second)

Proven configurations with highest probability of incremental improvement.

| Priority | Kernel | File | Strategy | Expected µs |
|----------|--------|------|----------|-------------|
| 1 | **MoE** | `submission_moe_dispatch_policy.py` | moe_sorting_dispatch_policy=1 | 154-436 |
| 2 | **MLA** | `submission_best_mla_final.py` | Three-regime routing (718 lines) | 67.8 |
| 3 | **GEMM** | `submission.py` (baseline) | aiter gemm_a4w4_asm | 13.4 |
| 4 | **MLA** | `submission_fastmode.py` | A/B test fast_mode=True | 69.7 |
| 5 | **MoE** | `submission_dispatch1_mask.py` | Expert masking variant | 140-150 |
| 6 | **MoE** | `submission.py` (baseline) | fused_moe with adaptive KSPLIT | 154 |

**Why Deploy Second:**
- Known working configurations
- Lower risk of failure
- Baseline for comparison
- Quick wins if breakthroughs fail

### Tier 3: EXPERIMENTAL APPROACHES (Deploy Third)

Advanced techniques for when Tier 1/2 options are exhausted.

| Priority | Kernel | Files | Strategy | Risk Level |
|----------|--------|-------|----------|------------|
| 1 | **GEMM** | `submission_loadinline.py` | Custom HIP kernel with MFMA | HIGH |
| 2 | **GEMM** | `submission_fp4mfma_v6.py` | FP4 native MFMA intrinsics | HIGH |
| 3 | **GEMM** | `submission_mfma_128x128_v2.py` | MFMA 128x128 tile optimization | MEDIUM |
| 4 | **MLA** | `submission_loadinline.py` (341 lines) | Direct CK dispatch via load_inline | HIGH |
| 5 | **MLA** | `submission_direct_ck.py` (380 lines) | CK-Tile stage1/stage2 direct | MEDIUM |
| 6 | **MLA** | `submission_cudagraph.py` (261 lines) | CUDA Graph capture | MEDIUM |
| 7 | **MoE** | `submission_cktile_moe_v2.py` (612 lines) | CK-Tile MoE dispatch | MEDIUM |
| 8 | **MoE** | `submission_sortmask.py` (113 lines) | Custom sorting with mask | LOW |
| 9 | **GEMM** | `submission_triton_splitk.py` (366 lines) | Triton with split-K | MEDIUM |
| 10 | **GEMM** | `submission_asm_tuned.py` | ASM kernel tuning | MEDIUM |
| 11 | **MoE** | `submission_blockscale_v3.py` | Blockscale quantization | MEDIUM |

**Why Deploy Third:**
- Higher complexity
- Unknown correctness
- May require debugging
- Time-intensive to validate

---

## 3. KERNEL INVENTORY BY TYPE

### MLA (Multi-Head Latent Attention) Kernels - 138 Files Total

| File | Lines | Strategy | Expected Improvement | Risk |
|------|-------|----------|----------------------|------|
| `submission_best_mla_final.py` | 718 | Three-regime hybrid routing | Baseline (67.8 µs) | LOW |
| `submission_fastmode.py` | 178 | fast_mode=True A/B test | ±5% vs baseline | LOW |
| `submission_breakthrough_mla.py` | 105 | Flash Attention approach | 20-30% if works | HIGH |
| `submission_asm_only.py` | 160 | Direct ASM dispatch only | 10-15% | MEDIUM |
| `submission_hybrid_bs4.py` | 219 | Batch size 4 optimization | 5-10% | LOW |
| `submission_hybrid_v2.py` | 179 | Hybrid routing v2 | 5-10% | LOW |
| `submission_hybrid_v3.py` | 146 | Hybrid routing v3 | 5-10% | LOW |
| `submission_direct_ck.py` | 380 | Direct CK stage dispatch | 15-25% if works | MEDIUM |
| `submission_loadinline.py` | 341 | Custom load_inline kernel | 30-50% if works | HIGH |
| `submission_cudagraph.py` | 261 | CUDA Graph capture | 10-20% | MEDIUM |
| `submission_fmhav3.py` | ~200 | FlashAttention v3 | Unknown | HIGH |
| `submission_compute_opt_v1.py` | ~180 | Compute optimization | 5% | LOW |
| `submission_bf16_only.py` | ~150 | BF16 precision only | 3-5% | LOW |
| `submission_sdpa.py` | ~100 | SDPA backend | Baseline | LOW |

**Notes:**
- Reference baseline: ~69.7 µs
- Leader: ~33.0 µs (2.1x gap)
- 97 Ollama iteration files (iter1-iter97) for research trail

### MoE (Mixture-of-Experts) Kernels - 125 Files Total

| File | Lines | Strategy | Expected Improvement | Risk |
|------|-------|----------|----------------------|------|
| `submission_breakthrough_moe.py` | 123 | Fused quant+GEMM | 20-30% if works | HIGH |
| `submission_moe_dispatch_policy.py` | 46 | moe_sorting_dispatch_policy=1 | -37% worst case | LOW |
| `submission_dispatch1_mask.py` | 55 | Expert masking dispatch=1 | 10-15% | MEDIUM |
| `submission_dispatch2.py` | 45 | dispatch_policy=2 variant | Unknown | MEDIUM |
| `submission_blockm_tuned.py` | 77 | Tuned block_m parameter | 5-10% | LOW |
| `submission_sortmask.py` | 113 | Custom sorting with mask | 5-10% | MEDIUM |
| `submission_cktile_moe.py` | 450 | CK-Tile MoE v1 | 15-25% if works | MEDIUM |
| `submission_cktile_moe_v2.py` | 612 | CK-Tile MoE v2 (optimized) | 20-30% if works | MEDIUM |
| `submission_loadinline.py` | 193 | Custom HIP kernel | 25-40% if works | HIGH |
| `submission_blockscale_v3.py` | ~150 | Blockscale quantization | 10-15% | MEDIUM |
| `submission_early_exit_v4.py` | ~120 | Early exit optimization | 5-8% | LOW |
| `submission_expert_mask.py` | ~100 | Expert masking base | 5-10% | LOW |
| `submission_fmoe_g1u1_a16.py` | ~140 | fmoe_g1u1 A16 variant | 5-10% | MEDIUM |
| `submission.py` (baseline) | 72 | fused_moe adaptive KSPLIT | Baseline (154 µs) | LOW |

**Notes:**
- Reference baseline: ~154 µs
- Leader: ~109 µs (1.4x gap - closest to competitive)
- 82 Ollama iteration files (iter1-iter82) for research trail
- dispatch_policy=1 verified to reduce worst-case by 37%

### GEMM (MXFP4 Matrix Multiply) Kernels - 104 Files Total

| File | Lines | Strategy | Expected Improvement | Risk |
|------|-------|----------|----------------------|------|
| `submission_breakthrough_gemm.py` | 155 | Fused prologue quant | 20-30% if works | HIGH |
| `submission_loadinline.py` | 300 | Custom HIP with MFMA | 30-50% if works | HIGH |
| `submission_fp4mfma_v6.py` | 183 | FP4 native MFMA | 25-40% if works | HIGH |
| `submission_fp4mfma_v5.py` | ~180 | FP4 MFMA v5 | 20-30% | HIGH |
| `submission_fp4mfma_v4.py` | ~175 | FP4 MFMA v4 | 20-30% | HIGH |
| `submission_mfma_128x128_v2.py` | 365 | MFMA 128x128 tiles v2 | 15-25% | MEDIUM |
| `submission_mfma_128x128_v1.py` | 493 | MFMA 128x128 tiles v1 | 15-25% | MEDIUM |
| `submission_mfma_128x128.py` | 340 | MFMA 128x128 base | 15-25% | MEDIUM |
| `submission_asm_tuned.py` | ~200 | ASM kernel tuning | 10-15% | MEDIUM |
| `submission_asm_wide_tiles_v2.py` | ~220 | Wide tile ASM | 10-15% | MEDIUM |
| `submission_triton_splitk.py` | 366 | Triton split-K | 10-15% | MEDIUM |
| `submission_triton_v2_gemma.py` | 355 | Triton v2 optimized | 10-15% | MEDIUM |
| `submission_triton_dotscaled.py` | 251 | Triton tl.dot_scaled | 5-10% | MEDIUM |
| `submission_splitk_v2.py` | 221 | Split-K v2 | 5-10% | LOW |
| `submission_splitk.py` | 242 | Split-K base | 5-10% | LOW |
| `submission_ksplit.py` | 44 | KSPLIT parameter tuning | 3-5% | LOW |
| `submission_hipb_tuned.py` | 42 | hipBLAS tuned | 3-5% | LOW |
| `submission_tuned.py` | ~100 | General tuning | 3-5% | LOW |
| `submission.py` (baseline) | 177 | aiter gemm_a4w4_asm | Baseline (13.4 µs) | LOW |

**Notes:**
- Reference baseline: ~13.4 µs (aiter API ceiling)
- Leader: ~4.3 µs (3.1x gap)
- 4 Ollama iteration files (iter1-iter4)
- BLOCK_K >= 128 mandatory for Triton FP4
- Quantization (~26 µs) dominates actual GEMM (~7-10 µs)

---

## 4. RUNNER DEPLOYMENT PLAN

### Phase 1: Test Mode for All (Days 1-2)

**Objective:** Validate correctness before benchmark runs

```bash
# Test all Tier 1 (Breakthrough)
popcorn run submission_breakthrough_moe.py --mode test --leaderboard amd-moe-mxfp4
popcorn run submission_breakthrough_mla.py --mode test --leaderboard amd-mla-decode
popcorn run submission_breakthrough_gemm.py --mode test --leaderboard amd-mxfp4-mm

# Test all Tier 2 (Best Variants)
popcorn run submission_moe_dispatch_policy.py --mode test --leaderboard amd-moe-mxfp4
popcorn run submission_best_mla_final.py --mode test --leaderboard amd-mla-decode
popcorn run submission_fastmode.py --mode test --leaderboard amd-mla-decode
popcorn run submission.py --mode test --leaderboard amd-mxfp4-mm  # GEMM baseline

# Test Tier 3 (Selected Experimental)
popcorn run submission_loadinline.py --mode test --leaderboard amd-mxfp4-mm
popcorn run submission_fp4mfma_v6.py --mode test --leaderboard amd-mxfp4-mm
```

**Success Criteria:**
- [ ] All Tier 1 kernels pass test mode
- [ ] At least 4 Tier 2 kernels pass test mode
- [ ] At least 2 Tier 3 kernels pass test mode

**Failure Protocol:**
- Test FAIL → Analyze log → Fix issue → Redeploy
- Document failure mode in KERNEL_REFERENCE.md
- Skip to next variant in tier

### Phase 2: Benchmark Successful (Days 2-3)

**Objective:** Measure performance against baselines

```bash
# Benchmark breakthrough candidates
popcorn run submission_breakthrough_moe.py --mode benchmark --leaderboard amd-moe-mxfp4
popcorn run submission_breakthrough_mla.py --mode benchmark --leaderboard amd-mla-decode
popcorn run submission_breakthrough_gemm.py --mode benchmark --leaderboard amd-mxfp4-mm

# Benchmark best variants
popcorn run submission_moe_dispatch_policy.py --mode benchmark --leaderboard amd-moe-mxfp4
popcorn run submission_best_mla_final.py --mode benchmark --leaderboard amd-mla-decode
```

**Recording Template:**
```
Kernel: <name>
Variant: <file>
Test: PASS
Benchmark Results:
  - Shape 1: <µs> (baseline: <µs>)
  - Shape 2: <µs> (baseline: <µs>)
  - Average: <µs> (baseline: <µs>)
Improvement: <±%>
Decision: [Proceed to Phase 3 / Try Next Variant]
```

**Decision Matrix:**
| Result | Action |
|--------|--------|
| Improved >5% | Proceed to Phase 3 |
| Improved 0-5% | Document, try next variant |
| No improvement | Try next tier |
| Regression | Debug or abandon |

### Phase 3: Leaderboard Submission (Days 3-4)

**Objective:** Submit optimized kernels to ranked leaderboard

```bash
# Submit breakthroughs first (highest potential)
popcorn run submission_breakthrough_moe.py --mode leaderboard --leaderboard amd-moe-mxfp4
popcorn run submission_breakthrough_mla.py --mode leaderboard --leaderboard amd-mla-decode
popcorn run submission_breakthrough_gemm.py --mode leaderboard --leaderboard amd-mxfp4-mm

# Submit best variants
popcorn run submission_moe_dispatch_policy.py --mode leaderboard --leaderboard amd-moe-mxfp4
popcorn run submission_best_mla_final.py --mode leaderboard --leaderboard amd-mla-decode
```

**CRITICAL: Benchmark ≠ Ranked**
- Ranked runner has warm JIT caches
- Benchmark improvements may not translate to ranked
- Session 91 proof: ALL 5 "improved" benchmark submissions scored WORSE on ranked
- ONLY GPU compute improvements help in ranked mode

**Post-Submission Documentation:**
```
Leaderboard Results:
  - Kernel: <name>
  - Rank: <position>
  - Score: <µs>
  - Benchmark vs Ranked Delta: <±%>
  - Notes: <observations>
```

---

## 5. SUCCESS METRICS

### Minimum (Must Achieve)

- [ ] At least 1 kernel from Tier 1 passes correctness test
- [ ] At least 3 kernels from Tier 2 pass correctness test
- [ ] No regressions from previous best-known results
- [ ] All deployment phases completed for at least 1 kernel

### Target (Aim For)

- [ ] 3+ kernels show improvement over baseline in benchmark mode
- [ ] At least 1 kernel achieves ranked submission with measurable score
- [ ] MoE kernel within 1.2x of leader (currently 1.4x, target <130 µs)
- [ ] Documentation updated with all findings

### Stretch (Aspire To)

- [ ] Top 10 ranking on any single kernel
- [ ] Breakthrough improvement (>20%) on MoE or MLA
- [ ] Custom kernel via load_inline successfully deployed and ranked
- [ ] 2+ kernels in competitive range (<1.5x leader)

### Scoring Thresholds

| Kernel | Current | Target | Stretch |
|--------|---------|--------|---------|
| MoE | 154 µs (1.4x) | 130 µs (1.2x) | 109 µs (1.0x) |
| MLA | 69.7 µs (2.1x) | 50 µs (1.5x) | 33 µs (1.0x) |
| GEMM | 13.4 µs (3.1x) | 10 µs (2.3x) | 4.3 µs (1.0x) |

---

## 6. RISK MITIGATION

### High-Risk Scenarios

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| load_inline blocked | Medium | HIGH | Fallback to Tier 2 variants |
| Triton FP4 wrong results | Medium | MEDIUM | Use BLOCK_K>=128, verify correctness |
| Benchmark ≠ Ranked | High | MEDIUM | Focus on compute optimization only |
| JIT timeout | Medium | HIGH | Pre-warm caches, reduce variants |
| Rate limiting | High | LOW | Prioritize Tier 1 first, queue intelligently |

### Common Failure Modes & Fixes

| Error | Likely Cause | Fix |
|-------|--------------|-----|
| `KeyError: 'float4_e2m1fn_x2'` | Using aiter MXFP4 API | Use tritonblas or delegate to ref_kernel |
| Silent wrong results (80% match) | Triton JIT callsite issue | Match reference.py call pattern exactly |
| `doweight_stage1` NaN | Correctness-breaking flag | Set `doweight_stage1=False` |
| Column 0 correct, col 1+ wrong | MFMA register layout | Use column-major output mapping |
| BLOCK_K < 128 with FP4 | Hardware constraint violation | Use BLOCK_K >= 128 |
| fast_mode slower | MI355X specific behavior | Use fast_mode=False |

### Contingency Plans

1. **If all Tier 1 fail:**
   - Immediately pivot to Tier 2 best variants
   - Document failure reasons
   - Update research direction

2. **If Tier 2 underperform:**
   - Try remaining Tier 2 variants
   - Select promising Tier 3 approaches
   - Focus on highest probability wins

3. **If time running out (< 2 hours):**
   - Submit working Tier 2 variants immediately
   - Document current state for handoff
   - Prioritize correctness over optimization

---

## 7. QUICK REFERENCE

### Essential Commands

```bash
# Syntax check before deployment
python -m py_compile submission_<kernel>.py

# Test mode (correctness)
popcorn run submission_<kernel>.py --mode test --leaderboard amd-<kernel>

# Benchmark mode (performance)
time popcorn run submission_<kernel>.py --mode benchmark --leaderboard amd-<kernel>

# Leaderboard submission (FINAL)
popcorn run submission_<kernel>.py --mode leaderboard --leaderboard amd-<kernel>
```

### Leaderboard Names

- `amd-mxfp4-mm` (GEMM)
- `amd-moe-mxfp4` (MoE)
- `amd-mla-decode` (MLA)

### Critical Constraints

- `BLOCK_K >= 128` for Triton FP4 (mandatory)
- `doweight_stage1=False` for MoE correctness
- `fast_mode=False` for MLA (faster on MI355X)
- Do NOT use ctypes kernel dispatch (confirmed blocked)
- Benchmark ≠ Ranked score (warm JIT effects)

---

## 8. APPENDIX: FILE INVENTORY

### Documentation Files
- `DEPLOYMENT_CHECKLIST_FINAL.md` - Deployment procedures
- `MASTER_OPTIMIZATION_REPORT.md` - Comprehensive optimization report
- `KERNEL_REFERENCE.md` - Quick kernel reference
- `LEADERBOARD_SCORES.md` - Current standings
- `RESEARCH_SYNTHESIS_FINAL.md` - Research findings
- `RESEARCH_FLASH_ATTENTION.md` - Flash Attention research
- `RESEARCH_THUNDERKITTENS.md` - ThunderKittens research
- `RESEARCH_CK_TILE.md` - CK-Tile research

### Submission Directories
- `amd-mixed-mla/` - 138 MLA kernel files
- `amd-moe-mxfp4/` - 125 MoE kernel files
- `amd-mxfp4-mm/` - 104 GEMM kernel files

### Tooling
- `deploy_submissions.sh` - Batch deployment script
- `final_deploy.sh` - Final deployment orchestration
- `auto_benchmark.sh` - Automated benchmarking
- `popcorn-cli` - Competition submission tool

---

**Prepared for:** Luma AMD Speedrun Deployment Sprint  
**Last Updated:** April 6, 2026  
**Next Review:** Post-deployment results analysis
