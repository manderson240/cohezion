---
title: "G1 Queue Management - Optimization Recommendations"
date: 2026-03-15
status: in-progress
tags: [infinity, gamma, gpu-optimization]
aspect: thinker
---

# G1 Queue Management - Optimization Recommendations

## Current Status (as of 03:21 UTC)
- **Queue Status**: Healthy (0/3 active, 3 slots available)
- **Current Window**: Pre-off-peak (2h 39m until optimal window)
- **Next Optimal Window**: 06:00 UTC today

## Optimization Recommendations

### 1. Time-Based Scheduling
**Priority: HIGH**
- **Optimal Window**: 06:00-12:00 UTC (off-peak)
  - 40% better throughput vs peak hours
  - Lower server load = faster evaluation
  - Reduced timeout risk
- **Avoid**: 14:00-20:00 UTC (peak hours)
  - Higher queue times
  - Increased timeout probability

### 2. Pipeline Strategy
**Priority: HIGH**
Implement 3-stage pipeline for each kernel:
1. **Test Mode** (Priority 1): Validate correctness first
2. **Benchmark Mode** (Priority 2): Measure performance if test passes
3. **Leaderboard Mode** (Priority 3): Submit only if benchmark is competitive

**Benefits**:
- Prevents failed leaderboard submissions
- Saves quota on obvious failures
- Allows iterative improvement

### 3. Concurrent Submission Management
**Priority: MEDIUM**
- **Limit**: 3 concurrent submissions maximum
- **Strategy**: Fill all 3 slots during off-peak
- **Monitoring**: Check `ps aux | grep popcorn-cli` every 5 minutes

### 4. Retry Logic
**Priority: MEDIUM**
- **Transient Failures**: Retry after 60s delay
- **Max Attempts**: 3 retries per job
- **Backoff**: Linear (60s, 120s, 180s)
- **Permanent Failures**: Log and move to failed queue

### 5. Leaderboard-Specific Optimizations

#### MoE MXFP4 (`luma-amd-speedrun-moe`)
- **Key Parameters**: `doweight_stage1=False`, `AITER_KSPLIT=4` for sparse
- **Expected Time**: ~50-100ms for typical shapes
- **Submission Priority**: HIGH (Team Alpha focus)

#### MLA Decode (`luma-amd-speedrun-mla-decode`)
- **Key Parameters**: `fast_mode=False` (slower but correct on MI355X)
- **Expected Time**: ~20-50ms for small batches
- **Submission Priority**: MEDIUM

#### FP4 GEMM (`luma-amd-speedrun-fp4-gemm`)
- **Key Parameters**: All tensors as `torch.uint8`, B layout [N, K//2]
- **Expected Time**: ~10-30ms for typical shapes
- **Submission Priority**: MEDIUM

### 6. Queue Management Automation

**Recommended Cron Schedule** (if available):
```
# Check queue every 5 minutes during off-peak
*/5 6-12 * * * /path/to/g1/check_queue.py

# Process any pending submissions
0 6 * * * /path/to/g1/process_offpeak.py
```

### 7. Monitoring Checklist
- [ ] Check active processes: `ps aux | grep popcorn-cli`
- [ ] Review queue status: `cat queue/submission_queue.json`
- [ ] Check results: `cat results/result_tracker.json`
- [ ] Monitor disk space in logs/ directory
- [ ] Verify vault sync for result persistence

### 8. Emergency Procedures

**If Queue is Overloaded (>3 active)**:
1. Identify hung processes: `ps aux | grep popcorn-cli`
2. Kill stale processes: `kill -9 <PID>`
3. Reset queue state manually
4. Notify team lead

**If Submission Fails Repeatedly**:
1. Check kernel correctness locally first
2. Verify popcorn-cli version
3. Check network connectivity
4. Review logs in `logs/` directory

## Immediate Actions Required

1. **03:21 UTC - NOW**: Queue is ready, 3 slots available
2. **06:00 UTC**: Begin scheduled submissions (5 jobs queued)
3. **Monitor**: Check dashboard every 30 minutes during active window

## Success Metrics
- Target: 80%+ successful submissions
- Target: <5% timeout rate
- Target: Average queue time <10 minutes during off-peak


## Related
- [[performance_breakdown|Performance Breakdown]] (g2)
- [[handoff_g2_to_team|Handoff G2 To Team]] (g2)
- [[OPTIMIZATION_SUMMARY|Optimization Summary]] (g3)
