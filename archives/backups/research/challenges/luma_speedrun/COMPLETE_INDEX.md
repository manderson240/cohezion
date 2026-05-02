# FINAL COMPREHENSIVE INDEX — Luma AMD Speedrun Sprint

**Created:** April 6, 2026  
**Sprint Duration:** March–April 2026 (30+ sessions)  
**Competition:** Luma AMD Speedrun (GPU MODE × AMD)  
**Hardware:** AMD Instinct MI355X (gfx950, CDNA4, ROCm 7.1)  

---

## EXECUTIVE SUMMARY

This index documents the complete output of the Luma AMD Speedrun sprint — one of the most intensive GPU kernel optimization efforts attempted, spanning **484 Python files**, **93 documentation files**, and **60+ kernel implementations** across three kernel types.

### Final Performance

| Kernel | Our Best | Leader | Gap | Status |
|--------|----------|--------|-----|--------|
| **GEMM** | 13.3 µs | 4.3 µs | 3.1× | API Ceiling Reached |
| **MoE** | 134 µs | 70 µs | 1.9× | API Ceiling Reached |
| **MLA** | 69.7 µs | 19 µs | 3.7× | Dispatch Floor Reached |

**Key Finding:** Parameter tuning is exhausted across all kernels. Custom `load_inline` HIP kernels can reduce Python overhead but cannot close the remaining gap without access to the harness timing stream.

---

## PART 1: ALL SUBMISSIONS (400+ Kernel Files)

### 1.1 MLA (Multi-head Latent Attention) Decode — 146 Submissions

**Location:** `luma_speedrun/amd-mixed-mla/`

| File | Lines | Description |
|------|-------|-------------|
| `submission.py` | ~200 | **BASELINE** — einsum + ASM hybrid |
| `submission_best_mla_final.py` | ~400 | Best performing hybrid approach |
| `submission_fastmode.py` | ~150 | fast_mode=True optimization |
| `submission_nosplit.py` | ~120 | num_kv_splits=1 variant |
| `submission_a2_splits.py` | ~180 | Fixed splits=32 variant |
| `submission_a3_mxfp4kv.py` | ~220 | MXFP4 KV cache attempt (BLOCKED) |
| `submission_a5_optimized.py` | ~190 | Optimized parameter sweep |
| `submission_a6_devkernarg.py` | ~200 | HIP_FORCE_DEV_KERNARG variant |
| `submission_a7_fastmode.py` | ~160 | Combined fast_mode optimizations |
| `submission_a8_lowthresh.py` | ~175 | Lower threshold variant |
| `submission_a16w16.py` | ~140 | A16W16 precision variant |
| `submission_asm_only.py` | ~130 | Pure ASM dispatch |
| `submission_asm_decode_bypass.py` | ~150 | ASM with decode bypass |
| `submission_bf16_only.py` | ~145 | BF16-only path |
| `submission_bf16_pure_v3.py` | ~170 | Pure BF16 v3 |
| `submission_dec_bf16_v3.py` | ~185 | BF16 decoder v3 |
| `submission_hybrid_v2.py` | ~220 | Hybrid routing v2 |
| `submission_hybrid_v3.py` | ~240 | Hybrid routing v3 |
| `submission_hybrid_bs4.py` | ~200 | Batch size 4 hybrid |
| `submission_linear_attention.py` | ~300 | Linear attention approximation |
| `submission_factorized_attention.py` | ~280 | Factorized attention approach |
| `submission_progressive_attention.py` | ~290 | Progressive decoding |
| `submission_sliding_window.py` | ~250 | Sliding window attention |
| `submission_sdpa.py` | ~130 | SDPA backend |
| `submission_fmhav3.py` | ~140 | FlashAttention v3 |
| `submission_fmhav3_padded.py` | ~160 | FMHA with padding |
| `submission_cudagraph.py` | ~180 | CUDA Graph attempt (BLOCKED) |
| `submission_direct_ck.py` | ~200 | Direct CK dispatch |
| `submission_loadinline.py` | ~350 | load_inline custom kernel |
| `submission_direct_loadinline_v2.py` | ~400 | load_inline v2 |
| `submission_custom_mla.py` | ~380 | Custom MLA implementation |
| `submission_custom_mla_v2.py` | ~420 | Custom MLA v2 |
| `submission_ultra_aggressive.py` | ~200 | Aggressive optimization |
| `submission_aggressive.py` | ~180 | Standard aggressive |
| `submission_compute_opt_v1.py` | ~170 | Compute-bound optimization |
| `submission_wrapper.py` | ~190 | Wrapper dispatch |
| `submission_breakthrough_mla.py` | ~250 | Breakthrough attempt |
| `submission_probe_mla_apis.py` | ~160 | API probing |
| `submission_shape_probe.py` | ~140 | Shape probing |
| `submission_memory_bandwidth.py` | ~170 | Memory bandwidth optimization |
| `submission_compound_v1.py` | ~210 | Compound approach |
| `submission_all_einsum.py` | ~150 | Pure einsum |
| `submission_multiwave_v3.py` | ~240 | Multi-wave scheduling |
| `reference_implementation.py` | ~180 | Reference for comparison |

