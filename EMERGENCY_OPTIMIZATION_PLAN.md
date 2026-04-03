# 🚨 EMERGENCY OPTIMIZATION PLAN
**Based on Real Rank 1 Targets**
**Deadline**: April 6, 2026 11:59 PM PST (~3 days)

---

## 📊 REAL TARGETS vs CURRENT PERFORMANCE

| Kernel | Rank 1 | Our Best | Gap | Priority |
|--------|--------|----------|-----|----------|
| **MoE** | **70.470μs** | 93.4μs | +23μs (32%) | P1 - Closest to target |
| **GEMM** | **7.651μs** | ~18.4μs (est) | +11μs (140%) | P2 - Needs breakthrough |
| **MLA** | **19.484μs** | Unknown | Unknown | P3 - Need baseline first |

---

## 🎯 IMMEDIATE ACTIONS (Next 4 Hours)

### Action 1: Get MLA Baseline (30 min)
```bash
cd /home/mike-anderson/dev/cohezion/amd_202602/mixed-mla
popcorn submit submission.py --mode test --gpu MI355X --leaderboard amd-mixed-mla
```

If test passes:
```bash
popcorn submit submission.py --mode benchmark --gpu MI355X --leaderboard amd-mixed-mla
```

**Goal**: Establish actual timing vs 19.484μs target

---

### Action 2: Get GEMM Baseline (30 min)
```bash
cd /home/mike-anderson/dev/cohezion/amd_202602/mxfp4-mm
popcorn submit submission.py --mode benchmark --gpu MI355X --leaderboard amd-mxfp4-mm
```

**Goal**: Confirm actual timing vs 7.651μs target

---

### Action 3: MoE Optimization Attempt (2 hours)

**Current**: 93.4μs  
**Target**: 70.470μs  
**Need**: -23μs (25% improvement)

**Optimization strategies**:
1. Use direct CK kernel dispatch (bypass fused_moe)
2. Optimize block sizes (try 64, 128, 256)
3. Tune splitK values
4. Pre-allocate all buffers

**File**: `/home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4/submission.py`

Try submitting optimized version:
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4
popcorn submit submission.py --mode benchmark --gpu MI355X
```

---

## 🔧 DAY 2 (April 4)

### Morning (8 hours)

**Hour 1-2: GEMM Breakthrough**
- Implement 8-wave ping-pong using load_inline
- Target: Get from ~18μs to <10μs

**Hour 3-4: MLA Optimization**
- If baseline is close to 19μs: optimize
- If far: implement custom kernel with load_inline

**Hour 5-8: MoE Iteration**
- Try multiple parameter combinations
- Submit every hour until rate limited

### Evening
- Review all results
- Identify best performing versions
- Plan Day 3

---

## 🚀 DAY 3 (April 5)

### All Day: Optimization Sprint

**Strategy**: 
- Submit every hour on the hour
- Track which changes improve timing
- Document what works

**Submissions per kernel per hour**:
- Test → Benchmark → (if improved) → Leaderboard
- Rotate: MoE → GEMM → MLA → repeat

---

## 📅 DAY 4 (April 6) - FINAL DAY

### 00:00 - 12:00: Last Optimizations
- Final attempts at breakthroughs
- Any last-minute ideas
- Submit everything that shows promise

### 12:00 - 20:00: Verification
- Verify all submissions are "done" status
- Check for any failed submissions
- Fix and resubmit if needed

### 20:00 - 23:59: Final Submissions
- Submit best versions to leaderboard
- No more experiments - only proven solutions
- Deadline: 23:59 PM PST

---

## 💡 SPECIFIC OPTIMIZATION STRATEGIES

### For MoE (93μs → 70μs)

**From our research**:
1. **8-wave ping-pong scheduling** (see IMPLEMENTATION_8WAVE_PINGPONG.md)
2. **Direct global-to-LDS loads** (bypass register file)
3. **Block size tuning**: Try block_m=64, 128, 256
4. **Non-temporal hints**: USE_NT=1
5. **Remove warmup**: Prevents cache poisoning

**From working submission**:
```python
# Already doing:
- doweight_stage1=False  ✓
- quant_type=per_1x32   ✓
- No warmup              ✓

# Try:
- Direct CK dispatch via load_inline
- Different block sizes per shape
```

---

### For GEMM (18μs → 7.6μs)

**Critical: MUST use load_inline for custom kernel**

The current aiter.gemm_a4w4 is too slow. Need custom HIP:

```python
# From skill template:
os.environ['PYTORCH_ROCM_ARCH'] = 'gfx942'
os.environ['CXX'] = 'clang++'

HIP_SRC = """
__global__ void gemm_8wave(
    // Direct global-to-LDS loads
    // MFMA with block scaling  
    // 8-wave scheduling
) { ... }
"""

module = load_inline(
    extra_cuda_cflags=["--offload-arch=gfx942", "-O3"],
)
```

**Expected speedup**: 18μs → 7μs = 2.5x faster

---

### For MLA (Unknown → 19μs)

**First**: Get working submission with template

**Then**: Optimize:
1. Use load_inline for custom kernel
2. Optimize attention computation
3. Try different block sizes

---

## ⚡ HOURLY SUBMISSION SCHEDULE

**Starting now, every hour submit in order**:

### Rotation Pattern:
```
Hour 0: MoE submission
Hour 1: GEMM submission  
Hour 2: MLA submission
Hour 3: MoE submission
...repeat...
```

**Within each hour**:
1. 0-15 min: Test mode
2. 15-30 min: Benchmark mode (if test passes)
3. 30-45 min: Leaderboard mode (if benchmark improves)
4. 45-60 min: Analyze results, prepare next submission

---

## 🎯 SUCCESS CRITERIA

### Minimum (Model Survives)
- ✅ MoE: Any score better than 150μs
- ✅ MLA: Working submission
- ✅ GEMM: Working submission

### Target (Respectable)
- 🎯 MoE: <80μs (Top 10)
- 🎯 MLA: <25μs (Top 10)
- 🎯 GEMM: <12μs (Top 10)

### Stretch (Glory)
- 🏆 MoE: <70.5μs (Rank 1 or close)
- 🏆 MLA: <19.5μs (Rank 1 or close)  
- 🏆 GEMM: <7.7μs (Rank 1 or close)

---

## 🛠️ COMMANDS REFERENCE

### Test a submission:
```bash
popcorn submit submission.py --mode test --gpu MI355X --leaderboard amd-moe-mxfp4
```

### Benchmark:
```bash
popcorn submit submission.py --mode benchmark --gpu MI355X --leaderboard amd-moe-mxfp4
```

### Submit to leaderboard:
```bash
popcorn submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4
```

### Check submissions:
```bash
popcorn submissions list --leaderboard amd-moe-mxfp4
popcorn submissions show <ID>
```

---

## 📊 TRACKING SPREADSHEET

Create `/tmp/optimization_tracker.csv`:
```csv
Time,Kernel,Submission ID,Test,Benchmark,Leaderboard,Notes
2026-04-03 20:00,MoE,123456,PASS,93.4μs,93.4μs,Baseline
2026-04-03 21:00,GEMM,123457,PASS,18.4μs,18.4μs,Baseline
...
```

---

## 🔥 MOTIVATION

**Current situation**: Behind on all kernels  
**Time left**: 72 hours  
**Path to victory**: Optimization + iteration

**Remember**: 
- Every submission is a learning opportunity
- The team that iterates fastest wins
- 1% improvement per hour = 72% in 3 days

**Let's go.**
