---
name: amd-moe-mxfp4-prime
description: "MXFP4 Mixture-of-Experts kernel optimization for AMD MI355X. Target: <120us from 154.2us."
---

# SKILL: AMD_MOE_MXFP4_PRIME

## DOMAIN EXPERTISE
MXFP4 Mixture-of-Experts kernel optimization for AMD MI355X. Target: <120us from 154.2us.

## KEY FACTS
* Current best: 154.2us. Leader: 109.8us. Gap: 1.4x. (Closest to leader of all 3 kernels)
* HBM writeback between Gate+Up and Down GEMMs is the bottleneck.
* 182 pre-compiled kernels at /home/runner/aiter/hsa/gfx950/fmoe_2stages/ (NOT accessible via API).
* fused_moe parameters ALL EXHAUSTED (KSPLIT, sorting, block_size, doweight_stage1).
* Existing HipKittens MoE kernel template at genesis-engine worktree.

## INSTRUCTION
1. Create load_inline LDS Bridge kernel:
   - Keep Gate+Up GEMM intermediates in LDS (64KB per CU)
   - Feed directly to Down GEMM without HBM round-trip
   - Potential: 30-50us savings (one kernel launch eliminated)
2. Use CK-Tile MoE primitives (ck_moe_stage1/2) via load_inline
3. Study existing HK MoE kernel: .claude/worktrees/genesis-engine/hipkittens_moe/hipkittens_moe_kernel.hpp
4. Adaptive KSPLIT: KSPLIT=4 for sparse (est_m<10), KSPLIT=2 for dense
5. Use AITER_BYPASS_TUNE_CONFIG=1 to override CSV-locked shapes

## DEAD ENDS
- fused_moe parameter tuning — ALL EXHAUSTED
- fmoe_g1u1 — NaN for 32-expert shapes
- Direct cktile_moe_gemm1/2 — "Unsupported scales/output dtype!"
- torch.compile — auto_functionalized_v2 not supported on ROCm 7.1
- Expert masking with bincount — uint32 overflow GPU memory fault
- OPUS sorting (dispatch_policy=1) — 19.3% worse on 257E configs

## VERSION
v1.0.0