**Ollama Research Submissions (100+ iterations):**
- `submission_ollama_mla_iter*.py` (iter1 through iter97) — Systematic iteration via local models

**Additional MLA Dirs:**
- `amd-mla-blockwise/` — Blockwise attention (1 submission)
- `amd-mla-chunked/` — Chunked processing (1 submission)
- `amd-mla-chunked-opt/` — Optimized chunked (1 submission)
- `amd-mla-pi-rope/` — Pi RoPE variant (1 submission)
- `amd-mla-reordered-kv/` — Reordered KV cache (1 submission)
- `amd-mla-rotary/` — Rotary embeddings (1 submission)
- `amd-mla-sparse-blocks/` — Sparse block attention (1 submission)

**Total MLA Lines:** ~43,693

---

### 1.2 GEMM (MXFP4 Matrix Multiply) — 119 Submissions

**Location:** `luma_speedrun/amd-mxfp4-mm/`

| File | Lines | Description |
|------|-------|-------------|
| `submission.py` | ~120 | **BASELINE** — aiter.gemm_a4w4 |
| `submission_naive_13us.py` | ~130 | Best baseline (13.4µs) |
| `submission_tuned.py` | ~40 | Tuned configuration |
| `submission_triton_v2.py` | ~284 | Triton v2 kernel |
| `submission_triton_v2_gemma.py` | ~355 | Triton optimized for Gemma |
| `submission_triton_splitk.py` | ~366 | Triton Split-K |
| `submission_triton_v3.py` | ~320 | Triton v3 with optimizations |
| `submission_winograd_gemm.py` | ~391 | Winograd transformation |
| `submission_splitk_gemm.py` | ~280 | Split-K implementation |
| `submission_mfma_128.py` | ~350 | MFMA 128×128 tiles |
| `submission_mfma_256.py` | ~380 | MFMA 256×256 tiles |
| `submission_8wave_pingpong.py` | ~400 | 8-wave ping-pong scheduling |
| `submission_splitk_sequential.py` | ~310 | Sequential Split-K |
| `submission_splitk_parallel.py` | ~330 | Parallel Split-K |
| `submission_g2_ksplit.py` | ~150 | G2 k_split variant |
| `submission_g6_bypass.py` | ~140 | BYPASS_TUNE_CONFIG |
| `submission_g7_nt.py` | ~130 | USE_NT variant |
| `submission_g8_lean.py` | ~160 | Lean aiter |
| `submission_asm_gemm.py` | ~180 | ASM dispatch |
| `submission_loadinline_gemm.py` | ~400 | load_inline kernel |
| `submission_compound_gemm.py` | ~250 | Compound approach |
| `submission_breakthrough_gemm.py` | ~300 | Breakthrough attempt |
| `submission_per_1x32_f4_quant.py` | ~170 | Per-1x32 quantization |
| `submission_hipblaslt.py` | ~140 | hipBLASLt backend |
| `submission_deepgemm.py` | ~160 | DeepGEMM integration |
| `submission_wmma_gemm.py` | ~200 | WMMA implementation |
| `submission_rocwmma.py` | ~220 | rocWMMA library |
| `submission_f4_f8_hybrid.py` | ~190 | FP4/FP8 hybrid |
| `submission_ck_gemm.py` | ~210 | Composable Kernel |
| `submission_fused_quant_gemm.py` | ~280 | Fused quant+GEMM |

