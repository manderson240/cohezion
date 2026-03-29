# Luma AMD Speedrun - Session Coordination

## Status
- **Last Updated**: 2026-03-25 07:35 UTC
- **Active Sessions**: Parallel optimization
- **Competition Deadline**: March 30, 2026 (5 days remaining)

### Current Benchmark Results (2026-03-25)
| Kernel | Best µs | Rank 1 µs | Gap | Notes |
|--------|----------|------------|-----|-------|
| GEMM | **22.0** | 4.327 | **5.1× behind** | JIT 20s+ per shape; no tuned config |
| MoE | **167.0** | 109.793 | **1.5× behind** | fused_moe + USE_NT=1 + ksplit=4 |
| MLA | **70.0** | 32.972 | **2.1× behind** | three-regime routing |

### SurrealDB Results Logged
- GEMM: 22.0µs (HIP_ONLINE_TUNING=1)
- MoE: 167.0µs (fused_moe + USE_NT=1 + ksplit=4)
- MLA: 70.0µs (three-regime routing)

### Custom Triton Kernels Plan

#### Priority #1: GEMM (3.1× gap)
**Template**: `autoresearch/templates/gemm_fused_template.py`
**Approach**: Fused quant+GEMM via `tl.dot_scaled`
- Uses `dynamic_mxfp4_quant` for A quantization
- Uses `e8m0_unshuffle` to recover raw B scale (~0.1µs)
- `tl.dot_scaled` with `"e2m1"` format
- **Status**: Template exists but needs template code synthesis

#### Priority #2: MLA (2.1× gap)
**Template**: `autoresearch/templates/mla_flash_template.py`
**Approach**: FlashAttention-style single-pass kernel
- Single kernel processes Q tiles while iterating KV tiles
- Handles K=576, V=512 asymmetric dimensions
- **Status**: Template exists but incomplete

#### Priority #3: MoE (1.4× gap)
**Template**: `autoresearch/templates/moe_triton_template.py`
**Approach**: Custom Triton MoE with persistent tiles
- Stage 1 + Stage 2 with fused activation
- **Status**: Template exists but incomplete

### Breakthrough Path: HipKittens DSL

Per CUSTOM_TRITON_KERNELS_PLAN.md:
- **HipKittens** (arxiv:2511.08083) is the breakthrough path
- Write ORIGINAL kernels using HK tile primitives
- 8-Wave Ping-Pong scheduling for GEMM
- Native MFMA instructions for MLA

### Infrastructure
- Ralph Loop integration ready: `autoresearch/ralph_main.py`
- SurrealDB logging: `autoresearch/surreal_tracker.py`
- Git worktrees: `.worktrees/{gemm,moe,mla}-command-center`

### Critical Blocker
**Test/benchmark timeouts**: Popcorn CLI timeouts (300+ seconds) preventing validation.

### Dead Ends (Do NOT Retry)
- Direct ctypes dispatch: BLOCKED by stream isolation
- gemm_a4w4_blockscale: "Not supported" on runner
- cktile direct dispatch: Wrong dtype
- torch.compile on ROCm: anti-pattern

### Rate Limits (per leaderboard, 1/hour)
- **amd-moe-mxfp4**: Check for latest
- **amd-mxfp4-mm**: Check for latest
- **amd-mixed-mla**: Check for latest

### Ralph Loop + Autoresearch Integration
| File | Purpose |
|------|---------|
| `autoresearch/ralph_main.py` | Ralph Loop main with coherence gating |
| `autoresearch/ralph_integrator.py` | Coherence computation + HIHO gate |
| `autoresearch/inject_breakthrough_nodes.py` | Injects breakthrough nodes into trees |
| `autoresearch/tree/*_tree.json` | Updated with breakthrough hypotheses |

### Rate Limits (per leaderboard, 1/hour)
- **amd-moe-mxfp4**: Check for latest
- **amd-mxfp4-mm**: Check for latest
- **amd-mixed-mla**: Check for latest

### Dead Ends Confirmed This Session
- KSPLIT bypass: Worse (-7.5%) — CSV tuning is optimal
- OPUS sorting: Much worse (-19.3%) — kills large shapes
- Custom Triton v2/v3: Crash (scale dimension mismatches)
- gemm_a4w4 log2_ks: Not in API schema
- gemm_a4w4_asm direct: Wrong kernel selection (27K mismatches)
- MLA expanded splits: No improvement — bottleneck is compute volume
- **KSPLIT env var approach**: AITER_KSPLIT not honored by aiter kernel (aiter computes its own estimated_m_per_expert internally)

## Staging Directory Structure

Each kernel directory has a `staging/` folder where sessions place their submissions:

