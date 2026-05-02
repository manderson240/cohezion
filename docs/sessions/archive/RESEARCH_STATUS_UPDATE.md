# RESEARCH STATUS UPDATE
**Time**: $(date)  
**Status**: Submissions timing out - need to retry

---

## 🚨 CURRENT STATUS

### Attempted Submissions (Both Failed/Timed Out)

**1. MLA Leaderboard Submission (22:52)**
- Status: ⚠️ **Hung/No output**
- File: `/tmp/mla_leaderboard_submit.log`
- Result: Only shows "Waiting for results..." with no timing data
- **Likely failed or timed out**

**2. GEMM Blockscale Test (22:55)**
- Status: ⚠️ **Hung at 45.87s**
- File: `/tmp/gemm_blockscale_test.log`
- Result: Benchmark started but never completed
- **Process died or connection dropped**

### Root Cause
- Network issues OR
- Popcorn service instability OR
- Timeout too short (used 60s timeout)

---

## ✅ GEMM BREAKTHROUGH RESEARCH (What We Found)

### Created: `submission_blockscale_tuned.py`

Based on historical research (`submission.gemm-specialist.blockscale_tuned.py`):

**Key Optimizations**:
1. ✅ **Direct `gemm_a4w4_blockscale` call** - bypasses unified API overhead
2. ✅ **Pre-allocated output tensor** - avoids allocation overhead
3. ✅ **splitK=0** - no K-splitting for most shapes (single kernel launch)
4. ✅ **Contiguous memory handling** - ensures proper memory layout

**Code Pattern** (from historical 13.425 µs):
```python
# Pre-allocate output
Out = torch.empty(m, n, dtype=torch.bfloat16, device="cuda")

# Direct blockscale call
C = aiter.gemm_a4w4_blockscale(
    A_q, B_shuffle, A_scale_sh, B_scale_sh,
    Out,      # Pre-allocated
    splitK=0, # Tuned parameter
)
```

**Current submission** (`submission.py`) uses:
```python
# Standard API
out_gemm = aiter.gemm_a4w4(A_q, B_shuffle, ...)
```

**Difference**: Blockscale path has less dispatch overhead!

---

## 🎯 NEXT STEPS

### Immediate (23:10 - In 15 Minutes)

**When MoE Rate Limit Clears**:
```bash
# 1. Submit MoE (PRIORITY #1)
cd amd-moe-mxfp4
popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui

# 2. Retry MLA (if MoE succeeds)
cd amd-mixed-mla
popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui

# 3. Test Blockscale GEMM (no timeout)
cd amd-mxfp4-mm
popcorn-cli submit submission_blockscale_tuned.py --mode benchmark --gpu MI355X --leaderboard amd-mxfp4-mm --no-tui
```

### Research for Tomorrow

**If Blockscale GEMM works**:
- Compare timing vs 18.4 µs baseline
- If better: Submit to leaderboard
- If not: Research splitK=1,2 tuning

**Research Paths** (from `inject_breakthrough_nodes.py`):
1. `gemm_a4w4_blockscale` with splitK tuning ✅ (testing now)
2. Direct CK dispatch via ctypes ⚠️ (blocked by stream sync error)
3. Custom Triton kernel (long shot)

---

## 💡 KEY INSIGHTS FROM RESEARCH

### From Historical Files

**Staging Winner (gemm-winner.py)**:
- Uses "ghost registry" / fingerprinting
- Pre-computes results based on seed detection
- **Not valid** for real competition (randomized seeds)

**Blockscale Tuned (blockscale_tuned.py)**:
- Real performance optimization
- Direct API calls
- splitK parameter tuning
- **Valid approach**

**Inject Breakthrough Nodes**:
- Current best: 13.425 µs documented
- Recommended: `gemm_a4w4_blockscale` + splitK tuning
- Status: "active" path

---

## 📊 COMPARISON

| Approach | Expected | Status |
|----------|----------|--------|
| Current `gemm_a4w4` | 18.4 µs | Tested, slower than historical |
| `gemm_a4w4_blockscale` + splitK=0 | ??? | Created, needs testing |
| Historical best | 13.425 µs | Documented, need to replicate |
| Rank 1 | 1.000 µs | Need breakthrough kernel |

---

## 🚨 CRITICAL TIMELINE

```
23:10 - Rate limit clears (MoE available)
      - Retry MLA submission
      - Test GEMM blockscale variant
      
00:10 - If successful, all 3 have baselines
      - Continue optimization overnight

04/03 - Day 2: Implement advanced techniques
      - 8-wave ping-pong (from HipKittens)
      - Direct global-to-LDS loads
      - MFMA inline assembly

04/06 - Competition ends
```

---

## ✅ FILES CREATED/READY

1. ✅ `submission_blockscale_tuned.py` - Blockscale variant ready to test
2. ✅ `submission_hipkittens.py` - HipKittens MoE copied
3. ✅ Research docs (multiple)
4. ⏰ Standing by for 23:10 submissions

---

**Status**: Research complete. Created blockscale variant. Standing by for 23:10 execution window.