**Additional GEMM Dirs:**
- `amd-mxfp4-blocked/` — Blocked GEMM (1 submission)
- `amd-mxfp4-block-sparse/` — Block-sparse (1 submission)
- `amd-mxfp4-cannon/` — Cannon's algorithm (1 submission)
- `amd-mxfp4-fft-gemm/` — FFT-based (1 submission)
- `amd-mxfp4-mixed-tiling/` — Mixed tiling (1 submission)
- `amd-mxfp4-outer-product/` — Outer product (324 lines)
- `amd-mxfp4-sparse-dense/` — Sparse-dense (308 lines)
- `amd-mxfp4-splitk-atomic/` — Atomic Split-K (303 lines)
- `amd-mxfp4-strassen/` — Strassen algorithm (518 lines)
- `amd-mxfp4-toeplitz/` — Toeplitz matrices (476 lines)
- `amd-mxfp4-walsh-hadamard/` — Walsh-Hadamard (351 lines)
- `amd-mxfp4-winograd/` — Winograd convolution (348 lines)

**Total GEMM Lines:** ~19,790

---

### 1.3 MoE (Mixture of Experts) MXFP4 — 134+ Submissions

**Location:** `luma_speedrun/amd-moe-mxfp4/`

| File | Lines | Description |
|------|-------|-------------|
| `submission.py` | ~180 | **BASELINE** — fused_moe API |
| `submission_adaptive_batch.py` | ~145 | Adaptive batching |
| `submission_alt_api.py` | ~396 | Alternative API paths |
| `submission_asm_moe.py` | ~59 | ASM MoE dispatch |
| `submission_blockm_tuned.py` | ~77 | Tuned block_M |
| `submission_blockscale_g1u1.py` | ~255 | Block-scaled FP8 G1U1 |
| `submission_blockscale_v2.py` | ~192 | Block-scaled v2 |
| `submission_blockscale_v3.py` | ~211 | Block-scaled v3 |
| `submission_breakthrough_moe.py` | ~123 | Breakthrough attempt |
| `submission_candidate.py` | ~230 | Candidate kernel |
| `submission_cktile_moe.py` | ~450 | CK-Tile MoE |
| `submission_cktile_moe_v2.py` | ~612 | CK-Tile v2 |
| `submission_compound_v1.py` | ~272 | Compound approach |
| `submission_compute_opt_v1.py` | ~128 | Compute optimization |
| `submission_conditional_routing.py` | ~269 | Conditional routing |
| `submission_dispatch1_mask.py` | ~55 | Dispatch policy 1 |
| `submission_dispatch2.py` | ~45 | Dispatch policy 2 |
| `submission_dynamic_capacity.py` | ~366 | Dynamic capacity |
| `submission_early_exit_v4.py` | ~243 | Early exit optimization |
| `submission_expert_dropout.py` | ~343 | Expert dropout |
| `submission_expert_mask.py` | ~83 | Expert masking |
| `submission_expert_pruning.py` | ~120 | Expert pruning |
| `submission_fmoe_g1u1.py` | ~200 | fmoe_g1u1 variant |
| `submission_fused_gate.py` | ~175 | Fused gating |
| `submission_hierarchical_routing.py` | ~290 | Hierarchical routing |
| `submission_ksplit_adaptive.py` | ~195 | Adaptive KSPLIT |
| `submission_ksplit_optimized.py` | ~185 | Optimized KSPLIT |
| `submission_lora_adapter.py` | ~220 | LoRA adapter |
| `submission_m1_clean.py` | ~140 | Clean baseline |
| `submission_m2_ksplit.py` | ~160 | M2 KSPLIT variant |
| `submission_meta_routing.py` | ~310 | Meta-learning routing |
| `submission_moe_hybrid.py` | ~240 | Hybrid MoE |
| `submission_parallel_topk.py` | ~170 | Parallel top-k |
| `submission_predictive_dispatch.py` | ~260 | Predictive dispatch |
| `submission_quant_type_per1x32.py` | ~150 | Per-1x32 quantization |
| `submission_quant_type_tensor.py` | ~145 | Per-tensor quantization |
| `submission_socialized_routing.py` | ~280 | Socialized routing |
| `submission_sparse_comm.py` | ~190 | Sparse communication |
| `submission_token_prefetch.py` | ~210 | Token prefetching |
| `submission_topk_optimization.py` | ~165 | Top-k optimization |

