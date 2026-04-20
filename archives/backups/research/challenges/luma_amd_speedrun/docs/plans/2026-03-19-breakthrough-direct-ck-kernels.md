# Scattershot Plan v3: Remaining Paths Across All Kernels

Created: 2026-03-19
Status: PENDING
Approved: Yes
Iterations: 3
Worktree: No

> **Status Lifecycle:** PENDING -> COMPLETE -> VERIFIED
> **Deadline:** March 30, 2026 (11 days remaining)

## Why v2 Was Obsolete Before It Started

v2 proposed probing `fmoe_g1u1`, `deepgemm_ck`, `ck_moe_stage1/2`, and MLA work distribution.
Skill restructuring (v3.0 of `competitive-kernel-optimization-ceiling` → 3 kernel-specific
skills) confirmed ALL four probes are dead ends:

| Probe | Status | Confirmed By |
|-------|--------|-------------|
| `fmoe_g1u1` | DEAD — NaN for 32-expert, no gain for 256-expert | `amd-moe-mxfp4-optimization` Phase 17 |
| `deepgemm_ck` | DEAD — grouped GEMM only, requires `group_layout` | `amd-gemm-mxfp4-optimization` Phase 7 |
| `ck_moe_stage1/2` | DEAD — "Unsupported scales/output dtype!", replicates fused_moe | `amd-moe-mxfp4-optimization` Phase 18 |
| MLA work distribution | Already implemented — metadata caching + adaptive splits | `amd-mla-decode-optimization` Phases 10-17 |

## v3 Strategy: Scattershot Remaining Paths

Accept that all high-probability paths are exhausted. Fire at the remaining low-probability
paths in parallel. Any single improvement on any kernel is a win.

### Current Leaderboard

| Kernel | Our Best | Leader | Gap | Skill |
|--------|----------|--------|-----|-------|
| GEMM (`amd-mxfp4-mm`) | ~14.1µs | 9.7µs | 1.45x | `amd-gemm-mxfp4-optimization` |
| MoE (`amd-moe-mxfp4`) | ~155µs | 145µs | 1.07x | `amd-moe-mxfp4-optimization` |
| MLA (`amd-mixed-mla`) | ~67.8µs | 4.3µs | 15.8x | `amd-mla-decode-optimization` |

## Track 1: GEMM Optimizer (Highest ROI)

**Agent:** `gemm-optimizer`
**Target:** 14.1µs → <12µs
**Skill reference:** `amd-gemm-mxfp4-optimization`

### Submission 1.1: gemm_afp4wfp4 skip_reduce=True exploitation
- `gemm_afp4wfp4` with `skip_reduce=True` returns `[num_splits, M, N]` float32 partials
- Custom reduce (e.g., `torch.sum(dim=0)`) may be faster than internal reduce for some shapes
- Risk: Triton persistent kernel may not expose individual splits usefully

### Submission 1.2: Per-shape config discovery
- Read `AITER_TRITON_CONFIGS_PATH` JSON files on runner via stderr probe
- Check if M=16/N=2112/K=7168 (the bottleneck shape at 21.7µs) has a tuned entry
- If not, discover what config it falls back to and whether a better one exists

### Submission 1.3: Quant dispatch floor reduction
- Profile `dynamic_mxfp4_quant` in isolation — is the 26µs floor JIT or compute?
- If JIT: pre-warm via ref_kernel call before timed region
- If compute: try `torch.compile(dynamic_mxfp4_quant)` (may work unlike fused_moe)

### Submission 1.4: Triton persistent fused quant+GEMM (long shot)
- The runner's Triton has `float4_e2m1fn_x2` KeyError for `tl.dot_scaled`
- BUT: can we do bf16 quant inside the kernel and use bf16 `tl.dot` instead?
- This avoids the fp4 type entirely while still fusing quant into the GEMM

## Track 2: MoE Infrastructure (Unblock + Marginal Gains)

**Agent:** `moe-infra`
**Target:** Fix timeout, then test remaining low-V paths
**Skill reference:** `amd-moe-mxfp4-optimization`

### Submission 2.1: AITER_JIT_DIR persistence probe
- Set `AITER_JIT_DIR=/tmp/aiter_jit_cache` before `import aiter`
- Submit with `--mode test` twice — second should skip JIT builds
- If JIT persists across submissions, the 720s timeout is solved
- This enables all future MoE experiments

### Submission 2.2: Fix active-expert masking
- Phase 18 crashed with `GPU memory access fault` — cumsum produces -1 IDs → uint32(4.3B) OOB
- Fix: clamp expert IDs to valid range before weight indexing
- ```python
  expert_mask = torch.bincount(topk_ids.flatten(), minlength=num_experts) > 0
  # Remap expert indices to compact range [0, num_active)
  compact_map = torch.cumsum(expert_mask, dim=0) - 1  # -1 for zero-indexed
  # Guard: only index into w1/w2 with valid expert IDs
  ```
- Expected: ~3µs Python overhead but saves sorting overhead for 224 empty experts

### Submission 2.3: IREE K-tile heuristic probe
- Read runner's CSV configs for competition shapes via stderr
- Check if K-tile is suboptimal per IREE Issue #22309
- If so, test if `block_m` override via direct cktile call can help
  (requires 2.1 to succeed first for timeout budget)

## Track 3: MLA Explorer (Low Probability)

**Agent:** `mla-explorer`
**Target:** Any improvement below 67.8µs
**Skill reference:** `amd-mla-decode-optimization`