```
kernels/
├── mixed-mla/
│   ├── submission.py          # Current active submission (symlink or copy)
│   ├── reference.py
│   ├── task.py
│   └── staging/
│       ├── submission.<session>.<timestamp>.py
│       └── ...
├── mxfp4-mm/
│   └── staging/
└── moe-mxfp4/
    └── staging/
```

## Naming Convention

**Format**: `submission.<session-name>.<YYYYMMDD_HHMMSS>.py`

**Examples**:
- `submission.opencode.k2-5.20260318_144500.py`
- `submission.gemini.v2.20260318_150000.py`
- `submission.antigravity.20260318_153000.py`
- `submission.claude.latest.20260318_160000.py`

## Session Registry

| Session Name | Status | Last Submission | Best Result |
|-------------|--------|----------------|-------------|
| opencode-hip-k2-5 | ACTIVE | 2026-03-18 15:45 | GEMM: ~23µs, MLA: ~67µs, MoE: ~184µs |
| **autoresearch** | ACTIVE | 2026-03-19 18:10 | GEMM: 24.2µs ranked (no change), MoE: KSPLIT validated (6.4%), MLA: MXFP4 ASM broken (aiter regression) |
| **moe-specialist** | NEW | 2026-03-24 10:17 | MoE: 167.1µs benchmark (10.2% improvement from baseline) |
| gemini | unknown | - | - |
| antigravity | unknown | - | - |
| claude | unknown | - | - |

## Submission Workflow

1. **Work in your workspace**: Edit files in your session directory
2. **Copy to staging**: When ready, copy to `kernels/<kernel>/staging/`
3. **Update this file**: Add your submission to the Session Registry table
4. **Wait for consensus**: Before copying to main `submission.py`

## Current Submissions (Staging)

### GEMM (amd-mxfp4-mm)
- [x] opencode: `submission.opencode.k2-5.20260318_152837.py` - gemm_a4w4 baseline (~23µs)
- [ ] gemini: TBD
- [ ] antigravity: TBD
- [ ] claude: TBD
- **Reference**: Updated to official luma_speedrun version (uses dynamic_mxfp4_quant)
- **Status**: Test submission in progress (2026-03-18 15:28)

### MLA (amd-mixed-mla)
- [x] opencode: `submission.opencode.k2-5.latest.py` - reference implementation (~67µs)
- [ ] gemini: TBD
- [ ] antigravity: TBD
- [ ] claude: TBD
- **Reference**: Updated to official luma_speedrun version (FP8 optimized, a8w8 kernel)

### MoE (amd-moe-mxfp4)
- [x] moe-specialist: `submission.moe-specialist.20260324_101727.py` - USE_NT + Adaptive KSPLIT (167.1µs geom mean, test ✅)
- **Previous best**: 178.2µs benchmark (USE_NT=1 only)
- **Improvement**: 10.2% from baseline ~186µs
- **Target**: 145µs (leader)
- **Gap**: 1.21x

## MoE Optimization Notes (moe-specialist session)

### What Was Tried
1. **USE_NT=1 alone**: 178µs ranked
2. **Adaptive KSPLIT table alone**: Not tested standalone
3. **Combined (USE_NT=1 + Adaptive KSPLIT)**: 167.1µs benchmark

### Key Finding
The `AITER_KSPLIT` environment variable is NOT honored by the aiter kernel. The aiter kernel computes its own `estimated_m_per_expert` internally (visible in stderr logs) and uses that for kernel selection.

### Benchmark Shape Details
| Shape | Time (µs) | AITER_KSPLIT Used | Notes |
|-------|-----------|-------------------|-------|
| 257 experts, bs=16 | 139 | 4 | Sparse |
| 257 experts, bs=128 | 217 | 4 | Sparse |
| 257 experts, bs=512 | 250 | 4 | Sparse |
| 33 experts, bs=16 | 59.8 | 2 | Medium |
| 33 experts, bs=128 | 108 | 2 | Medium |
| 33 experts, bs=512 | 213 | 0 | Dense |
| 33 experts, d=2048, bs=512 | 350 | 0 | Dense |

## Current Best Results vs Rank 1

### GEMM (amd-mxfp4-mm)
- **Our Best**: 13.425µs
- **Rank 1**: 4.327µs
- **Gap**: 3.1×
- **Breakthrough Path**: Direct CK dispatch via ctypes (blocked by stream sync error)

### MLA (amd-mixed-mla)
- **Our Best**: 69.745µs
- **Rank 1**: 32.972µs
- **Gap**: 2.1×
- **Breakthrough Path**: PS metadata buffer pre-allocation (avoids 20-30µs C++ overhead)

### MoE (amd-moe-mxfp4)
- **Our Best**: 154.183µs
- **Rank 1**: 109.793µs
- **Gap**: 1.4×
- **Breakthrough Path**: Direct cktile_moe_gemm1/2 dispatch + 182 pre-compiled kernels

## Breakthrough Findings Summary (2026-03-24)