**Additional MoE Dirs:**
- `amd-moe-attention-routing/` — Attention-based routing (1 submission)
- `amd-moe-contrastive/` — Contrastive learning (1 submission, ~200 lines)
- `amd-moe-curriculum-learning/` — Curriculum learning (1 submission)
- `amd-moe-dynamic-capacity/` — Dynamic capacity (1 submission)
- `amd-moe-hierarchical/` — Hierarchical experts (1 submission)
- `amd-moe-meta-routing/` — Meta-routing (1 submission)
- `amd-moe-sparse-comm/` — Sparse communication (1 submission)
- `amd-moe-token-prefetch/` — Token prefetch (1 submission)

**Total MoE Lines:** ~75,535

---

### 1.4 Submission Totals by Category

| Category | Files | Lines | Best Performance |
|----------|-------|-------|------------------|
| **MLA** | 146 | ~43,693 | 69.7 µs |
| **GEMM** | 119 | ~19,790 | 13.3 µs |
| **MoE** | 134 | ~75,535 | 134 µs |
| **Total** | **399+** | **139,018+** | — |

---

## PART 2: ALL RESEARCH DOCUMENTS (40+ Files)

### 2.1 Core Research Papers

| Document | Lines | Description |
|----------|-------|-------------|
| `RESEARCH_MASTER_SUMMARY.md` | ~781 | Comprehensive research synthesis |
| `RESEARCH_FUTURE_OUTLOOK.md` | ~150 | Future optimization paths |
| `RESEARCH_SYNTHESIS_FINAL.md` | ~400 | Final research synthesis |
| `RESEARCH_DR_KERNEL.md` | ~300 | Dr.Kernel paper analysis |
| `RESEARCH_KERNELBENCH.md` | ~250 | KernelBench research |
| `RESEARCH_MULTIKERNELBENCH.md` | ~200 | Multi-KernelBench analysis |
| `RESEARCH_CK_TILE.md` | ~180 | CK-Tile research |
| `RESEARCH_THUNDERKITTENS.md` | ~220 | ThunderKittens analysis |
| `RESEARCH_TILELANG.md` | ~170 | TileLang research |
| `RESEARCH_FLASH_ATTENTION.md` | ~190 | Flash Attention research |
| `RESEARCH_DEEPSEEK_OPTIMIZATIONS.md` | ~240 | DeepSeek optimizations |
| `FINAL_RESEARCH_FINDINGS.md` | ~529 | Final findings compilation |

### 2.2 Session Reports

| Document | Lines | Description |
|----------|-------|-------------|
| `SESSION_90_COMPREHENSIVE.md` | ~450 | Session 90 comprehensive report |
| `SESSION_91_FINAL.md` | ~520 | Session 91 final |
| `SESSION_95_CONTINUATION.md` | ~300 | Session 95 continuation |
| `SESSION_LOG.md` | ~200 | Session activity log |
| `ULTIMATE_SPRINT_FINALE.md` | ~350 | Sprint finale summary |
| `FINAL_SPRINT_SUMMARY.md` | ~280 | Final sprint summary |

