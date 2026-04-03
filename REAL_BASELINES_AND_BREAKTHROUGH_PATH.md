# REAL BASELINES & BREAKTHROUGH PATH
**Date**: 2026-04-02  
**Status**: Correcting baselines from historical data

---

## ⚠️ BASELINE CORRECTION

From analyzing `research/challenges/luma_amd_speedrun/`:

### Historical Best (Proven on Popcorn)

| Kernel | Documented Best | When Achieved | Current Submission | Gap |
|--------|-----------------|---------------|-------------------|-----|
| **GEMM** | **22.0µs** | March 25 | `aiter.gemm_a4w4_asm()` (JIT) | 5.1× behind Rank 1 |
| **MLA** | **69.745µs** | March 24-30 | Three-regime routing (6 splits) | 2.1× behind Rank 1 |
| **MoE** | **154.183µs** | March 24-25 | fused_moe + USE_NT=1 + KSPLIT=2 | 1.4× behind Rank 1 |

**Note**: The 13.425µs mentioned in older docs was likely from a different approach that is **no longer valid** (per COORDINATION.md: "may have been achieved with a different approach that is no longer valid")

---

## 🎯 REAL BREAKTHROUGH PATHS (Based on All Prior Work)

### 1. MoE → **MOST ACHIEVABLE** (1.4× to Rank 1)

**Current**: 154.183µs  
**Target**: 107.793µs (Rank 1)  
**Gap**: **1.4×** (DOABLE in 4 days)

**Strategy from team.json**:
```python
# Priority: HIGH
"cktile_moe_gemm1/2 direct dispatch"  # Skip fused_moe API overhead
"e2e_moe_persistent_kernel"          # Persistent tiles
"Probe 182 precompiled kernels"       # Already compiled at /home/runner/aiter/hsa/gfx950/fmoe_2stages/
```

**Dead End Confirmed**:
- ❌ `doweight_stage1=True` - GPU memory fault (catastrophic)
- ❌ `expert_mask` - crashes CK stage1 kernel
- ❌ KSPLIT=4 for 32-expert - overflow

**Working Approach**:
- ✅ `USE_NT=1` (non-temporal hints)
- ✅ Adaptive KSPLIT: {sparse: 4, medium: 2, dense: 1}
- ✅ Block size tuning (64, 128, 256)
- 🎯 **Breakthrough**: Direct CK .co dispatch (bypass Python API)

---

### 2. MLA → **ACHIEVABLE** (2.1× to Rank 1)

**Current**: 69.745µs  
**Target**: 32.972µs (Rank 1)  
**Gap**: **2.1×** (HARD but possible)

**Strategy from COORDINATION.md**:
```python
# Priority: HIGH
"pod_attention probe"                   # Persistent FlashAttention-style
"fav3_sage_attention_mxfp4"             # SageAttention for MXFP4
"PS metadata buffer pre-allocation"     # Eliminate allocation overhead
```

**Working** (current submission):
- ✅ Three-regime routing:
  - Small (bs≤4): torch.einsum bf16
  - Medium: mla_decode_fwd a16w8
  - Large: mla_decode_fwd a8w8
- ✅ 6 splits for metadata (optimal)

**Dead Ends**:
- ❌ `mla_decode_fwd_mxfp4` - aiter regression (broken)
- ❌ Expanded splits - no improvement (bottleneck is compute volume)

**Breakthrough Path**:
- 🎯 Custom Triton kernel: single-pass Q×K + Softmax×V
- 🎯 `__builtin_amdgcn_mfma_scale_f32_32x32x64_f8f6f4` via inline assembly
- 🎯 64×64 tiles per head

---

### 3. GEMM → **HARDEST** (5.1× to Rank 1)

**Current**: 22.0µs (JIT compilation, 20s+ per shape)  
**Target**: 4.327µs (Rank 1)  
**Gap**: **5.1×** (Requires breakthrough)

**Strategy from COORDINATION.md**:
```python
# Priority: HIGH
"fused_gemm_a8w8_blockscale_*"          # Fused quant+GEMM
"gemm_a4w4_blockscale with tuned splitK" # Split-K optimization
"HIP_ONLINE_TUNING=1"                    # Enable tuning
```

**Dead Ends Confirmed**:
- ❌ `gemm_a4w4_blockscale` - "Not supported" on runner (API error)
- ❌ `gemm_a4w4_ASM` direct - wrong kernel selection (27K mismatches)
- ❌ Custom Triton v2/v3 - scale dimension mismatches
- ❌ `log2_ksplit` parameter - not in API schema

**Current Working Approach** (in submission.py):
- ✅ `load_inline` with custom HIP kernel
- ✅ Block-wise GEMM (BLOCK=16)
- ✅ LIFTED scales (computed once per block)
- ✅ FP4 e2m1 unpack + E8M0 scale

**Breakthrough Path**:
- 🎯 **V_MFMA_SCALE_F32_16X16X128_F8F6F4** intrinsic
- 🎯 8-wave ping-pong scheduling
- 🎯 Direct global→LDS transfers (128-bit/lane)
- 🎯 Fused quant+GEMM (single kernel, zero Python overhead)

---

## 📊 SUBMISSION DATABASE (From Staging)

### Proven Working Submissions

**MoE (kernels/moe-mxfp4/staging/)**:
- `submission.opencode.k2-5.20260318_152837.py` - 167µs baseline
- Multiple KSPLIT variants tested
- `doweight_stage1=False` required

**GEMM (kernels/mxfp4-mm/staging/)**:
- `submission.opencode.k2-5.20260318_152837.py` - ~23µs baseline
- `submission.claude.*.py` - load_inline variants
- Multiple MFMA v3/v4 attempts