| Kernel | Finding | Status |
|--------|---------|--------|
| GEMM | 288-byte kernel arg layout found. 35 .co files exist. Direct ctypes dispatch hits stream sync error (B001). | 🔴 Blocker |
| MoE | Direct cktile_moe_gemm1/2 dispatch path found. 182 pre-compiled kernels exist. | 🟡 Opportunity |
| MLA | Persistent mode PS buffer pre-allocation avoids 20-30µs C++ overhead. | 🟡 Opportunity |

## Action Items

- [x] GEMM: Found kernel arg layout, confirmed blocker
- [x] MoE: Found direct CK dispatch path
- [x] MLA: Found PS buffer optimization path
- [ ] GEMM: Try alternative path (blockscale tuning, custom Triton)
- [ ] MoE: Test direct cktile_moe_gemm dispatch
- [ ] MLA: Implement PS buffer pre-allocation
- [ ] All sessions: Document optimization strategies in vault
- [ ] Consensus: Decide which submission goes to leaderboard
- [ ] Submit to leaderboard before March 30 deadline

## Lock Status

**Current Lock**: NONE

When a session is actively submitting to Popcorn CLI:
1. Change `Current Lock` to your session name
2. List the kernel(s) being submitted
3. Unlock when done

**Example**:
```
Current Lock: moe-specialist
Kernels: MoE (benchmark mode)
Started: 2026-03-24 10:00 UTC
```

## Communication

- Check this file before submitting
- Update immediately after submitting
- Use vault/SurrealDB for detailed learnings
- Coordinate in shared Discord/Slack if available

## MoE Specialist Investigation (2026-03-24)

### Investigation Summary

**What I investigated:**

1. **DIRECT CKTILE DISPATCH** - Investigated calling `cktile_moe_gemm1/2` directly
   - Status: CONFIRMED DEAD END
   - Error: "Unsupported scales/output dtype!" on fp8_e8m0
   - The kernel naming convention was identified: `moe_cktile2stages_gemm{stage}_{BLOCK_SIZE}x{MPerBlock}x{NPerBlock}x{KPerBlock}_{WAVE_MAP_M}x{WAVE_MAP_N}_{WAVE_TILE_M}x{WAVE_TILE_N}x{WAVE_TILE_K}_{BlockPerCU}perCU_{QuantType}_{ActOP}{MulRoutedWeight}{HasBias}{SplitK}`

2. **E2E MoE PERSISTENT KERNEL** - Investigated `e2e_moe_persistent_kernel`
   - Status: NOT ACCESSIBLE via Python API
   - Module not available in aiter package

3. **182 PRECOMPILED KERNELS** - Researched kernels at `/home/runner/aiter/hsa/gfx950/fmoe_2stages/`
   - Status: NOT ACCESSIBLE - cannot be invoked directly without knowing internal calling conventions

4. **MLA PERSISTENT MODE** - Found that MLA uses `AITER_MLA_USE_PERSISTENT=1`
   - Status: NO EQUIVALENT for MoE found
   - No `AITER_MOE_USE_PERSISTENT` env var exists

5. **Alternative Weight Paths** - Investigated using raw vs shuffled weights
   - Status: `fused_moe` REQUIRES shuffled weights (pre-shuffled in reference.py)
   - Raw weights require manual handling that's been confirmed slower

### Key Findings

1. **All Python API paths exhausted** - kernel_program.md confirms:
   - `cktile_moe_gemm1` direct dispatch: "Unsupported scales/output dtype!"
   - `doweight_stage1=True`: GPU memory fault
   - `expert_mask=bincount`: GPU crash (uint32 overflow)
   - `AITER_KSPLIT` env var: Ignored by kernel
   - Custom Triton: 68% slower than CK ASM

2. **Current best**: 154.183µs (ranked on leaderboard)
   - Using: `USE_NT=1` + adaptive KSPLIT
   - Gap to Rank 1: 1.4x (154.183µs vs 109.793µs)

3. **Test infrastructure issue**: Popcorn tests are timing out
   - Likely JIT compilation overhead on server
   - Current submission may need JIT pre-warming

### Recommended Next Steps

1. **For immediate improvement**: Focus on JIT pre-warming
   - The MLA submission uses persistent mode successfully
   - MoE might benefit from similar pre-allocation strategies

2. **For breakthrough**: Need to investigate C++ internals
   - The 182 pre-compiled kernels represent the true optimization opportunity
   - May require understanding CK tile scheduling directly

3. **For the team**: Consider:
   - Probing the aiter package with `inspect.getsource(fused_moe)` on the server
   - Checking if there are hidden configuration options in the C++ code
   - Investigating if rank-1 solution uses a completely different kernel invocation method

### Ralph Loop Status
- Coherence check: 0.5 threshold
- No improvement in 7+ cycles
- Recommend trying a completely different approach (inspect-based probing)