### 2.3 Status & Tracking Documents

| Document | Lines | Description |
|----------|-------|-------------|
| `PROJECT.md` | ~152 | Project management |
| `CONSOLIDATED_STATE.md` | ~180 | Consolidated state |
| `EXECUTION_STATUS.md` | ~150 | Execution status |
| `FINAL_BATCH_STATUS.md` | ~120 | Batch status |
| `LEADERBOARD_STATUS.md` | ~140 | Leaderboard tracking |
| `LEADERBOARD_SCORES.md` | ~200 | Score tracking |
| `RANKED_SHAPES.md` | ~160 | Ranked shape analysis |
| `RUNNER_INVENTORY.md` | ~180 | Runner API inventory |
| `OPTIMIZATION_LOG.md` | ~153 | Optimization cycle log |
| `MASTER_OPTIMIZATION_REPORT.md` | ~400 | Master optimization report |
| `TEST_RESULTS.md` | ~130 | Test results |
| `TODO.md` | ~100 | Task tracking |
| `ARCHIVE.md` | ~250 | Archive |
| `WORK_SAVED.md` | ~120 | Saved work log |

### 2.4 Deployment Documents

| Document | Lines | Description |
|----------|-------|-------------|
| `DEPLOYMENT_CHECKLIST_FINAL.md` | ~200 | Final deployment checklist |
| `FINAL_DEPLOYMENT_READINESS.md` | ~180 | Deployment readiness |
| `FINAL_DEPLOYMENT_SUMMARY.md` | ~150 | Deployment summary |
| `FINAL_BREAKTHROUGH_PLAN.md` | ~300 | Breakthrough plan |
| `CRITICAL_BREAKTHROUGH_PLAN.md` | ~280 | Critical breakthrough |
| `HANDOFF_NEXT_SESSION.md` | ~140 | Session handoff |
| `OVERNIGHT_HANDOFF.md` | ~120 | Overnight handoff |

### 2.5 Reference Documents

| Document | Lines | Description |
|----------|-------|-------------|
| `KERNEL_REFERENCE.md` | ~309 | Kernel API reference |
| `QUICK_REFERENCE.md` | ~180 | Quick command reference |
| `TEAMS.md` | ~150 | Team structure |
| `[Public] AMD x GPU MODE...` | ~100 | Competition rules |

**Total Documentation:** ~93 markdown files, ~9,000+ lines

---

## PART 3: INFRASTRUCTURE & TOOLS

### 3.1 Autoresearch Framework (`autoresearch/`)

| File | Lines | Purpose |
|------|-------|---------|
| `ksearch_tree.py` | 300 | K-Search tree implementation |
| `gpu_kernel_scientist.py` | 268 | GPU Kernel Scientist pattern |
| `code_synthesizer.py` | 299 | Code synthesis |
| `analyzer.py` | 138 | Analysis tools |
| `driver.py` | 246 | Research driver |
| `popcorn.py` | 210 | Popcorn CLI integration |
| `__init__.py` | 12 | Package init |
| `continuous_generate.sh` | ~50 | Continuous generation script |

**Templates:** `templates/__init__.py`

**State:** `state/gemm_tree.json`, `state/moe_tree.json`, `state/mla_tree.json`, `state/cross_kernel_*.json`

**K-Search Trees:** `state/ksearch_trees/gemm_tree_v1.json`, `moe_tree_v1.json`, `mla_tree_v1.json`

**Total Autoresearch:** ~1,473 lines

### 3.2 Deployment Scripts (`deploy/`)

| File | Lines | Purpose |
|------|-------|---------|
| `tier1_breakthrough/` | — | Breakthrough candidates |
| `tier2_best/` | — | Best submissions |
| `tier3_experimental/` | — | Experimental variants |

**Deployment Code:** ~6,004 lines across tiers

### 3.3 Shell Scripts (18 files)

