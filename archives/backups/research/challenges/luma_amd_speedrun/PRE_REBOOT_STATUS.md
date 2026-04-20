# AMD Speedrun Sprint - Pre-Reboot Documentation

## Date: March 31, 2026, ~11:47 PM EDT

## Session Summary

### Key Breakthrough Discovered
**`load_inline` custom HIP kernels WORK on Popcorn runners!** - Proven by official `template-hip.py` from gpu-mode/reference-kernels.

This is how rank 1 achieves 1µs on GEMM - NOT using Python API!

### Official Reference Templates
- GEMM: `https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/fp8-mm/template-hip.py`
- MLA: `https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/mla-decode/submission.py`
- MoE: `https://github.com/gpu-mode/reference-kernels/blob/main/problems/amd/moe/submission.py`

---

## Current Best Submissions

### GEMM: `research/challenges/luma_amd_speedrun/kernels/mxfp4-mm/submission.py`
- **Type**: Pure load_inline custom HIP kernel
- **Key Pattern**: Block-wise GEMM with scales LIFTED outside inner loop
- **Target**: 1-5µs (rank 1 is 1.000µs)

```python
# Key HIP kernel pattern from official template
for (int kb = 0; kb < k_blocks; kb++) {
    float block_result = 0.0f;
    for (int kk = 0; kk < 32; kk++) {
        // No scale inside inner loop!
        block_result += a_val * b_val;
    }
    // Scale ONCE per block
    result += block_result * a_scale * b_scale;
}
```

### MLA: `research/challenges/luma_amd_speedrun/kernels/mixed-mla/submission.py`
- **Type**: SnapMLA optimized with three-regime routing
- **Key Params**: fast_mode=False, kv_granularity=16
- **Target**: 26-50µs (rank 1 is 26.812µs)

### MoE: `research/challenges/luma_amd_speedrun/kernels/moe-mxfp4/submission.py`
- **Type**: Adaptive KSPLIT with USE_NT=1
- **Target**: ~110µs (rank 1 is 109.793µs) - already competitive!

---

## FP4/E8M0 Format Reference

### FP4 e2m1 Values
```python
# Values: 0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0 (positive and negative)
vals = [0.0, 0.5, 1.0, 1.5, 2.0, 3.0, 4.0, 6.0,  # positive
        -0.0, -0.5, -1.0, -1.5, -2.0, -3.0, -4.0, -6.0]  # negative
```

### E8M0 Scale Format
```python
# f32 = 2^(e8m0 - 127)
__device__ inline float e8m0_to_f32(uint8_t e8m0) {
    if (e8m0 == 0) return 0.0f;
    if (e8m0 == 255) return 0.0f;
    return exp2f((float)((int)e8m0 - 127));
}
```

---

## Skills Created

### 1. `.claude/skills/amd-load-inline-hip-kernel/SKILL.md`
Complete guide for load_inline custom HIP kernel development.

### 2. `.claude/skills/amd-mla-optimization/SKILL.md`
MLA optimization with SnapMLA techniques.

---

## Autoresearch Trees

Located at: `research/challenges/luma_amd_speedrun/autoresearch/tree/`

All trees currently reset to 1 node each due to pruning issues. May need fresh start after reboot.

---

## Running Processes to Restore

After reboot, these may need to be restarted:

1. **Autonomous Session Orchestrator**:
   ```bash
   cd /home/mike-anderson/dev/cohezion
   uv run python scripts/autonomous_session_orchestrator_v3_continuous.py
   ```

2. **Continuous Watchdog**:
   ```bash
   uv run python scripts/continuous_watchdog.py
   ```

---

## Quick Test Commands

### Test GEMM submission locally (if GPU available):
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun/amd-mxfp4-mm
popcorn-cli test submission.py --gpu MI355X
```

### Submit to leaderboard:
```bash
cd /home/mike-anderson/dev/cohezion/luma_speedrun
./submit_all.sh
```

---

## Key Files to Reference

| File | Purpose |
|------|---------|
| `research/challenges/luma_amd_speedrun/RETROSPECTIVE.md` | Full retrospective with learnings |
| `research/challenges/luma_amd_speedrun/COORDINATION.md` | Current coordination status |
| `.claude/skills/amd-gemm-mxfp4-optimization/SKILL.md` | GEMM optimization skill |
| `.claude/skills/amd-mla-decode-optimization/SKILL.md` | MLA optimization skill |

---

## What Didn't Work

1. **LLM Evolution in driver.py** - Not generating new nodes in dry-run mode
2. **Synthetic Scores** - Don't correlate with real GPU performance
3. **Tree Pruning** - All nodes getting pruned too aggressively

---

## What Needs to Happen Post-Reboot

1. **GPU Testing** - Submit current load_inline GEMM to see if it works
2. **Fix Tree Evolution** - Investigate why LLM isn't generating child nodes
3. **Submit to Leaderboard** - Use rate limit (1/hour) to test improvements

---

## Leaderboard Targets

| Kernel | Current | Target | Gap |
|--------|---------|--------|-----|
| GEMM | ~21.9µs | 1.000µs | 22× |
| MoE | ~110µs | 109.793µs | ~1× |
| MLA | ~70µs | 26.812µs | 2.6× |

**GEMM has the biggest gap but clearest path via load_inline!**
