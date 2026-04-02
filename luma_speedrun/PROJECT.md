# Luma AMD Speedrun - Project Management

## Overview
**Deadline**: April 6, 2026 11:59 PM PST  
**Worktree**: `.worktrees/luma-breakthrough-sprint`  
**Branch**: `luma-breakthrough-sprint`

## Current Status

| Kernel | Our Best | Leader | Gap | Priority | Status |
|--------|----------|--------|-----|----------|--------|
| **GEMM** | 22.8µs | 4.3µs | 5.3× | 🔴 Critical | 📝 Active |
| **MLA** | 69.7µs | 33.0µs | 2.1× | 🟡 High | 📝 Active |
| **MoE** | 154.2µs | 109.8µs | 1.4× | 🟢 Medium | 📝 Active |

## Team Structure

### Conductors
- **Claude (Primary)**: `luma_speedrun/` - load_inline HIP kernels, K-Search
- **Autoresearch**: `research/challenges/luma_amd_speedrun/` - Parameter sweeps
- **OpenCode/Kimi**: `hip-kernels-kimi-k2.5/` - rocWMMA variants
- **MoE-Specialist**: `research/.../kernels/moe-mxfp4/` - KSPLIT tuning

### RL Integration
- Optimizer: `optimizer/` - Search tree + CDNA4 knowledge
- State Tracking: `optimizer/state.py` - Node management
- Planner: `optimizer/planner.py` - Action selection prompts

## Sprint Board

### TODO
- [ ] Fix coherence/toFixed errors in all dashboard components
- [ ] Run GEMM through RL optimizer (target: <5µs)
- [ ] Run MLA through RL optimizer (target: <35µs)
- [ ] Run MoE through RL optimizer (target: <110µs)
- [ ] Integrate RL policy with submission pipeline
- [ ] Validate all submissions on Popcorn runners

### In Progress
- [ ] Coherence error fixes across worktrees
- [ ] RL infrastructure setup for kernel optimization

### Done
- [x] Initial load_inline GEMM submission
- [x] AMD MFMA intrinsic research
- [x] K-Search tree framework

## Technical Strategy

### GEMM Optimization Path
```
Current: 22.8µs (Python + load_inline)
Target:   4.3µs (Single fused kernel)
Gap:      5.3×

RL Actions:
1. Fused quant+GEMM (single kernel)
2. 8-wave ping-pong scheduling
3. LDS swizzle XOR remap
4. Direct global→LDS transfers
5. MFMA tile tuning (16x16x128)
6. Double buffering
```

### MLA Optimization Path
```
Current: 69.7µs (3 Python dispatches)
Target:  33.0µs (single kernel)
Gap:     2.1×

RL Actions:
1. Fuse stage1+reduce
2. FP8 quantization inline
3. Direct ASM dispatch
4. Persistent kernel
```

### MoE Optimization Path
```
Current: 154.2µs (fused_moe API)
Target:  109.8µs (direct CK)
Gap:     1.4×

RL Actions:
1. LDS bridge (intermediates in shared memory)
2. Direct CK .co dispatch
3. Adaptive KSPLIT per shape
4. Expert mask optimization
```

## File Locations

### Submissions
- `luma_speedrun/amd-mxfp4-mm/submission.py` (GEMM)
- `luma_speedrun/amd-mixed-mla/submission.py` (MLA)
- `luma_speedrun/amd-moe-mxfp4/submission.py` (MoE)

### RL Infrastructure
- `optimizer/state.py` - Search tree state management
- `optimizer/planner.py` - CDNA4 prompt templates
- `luma_speedrun/autoresearch/driver.py` - K-Search driver

### Documentation
- `luma_speedrun/CONSOLIDATED_STATE.md` - Current status
- `luma_speedrun/QUICK_REFERENCE.md` - Command cheat sheet
- `research/challenges/luma_amd_speedrun/RETROSPECTIVE.md` - Learnings

## Daily Workflow

```bash
# Switch to worktree
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint

# Run RL optimizer cycle
python optimizer/runner.py --kernel gemm --cycles 10

# Test submission
popcorn-cli submit luma_speedrun/amd-mxfp4-mm/submission.py \
    --mode test --gpu MI355X --leaderboard amd-fp8-gemm

# Update project status
make luma-status
```

## Metrics

### Cycle Time
- RL evaluation: ~10 min per kernel
- Popcorn submission: ~2 min (test) / ~5 min (benchmark)
- Daily capacity: ~50 trials

### Success Criteria
- GEMM: <5µs (top 10)
- MLA: <35µs (top 10)
- MoE: <110µs (match leader)

## Risk Register

| Risk | Impact | Mitigation |
|------|--------|------------|
| Popcorn runner unavailable | High | Batch submissions overnight |
| CK kernel compilation fails | Medium | Fallback to load_inline |
| RL policy stagnation | Medium | R-Zero mutation injection |
| Time deadline | High | Parallel workstreams |

## Commits

1. `fix: coherence toFixed errors in dashboard`
2. `feat: integrate RL optimizer with GEMM`
3. `feat: integrate RL optimizer with MLA`
4. `feat: integrate RL optimizer with MoE`
5. `docs: update PROJECT.md with results`
