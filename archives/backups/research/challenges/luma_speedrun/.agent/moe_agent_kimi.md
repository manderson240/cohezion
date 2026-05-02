# 🎯 MoE Agent — Kimi Assignment

**Agent:** You (Kimi K2.5 Cloud)  
**Kernel:** MoE (amd-moe-mxfp4)  
**Current Best:** 154.183µs (rank ~63)  
**Target:** <100µs (rank ~30)  
**Gap:** 1.5x improvement needed  

---

## 📋 CURRENT STATUS

**Phase:** Implementation — FP8 Blockscale v2  
**Started:** T+0  
**Last Update:** T+0  
**ETA:** T+2 hours for first test submission

---

## 🎯 ASSIGNMENT

### Primary Approach: FP8 Blockscale Kernel Exploitation

**From Session 95 Discovery:**
The runner has an **undocumented FP8 blockscale kernel**:
- Location: `/home/runner/aiter/hsa/gfx950/fmoe/fmoe_fp8_blockscale_g1u1_novs_subGU_256.co`
- API: `aiter.fmoe_fp8_blockscale_g1u1()`
- Block size: 128×128 (fc_scale_blkn=128, fc_scale_blkk=128)

**Why This Could Win:**
1. FP8 has wider MFMA throughput than FP4 (2× compute potential)
2. Blockscale quantization is different from per_1x32 — may better utilize hardware
3. The `novs` (no vertical scaling) variant is lighter weight
4. Completely different code path from baseline fused_moe

---

## 🔧 TECHNICAL DETAILS

### Previous Attempt Analysis
**File:** `../amd-moe-mxfp4/submission_blockscale_g1u1.py`

**Failure Mode:** MXFP4→FP8 conversion produced incorrect scale layouts

**Root Cause (Identified):**
1. `pertoken_quant()` expected different input format than provided
2. Scale tensor dimensions didn't match kernel expectations
3. Missing shuffle layout verification

### v2 Implementation Plan

**File to Create:** `../amd-moe-mxfp4/submission_fp8_blockscale_v2.py`

**Key Fixes:**
1. **Proper weight dequantization:** Use `fp4_utils.mxfp4_to_f32()` correctly
2. **Scale reshaping:** Ensure [E, n_blocks] format for kernel
3. **Activation quantization:** Use `dynamic_per_token_scaled_quant` with correct group_size
4. **Block size validation:** Assert all dims divisible by 128

**Expected API Call:**
```python
aiter.fmoe_fp8_blockscale_g1u1(
    moe_buf,              # output [M, model_dim] bf16
    a1_fp8,               # input [M, model_dim] fp8
    w1_shuffled,          # gate [E, 2*d_expert, d_hidden] fp8
    w2_shuffled,          # down [E, d_hidden, d_expert] fp8
    sorted_ids,           # sorted_token_ids
    sorted_weights,         # sorted_weights
    sorted_expert_ids,    # sorted_expert_ids
    num_valid_ids,        # num_valid_ids
    total_top_k,          # topk
    a1_scale_t,           # input_scale [model_dim//128, M]
    w1_scale,             # fc1_scale [E, n_blocks]
    w2_scale,             # fc2_scale [E, n_blocks]
    "",                   # kernelName (auto-select)
    128,                  # fc_scale_blkn
    128,                  # fc_scale_blkk
    None,                 # fc2_smooth_scale
    aiter.ActivationType.Silu.value,
    32,                   # block_size_M
)
```

---

## 🧪 TESTING PROTOCOL

### Step 1: Correctness (Test Mode)
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

**Expected:** 4/4 tests pass

### Step 2: Benchmark (If Correct)
```bash
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

**Target:** <150µs geomean (first milestone)

### Step 3: Leaderboard (If Improved)
```bash
popcorn-cli submit --mode leaderboard --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

---

## 📝 DISCOVERY LOG

### T+0 — Assignment Received
- **Status:** Starting v2 implementation
- **Approach:** Fix MXFP4→FP8 conversion in blockscale_g1u1
- **Expected:** Proper scale tensor handling

### (To be updated every 30 min...)

---

## 🚧 BLOCKER TRACKER

| Blocker | Status | Resolution |
|---------|--------|------------|
| MXFP4→FP8 conversion | 🔴 ACTIVE | Implementing v2 with corrected scale layout |

---

## 🔄 FALLBACK PLANS

### If FP8 Blockscale Fails
1. **Shape-aware dispatch:** Different strategy per d_expert (256 vs 512 vs 2048)
2. **AITER_KSPLIT exploration:** Even though env var is ignored, try shape-based split logic
3. **fmoe_g1u1_tkw1:** Token-wise weight quant variant (different .co kernel)

### If Correctness Passes But No Speedup
1. Try `novs` variant explicitly (kernelName="novs_subGU_256")
2. Vary block_size_M (16, 32, 64)
3. Profile with IntelliKit if available

---

## 📊 SUCCESS CRITERIA

| Milestone | Target | Reward |
|-----------|--------|--------|
| Test passing | 4/4 tests | 🟢 Proceed to benchmark |
| Benchmark <150µs | 1.03x improvement | 🟡 Iterate for more speed |
| Benchmark <120µs | 1.28x improvement | 🟢 Submit to leaderboard |
| Leaderboard <100µs | 1.54x improvement | 🏆 Top 30 rank |

---

## 🔗 REFERENCES

- [Session 95 Findings](../SESSION_95_CONTINUATION.md)
- [Runner Inventory](../RUNNER_INVENTORY.md)
- [FP8 Blockscale v1 (failed)](../amd-moe-mxfp4/submission_blockscale_g1u1.py)
- [COORDINATION_HUB](./COORDINATION_HUB.md)
- [SHARED_DISCOVERIES](./SHARED_DISCOVERIES.md)

---

**Next Update:** T+30 minutes with v2 implementation complete
