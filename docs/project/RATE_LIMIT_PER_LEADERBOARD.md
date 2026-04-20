# RATE LIMIT IS PER-LEADERBOARD (You were right!)
**Time**: $(date)  
**Status**: Can submit to different leaderboards independently

---

## ✅ KEY INSIGHT (User Corrected Me)

**Rate limit: 1 submission per hour PER LEADERBOARD**

This means:
- amd-moe-mxfp4: Rate limited until ~23:10 ⏰
- amd-mxfp4-mm: Available NOW ✅
- amd-mixed-mla: Available NOW ✅

**We can submit to all 3 in parallel!**

---

## 🚨 IMMEDIATE ACTION

Since rate limit is per-leaderboard:

1. ✅ **Submit MLA NOW** (available immediately)
2. ✅ **Can submit GEMM now** (but shouldn't - today's is worse)
3. ⏰ **MoE still waiting** until 23:10

---

## 📋 EXECUTION PLAN (UPDATED)

### NOW (22:52) - Submit MLA
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-mixed-mla
popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-mixed-mla --no-tui
```

### 23:10 - Submit MoE (Still rate limited)
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/luma_speedrun/amd-moe-mxfp4
popcorn-cli submit submission.py --mode leaderboard --gpu MI355X --leaderboard amd-moe-mxfp4 --no-tui
```

### GEMM - Research before submitting
- Historical: 13.425 µs
- Today's: 18.4 µs (WORSE)
- **Don't submit yet** - find better approach first

---

## 🎯 SUBMITTING MLA NOW

**Command**: Submit to amd-mixed-mla immediately
**Expected**: Should go through (no rate limit on this leaderboard yet)
**Value**: Establish baseline timing

---

**Thank you for the correction - submitting MLA now.**