**MLA (kernels/mixed-mla/staging/)**:
- `submission.autoresearch.fixed_metadata.py` - 69.7µs
- `submission.autoresearch.fp8_adaptive_splits.py` - 70µs range
- Multiple split configurations

---

## 🛠️ UNTAPPED BREAKTHROUGH TOOLS

From `team.json["untapped_tools"]` - These have NOT been fully explored:

### Ready for Immediate Use

1. **`fused_gemm_afp4wfp4_a16w16`** - GEMM - Priority HIGH
   - Status: May exist in aiter but not yet probed
   - Action: Search aiter.ops for fused variants

2. **`pod_attention`** - MLA - Priority HIGH  
   - Status: Template exists but incomplete
   - Action: Complete FlashAttention-style Triton kernel

3. **`fav3_sage_attention_mxfp4`** - MLA - Priority HIGH
   - Status: SageAttention variant for MXFP4
   - Action: Implement from arxiv paper

4. **`e2e_moe_persistent_kernel`** - MoE - Priority MED
   - Status: Has .hpp in genesis worktree
   - Action: Integrate HipKittens MoE kernel

5. **`hstu_attention`** - MLA - Priority MED
   - Status: Alternative attention mechanism
   - Action: Research and implement

---

## 🎯 IMMEDIATE BREAKTHROUGH ACTIONS

### Day 1 (Today): MoE Breakthrough
**Easiest win - 1.4× improvement needed**

```bash
# Action 1: Probe 182 pre-compiled kernels
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint

# Action 2: Direct CK .co dispatch (bypass fused_moe)
python3 -c "
import subprocess
# Query available kernels
result = subprocess.run(['ls', '-la', '/home/runner/aiter/hsa/gfx950/fmoe_2stages/'], 
                       capture_output=True, text=True)
print(result.stdout)
"

# Action 3: Submit with expert mask + direct dispatch
popcorn-cli submit luma_speedrun/amd-moe-mxfp4/submission.py \
    --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4
```

**Target**: <120µs (approachable), <110µs (Rank 1)

---

### Day 2-3: MLA Breakthrough
**2.1× improvement - requires kernel work**

```bash
# Action 1: Complete Triton FlashAttention template
cat luma_speedrun/autoresearch/templates/mla_flash_template.py

# Action 2: Fill in missing pieces:
# - Q tile processing
# - KV tile iteration
# - Single-pass kernel

# Action 3: Compile and test
# Action 4: Submit
```

**Target**: <50µs (improvement), <35µs (top 10), 32.972µs (Rank 1)

---

### Day 3-4: GEMM Breakthrough
**5.1× improvement - requires breakthrough kernel**

```bash
# Action 1: Implement V_MFMA_SCALE in load_inline
cat luma_speedrun/amd-mxfp4-mm/submission.py

# Action 2: Add 8-wave ping-pong scheduling
# Action 3: Direct global→LDS transfers

# Action 4: Compile with --offload-arch=gfx950
# Action 5: Submit
```

**Target**: <15µs (improvement), <10µs (top 10), 4.327µs (Rank 1)

---

## 📈 SUCCESS PROBABILITY

| Kernel | Gap | Difficulty | Tools Ready | Success Likely?
|--------|-----|------------|-------------|----------------|
| **MoE** | 1.4× | 🟢 Medium | ✅ Yes | **HIGH** - Days 1-2 |
| **MLA** | 2.1× | 🟡 Hard | ⚠️ Partial | **MEDIUM** - Days 2-3 |
| **GEMM** | 5.1× | 🔴 Extreme | ⚠️ Research | **LOW** - Days 3-4 |

**Recommendation**: Focus energy on **MoE first** (easiest win), then MLA, then GEMM.

---

## 📁 KEY RESOURCES (All Found)

| File | What It Contains |
|------|------------------|
| `research/challenges/luma_amd_speedrun/COORDINATION.md` | Real baselines + what's working |
| `research/challenges/luma_amd_speedrun/autoresearch/team.json` | 4-agent configuration |
| `research/challenges/luma_amd_speedrun/autoresearch/ralph_main.py` | Ralph Loop framework |
| `luma_speedrun/autoresearch/templates/` | Triton kernel templates |
| `kernels/*/staging/` | 40+ submission variants tested |
| `cloud-vault-mcp/vault/cerebellum/luma-amd-speedrun-strategy.md` | Competition strategy |

---

## 🚨 CRITICAL INSIGHT

**The 13.425µs GEMM number is likely INVALID**:  
*"Note: The 13.425µs best mentioned in team.json may have been achieved with a different approach that is no longer valid"* - COORDINATION.md

**Real verified baseline**: 22.0µs (March 25, HIP_ONLINE_TUNING=1)

---

## ✅ NEXT ACTIONS (Choose One)

### A. Start with MoE (Recommended)
```bash
# Easiest path to Rank 1
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint
cp research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/staging/submission.moe-winner.py \
   luma_speedrun/amd-moe-mxfp4/submission.py

popcorn-cli submit luma_speedrun/amd-moe-mxfp4/submission.py \
    --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4
```

### B. Focus on MLA
```bash
# Complete the FlashAttention template
vim luma_speedrun/autoresearch/templates/mla_flash_template.py
# Then compile and submit
```

### C. Aggressive GEMM
```bash
# Requires custom kernel development
vim luma_speedrun/amd-mxfp4-mm/submission.py
# Implement V_MFMA_SCALE intrinsic
```

---

**Real baselines established. Breakthrough paths documented. Ready for execution.**