| Script | Purpose |
|--------|---------|
| `auto_benchmark.sh` | Automated benchmarking |
| `auto_final_sprint.sh` | Final sprint automation |
| `batch_submit.sh` | Batch submission |
| `cant_stop_wont_stop.sh` | Persistent execution |
| `deploy_submissions.sh` | Deployment script |
| `execute_breakthrough.sh` | Breakthrough execution |
| `final_deploy.sh` | Final deployment |
| `local_model_iterate.sh` | Local model iteration |
| `monitor_breakthrough.sh` | Monitoring |
| `monitor.sh` | General monitoring |
| `ollama_kernel_iterate.sh` | Ollama kernel iteration |
| `optimize_all.sh` | Optimize all kernels |
| `run-parallel.sh` | Parallel execution |
| `save_work.sh` | Work preservation |
| `submit_all.sh` | Submit all kernels |
| `submit_and_iterate.sh` | Submit + iterate |
| `submit_breakthrough_results.sh` | Submit breakthroughs |
| `task.sh` | Task runner |

### 3.4 Python Infrastructure

| File | Lines | Purpose |
|------|-------|---------|
| `breakthrough_orchestrator.py` | ~200 | Orchestration |
| `deploy_breakthroughs.py` | ~250 | Breakthrough deployment |
| `ollama_research_task.py` | ~180 | Ollama research tasks |
| `variants/gemm/*.py` | 2 | GEMM variants |
| `variants/moe/*.py` | 2 | MoE variants |
| `variants/mla/*.py` | 2 | MLA variants |

### 3.5 Skills (`.claude/skills/`)

| Skill | Description |
|-------|-------------|
| `gfx950-mfma-register-layouts/` | MFMA register mappings |
| `popcorn-runner-api-inventory/` | Popcorn API inventory |
| `popcorn-rate-limit-management/` | Rate limit management |

---

## PART 4: COMPLETE FILE MANIFEST

### 4.1 Quick Reference by Task

| Task | File/Dir |
|------|----------|
| **Best GEMM** | `amd-mxfp4-mm/submission_naive_13us.py` (13.4µs) |
| **Best MLA** | `amd-mixed-mla/submission_best_mla_final.py` (69.7µs) |
| **Best MoE** | `amd-moe-mxfp4/submission.py` (134µs) |
| **Research Papers** | `RESEARCH_MASTER_SUMMARY.md` |
| **API Reference** | `KERNEL_REFERENCE.md` |
| **Optimization Log** | `OPTIMIZATION_LOG.md` |
| **K-Search Trees** | `autoresearch/state/ksearch_trees/` |
| **Runner Inventory** | `RUNNER_INVENTORY.md` |
| **Deployment** | `deploy/tier2_best/` |

### 4.2 File Counts by Directory

| Directory | Python Files | Markdown | Total |
|-----------|-------------|----------|-------|
| `amd-mixed-mla/` | 146 | 1 | 147 |
| `amd-mxfp4-mm/` | 119 | 0 | 119 |
| `amd-moe-mxfp4/` | 134 | 0 | 134 |
| `amd-moe-*/` | 8 | 0 | 8 |
| `amd-mla-*/` | 6 | 0 | 6 |
| `amd-mxfp4-*/` | 11 | 0 | 11 |
| `autoresearch/` | 7 | 0 | 7 |
| `deploy/` | 30+ | 0 | 30+ |
| `variants/` | 6 | 0 | 6 |
| `root/` | 0 | 43 | 43 |
| **Total** | **467** | **44** | **511+** |

### 4.3 Total Line Counts

| Category | Lines |
|----------|-------|
| MLA Submissions | ~43,693 |
| GEMM Submissions | ~19,790 |
| MoE Submissions | ~75,535 |
| Autoresearch Framework | ~1,473 |
| Deployment Code | ~6,004 |
| Documentation | ~9,000+ |
| **Grand Total** | **~155,000+** |

---

## PART 5: KEY DISCOVERIES

### 5.1 Working Techniques

