# 🎯 PHASE 3 — TESTING & LEADERBOARD SPRINT

**Status:** Ready for Execution  
**Time Allocated:** 4 hours  
**Goal:** Test all 3 new submissions, iterate on failures, submit successes to leaderboard

---

## 📋 SUBMISSION INVENTORY

| Submission | Agent | Lines | Status | Next Step |
|------------|-------|-------|--------|-----------|
| `submission_fp8_blockscale_v2.py` | You (Kimi) | 348 | 🟡 Created | ➡️ TEST NOW |
| `submission_asm_decode_bypass.py` | Claude Code | 271 | ✅ Created | ➡️ TEST |
| `submission_mfma_128x128_v1.py` | Gemini CLI | 493 | ✅ Created | ➡️ TEST |

**Total New Code:** 1,112 lines across 3 kernels

---

## 🧪 TESTING PROTOCOL

### MoE FP8 Blockscale v2 (Priority P0)

```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-moe-mxfp4

# Test correctness
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py

# If pass, benchmark
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py

# If benchmark < 150µs, leaderboard
popcorn-cli submit --mode leaderboard --gpu MI355X \
  --leaderboard amd-moe-mxfp4 \
  submission_fp8_blockscale_v2.py
```

**Expected Issues:**
- Weight conversion correctness
- Scale tensor format
- Kernel API compatibility

**Fallback:** Iterate to v3 with fixes

---

### MLA ASM Decode Bypass (Priority P1)

```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-mixed-mla

# Test correctness
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mixed-mla \
  submission_asm_decode_bypass.py

# If pass, benchmark
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-mixed-mla \
  submission_asm_decode_bypass.py
```

**Strategy:** BF16-only tensors to trigger decode kernel

---

### GEMM MFMA 128×128 (Priority P1)

```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-mxfp4-mm

# Test correctness
popcorn-cli submit --mode test --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission_mfma_128x128_v1.py

# If pass, benchmark
popcorn-cli submit --mode benchmark --gpu MI355X \
  --leaderboard amd-mxfp4-mm \
  submission_mfma_128x128_v1.py
```

**Strategy:** 8-wave ping-pong with 128×128 tiles

---

## 🔄 ITERATION WORKFLOW

### If Test FAILS:
1. Analyze error message
2. Identify root cause (conversion, API, kernel compile)
3. Create v2.1, v2.2, etc. with fixes
4. Re-test until pass

### If Benchmark IMPROVES:
1. Compare to baseline (154µs MoE, 69µs MLA, 13µs GEMM)
2. If >5% improvement, submit to leaderboard immediately
3. Log results in `submissions/verified/`

### If Benchmark NO IMPROVEMENT:
1. Analyze profiling data
2. Identify bottlenecks
3. Try alternative approach
4. Consult cross-kernel patterns from Pi Agent

---

## 📊 SUCCESS CRITERIA

| Kernel | Current | Target | Status |
|--------|---------|--------|--------|
| MoE | 154µs | <100µs | 🟡 Testing v2 |
| MLA | 69µs | <40µs | 🟡 Ready to test |
| GEMM | 13.4µs | <8µs | 🟡 Ready to test |

---

## 🎯 IMMEDIATE ACTIONS

### Action 1: Test MoE v2 (YOU — RIGHT NOW)
Execute the test command above and report results.

### Action 2: Test MLA ASM (Parallel)
Launch test in background while MoE testing.

### Action 3: Test GEMM MFMA (Parallel)
Launch test in background while others running.

### Action 4: Pi Agent Monitoring
Continuous pattern extraction as submissions complete.

---

**Next Update:** Upon first test results (expected T+1 hour)
