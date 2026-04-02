# Luma Speedrun - Task Tracker

## Active Sprint

### Blockers 🚨
- [ ] **Coherence toFixed errors** - Breaking dashboard UI
  - File: `apps/webapp/src/components/LandingPage.tsx`
  - File: `apps/webapp/src/components/Universe/ManifoldCanvas.tsx`
  - File: `apps/webapp/src/components/Universe/HologramField.tsx`
  - File: `apps/morphospace-loom/src/App.tsx`
  - **Assignee**: Claude
  - **Priority**: P0 - Critical

### In Progress 🔄
- [ ] **RL Integration for GEMM kernel optimization**
  - Current: 22.8µs → Target: 4.3µs (5.3× gap)
  - Using: `optimizer/` + `luma_speedrun/autoresearch/`
  - **Assignee**: Autoresearch/RL
  - **Priority**: P0 - Critical

### TODO 📋
- [ ] **RL Integration for MLA kernel optimization**
  - Current: 69.7µs → Target: 33.0µs (2.1× gap)
  - Depends: GEMM RL pipeline validation
  - **Priority**: P1 - High

- [ ] **RL Integration for MoE kernel optimization**
  - Current: 154.2µs → Target: 109.8µs (1.4× gap)
  - **Priority**: P1 - High

- [ ] **Validate all submissions on Popcorn runners**
  - Run full benchmark suite
  - Verify correctness (rtol=1e-2)
  - **Priority**: P1 - High

### Completed ✅
- [x] Initial load_inline GEMM submission
- [x] AMD MFMA intrinsic research (V_MFMA_SCALE_F32_16X16X128_F8F6F4)
- [x] K-Search tree framework setup
- [x] CDNA4 knowledge base documentation
- [x] Worktree setup: `luma-breakthrough-sprint`

## Daily Standup

### 2025-04-02 (Today)
**Claude**:
- Fixed coherence toFixed errors in main worktree
- Setting up RL integration infrastructure
- Blockers: Need to validate RL pipeline before kernel optimization

**Autoresearch**:
- Ready to run RL cycles on GEMM
- Have 200+ experiments in K-Search tree
- Blockers: None

## Task Commands

```bash
# View status
./luma_speedrun/task.sh status

# Fix coherence errors
./luma_speedrun/task.sh fix-coherence
./luma_speedrun/task.sh commit "fix: coherence toFixed null checks"

# Run RL optimizer
./luma_speedrun/task.sh rl-run gemm 10
./luma_speedrun/task.sh rl-run mla 10
./luma_speedrun/task.sh rl-run moe 10

# Submit to leaderboard
./luma_speedrun/task.sh submit-gemm
./luma_speedrun/task.sh submit-mla
./luma_speedrun/task.sh submit-moe

# Sync worktree
./luma_speedrun/task.sh sync
```

## Definition of Done

### For Coherence Fixes:
- [ ] No `.toFixed()` calls without null checks
- [ ] All `(value ?? 0).toFixed(n)` patterns applied
- [ ] Dashboard renders without TypeError
- [ ] Committed to `luma-breakthrough-sprint` branch

### For RL Integration:
- [ ] Search tree initialized with CDNA4 knowledge
- [ ] Action selection working (SELECT → SYNTHESIZE → TEST → UPDATE)
- [ ] First successful kernel variant generated
- [ ] Benchmark results logged to SurrealDB
- [ ] Performance improved over baseline

### For Submission:
- [ ] Test mode passes (correctness)
- [ ] Benchmark mode shows improvement
- [ ] Leaderboard submission succeeds
- [ ] Result documented in `CONSOLIDATED_STATE.md`

## Risk Tracking

| Risk | Status | Mitigation |
|------|--------|------------|
| Time deadline (Apr 6) | 🟡 Watch | Parallel streams, overnight runs |
| Popcorn runner failures | 🟢 OK | Retry logic, batch submissions |
| RL policy not converging | 🟡 Watch | R-Zero mutations, manual override |
| Coherence errors blocking UI | 🔴 Alert | In progress - P0 |

## Resources

- **Project**: `luma_speedrun/PROJECT.md`
- **Status**: `luma_speedrun/CONSOLIDATED_STATE.md`
- **Reference**: `luma_speedrun/QUICK_REFERENCE.md`
- **Worktree**: `.worktrees/luma-breakthrough-sprint`
- **Branch**: `luma-breakthrough-sprint`

## Team Contacts

- **Primary**: manderson240@gmail.com
- **K-Search**: `luma_speedrun/autoresearch/driver.py`
- **RL Optimizer**: `optimizer/state.py`, `optimizer/planner.py`