### Submission 3.1: FP8 Triton attention (BLOCK_N=64 or 128)
- Phase 9 tested BLOCK_N=32 → 168µs (Triton dispatch floor)
- Larger blocks reduce total grid size → fewer launches
- BUT: same ~130µs dispatch floor applies regardless of block size
- Long shot: if block size eliminates enough grid cells, total may drop

### Submission 3.2: torch.compile on einsum regime
- The matmul regime (bs<=4 OR total_kv<=32768) uses torch.matmul+softmax+matmul
- `torch.compile(mode="reduce-overhead")` may fuse these 3 ops into 1 CUDA graph
- Unlike fused_moe, these are standard PyTorch ops — no `auto_functionalized_v2` issue
- Expected: 2-5µs reduction in matmul regime if graph capture succeeds

### Submission 3.3: Verify best submission is active
- MLA submission was silently corrupted once (Phase 16)
- Read current `submission.py`, verify it matches Phase 17 best (fast_mode=False)
- If corrupted, restore from backup

## Agent Definitions

### gemm-optimizer

```yaml
role: GEMM kernel optimization for amd-mxfp4-mm
skills:
  - amd-gemm-mxfp4-optimization
  - popcorn-cli-amd-kernel-submission
  - popcorn-benchmark-vs-ranked-scoring
focus: |
  Exploit gemm_afp4wfp4 internals (split-K, per-shape configs).
  Reduce quant dispatch overhead. Fuse where possible.
  Always compare ranked (not benchmark) geomean to 14.1µs baseline.
constraints:
  - Never switch from gemm_a4w4 (ASM) to gemm_afp4wfp4 for the main path
  - Never retry custom HIP compilation (scanner blocks)
  - Never retry custom tl.dot_scaled with fp4 (KeyError on runner)
  - Always restore best backup before leaderboard submit
submissions: 4 (1.1-1.4)
```

### moe-infra

```yaml
role: MoE infrastructure unblock and marginal optimization
skills:
  - amd-moe-mxfp4-optimization
  - aiter-kernel-parameter-semantics
  - popcorn-cli-amd-kernel-submission
focus: |
  First priority: solve JIT timeout via AITER_JIT_DIR.
  Then test active-expert masking and K-tile heuristic.
  All experiments gated on timeout solution.
constraints:
  - Never use doweight_stage1=True (crashes or wrong results)
  - Never use KSPLIT=4 for 32-expert shapes (overflow)
  - Never retry fmoe_g1u1 (dead end confirmed Phase 17)
  - Never retry direct CK dispatch (replicates fused_moe)
submissions: 3 (2.1-2.3), with 2.2-2.3 gated on 2.1 success
```

### mla-explorer

```yaml
role: MLA decode low-probability exploration
skills:
  - amd-mla-decode-optimization
  - deepseek-mla-decode-flash-attention-gap
  - popcorn-cli-amd-kernel-submission
focus: |
  Test torch.compile on matmul regime. Verify submission integrity.
  Try larger Triton blocks if time permits.
  Accept that Python dispatch floor limits gains.
constraints:
  - Never retry MXFP4 KV cache (blocked by aiter)
  - Never retry hiprtc/load_inline (scanner blocks)
  - Never change EINSUM_THRESHOLD from 131072 (confirmed optimal)
  - Always verify submission matches Phase 17 best before experimenting
submissions: 3 (3.1-3.3)
```

## Execution Order

1. **Day 1:** Submit 3.3 (verify MLA submission), 2.1 (JIT cache probe), 1.2 (config discovery)
   — all independent, can run in parallel
2. **Day 2-3:** Submit 1.1, 1.3 based on 1.2 results; Submit 2.2 if 2.1 succeeded
3. **Day 4-6:** Submit 1.4 (long shot Triton fusion), 3.2 (torch.compile), 2.3 (K-tile)
4. **Day 7-8:** Final leaderboard submissions with best results from each track

## Success Criteria

1. At least ONE kernel improves its RANKED score (not just benchmark)
2. All 3 leaderboard entries verified to be best-ever submissions
3. Dead ends and results documented in kernel-specific skills

## Dead Ends — COMPLETE LIST (Do NOT Retry)

### GEMM
- All non-ASM GEMM APIs (gemm_a4w4 non-ASM, blockscale, _scaled_mm_v2, deepgemm, LLMM1, hipb_mm, rocb_mm)
- Custom tl.dot_scaled MXFP4 (float4_e2m1fn_x2 KeyError on runner)
- CUDA/HIP graph capture (copy_() overhead exceeds kernel time)
- HIP C++ quant kernel (correct but 10% slower than Triton)
- Custom HIP compilation from submission.py (scanner blocks)

### MoE
- fmoe_g1u1 (NaN for 32-expert, no gain for 256-expert)
- Direct CK dispatch (cktile_gemm1/2) — replicates fused_moe
- ck_moe_stage1/2 — "Unsupported scales/output dtype!"
- torch.compile on fused_moe (auto_functionalized_v2 blocks)
- doweight_stage1=True (crashes or 82% mismatches)
- AITER_BYPASS_TUNE_CONFIG (dead code for competition shapes)
- Parameter tuning (KSPLIT, auto-tune) — at ceiling

### MLA
- MXFP4 KV cache (head_size assertion blocks all paths)
- hiprtc via ctypes (scanner blocks)
- load_inline (scanner blocks)
- F.scaled_dot_product_attention (head_dim=576 exceeds limit)
- 4D matmul with broadcast (9-53x regression)
- Triton FlashDecoding BLOCK_N=32 (~130µs dispatch floor)
- EINSUM_THRESHOLD != 131072 (all other values regress)
- kv_granularity != 16 (all other values regress)