1. **load_inline HIP Kernels** — Session 95 verified working on Popcorn runners
2. **Undocumented ASM APIs** — `mla_decode_fwd` with `fast_mode=False` is faster on MI355X
3. **MFMA 32×32×64** — Correct FP4 computation verified
4. **Undocumented `moe_sorting_dispatch_policy=1`** — Reduces worst-case shapes by 37%

### 5.2 Blocked Paths

1. **ctypes hipModuleLaunchKernel** — "work on another stream" error
2. **MXFP4 KV cache for MLA** — "head_size == KV.size(3)" limitation
3. **torch.compile** — auto_functionalized_v2 error on ROCm 7.1
4. **CUDA Graph** — Harness stream incompatibility

### 5.3 Research Papers Applied

| Paper | Application |
|-------|-------------|
| K-Search (arXiv:2602.19128) | `autoresearch/ksearch_tree.py` |
| GPU Kernel Scientist (arXiv:2506.20807) | `autoresearch/gpu_kernel_scientist.py` |
| GEAK | `autoresearch/` framework |
| Flash Attention | MLA optimizations |
| ThunderKittens | Template exploration |

---

## PART 6: SESSIONS & MILESTONES

| Session | Date | Key Achievement |
|---------|------|-----------------|
| 1-10 | March 2026 | Initial exploration, baseline establishment |
| 11-20 | March 2026 | API parameter discovery |
| 21-30 | March 2026 | Load_inline experiments |
| 31-40 | March 2026 | Triton kernel attempts |
| 41-50 | March 2026 | Research paper integration |
| 51-60 | March 2026 | K-Search implementation |
| 61-70 | March 2026 | Autoresearch framework |
| 71-80 | April 2026 | MFMA verification |
| 81-90 | April 2026 | GPU Kernel Scientist |
| 91-95 | April 2026 | Final optimization attempts |

---

## PART 7: QUICK COMMAND REFERENCE

```bash
# Test a submission
popcorn-cli submit <kernel>/submission.py --mode test --gpu MI355X --leaderboard <name>

# Benchmark
popcorn-cli submit <kernel>/submission.py --mode benchmark --gpu MI355X --leaderboard <name>

# Leaderboard submission
popcorn-cli submit <kernel>/submission.py --mode leaderboard --gpu MI355X --leaderboard <name>

# Run autoresearch
python autoresearch/driver.py --kernel <type> --cycles 10

# Deploy best kernels
bash deploy_submissions.sh

# Save work
bash save_work.sh
```

---

## APPENDIX: FULL FILE LIST

### All Python Submissions (Sample)

```
# MLA (amd-mixed-mla/)
submission.py
submission_best_mla_final.py
submission_fastmode.py
submission_nosplit.py
submission_a2_splits.py
... (142 more)

# GEMM (amd-mxfp4-mm/)
submission.py
submission_naive_13us.py
submission_triton_v2.py
submission_triton_splitk.py
... (115 more)

# MoE (amd-moe-mxfp4/)
submission.py
submission_adaptive_batch.py
submission_cktile_moe.py
submission_breakthrough_moe.py
... (130 more)
```

### All Research Documents

```
RESEARCH_MASTER_SUMMARY.md
RESEARCH_FUTURE_OUTLOOK.md
RESEARCH_SYNTHESIS_FINAL.md
RESEARCH_DR_KERNEL.md
RESEARCH_KERNELBENCH.md
RESEARCH_MULTIKERNELBENCH.md
RESEARCH_CK_TILE.md
RESEARCH_THUNDERKITTENS.md
RESEARCH_TILELANG.md
RESEARCH_FLASH_ATTENTION.md
RESEARCH_DEEPSEEK_OPTIMIZATIONS.md
FINAL_RESEARCH_FINDINGS.md
... (32 more)
```

---

**END OF INDEX**

*This document serves as the definitive master reference for the Luma AMD Speedrun sprint. For questions or updates, refer to the PROJECT.md and CONSOLIDATED_STATE.md files in this directory.*

**Last Updated:** April 6, 2026  
**Total Artifacts Documented:** 500+ files, 155,000+ lines
