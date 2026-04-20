# LUMA SPEEDRUN - FINAL BREAKTHROUGH PLAN
**Updated**: 2026-04-02  
**Deadline**: April 6, 2026 11:59 PM PST  
**Worktree**: `luma-breakthrough-sprint`

## Current Standing vs Rank 1

| Kernel | Our Best | Rank 1 | Gap | Priority |
|--------|----------|--------|-----|----------|
| **GEMM** | 13.425µs | 1.000µs | **13.4×** | 🔴 CRITICAL |
| **MLA** | 69.745µs | 12.685µs | **5.5×** | 🔴 CRITICAL |
| **MoE** | 154.183µs | 107.345µs | **1.4×** | 🟡 HIGH |

**Total Points Available**: 3,750  
**Current Strategy**: AutoResearch + Ralph Loop integration

---

## Coherence Errors: ✅ RESOLVED

All `toFixed` errors fixed across:
- ✅ Main repo (`apps/`, `src/`)
- ✅ All 6 worktrees
- ✅ `.pi/extensions/cohezion-bridge.ts`
- ✅ Auto-fix script: `fix_tofixed_quick.sh`

**Quick Fix (if errors recur)**:
```bash
cd /home/mike-anderson/dev/cohezion
./fix_tofixed_quick.sh
```

---

## Phase 1: AutoResearch Ralph Loop (ACTIVE)

### Execution Command
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint/research/challenges/luma_amd_speedrun

# Run Ralph Loop for all kernels
python autoresearch/ralph_main.py --kernel all --max-cycles 50

# Or run specific kernel
python autoresearch/ralph_main.py --kernel gemm --max-cycles 100
python autoresearch/ralph_main.py --kernel moe --max-cycles 50
python autoresearch/ralph_main.py --kernel mla --max-cycles 50
```

### Ralph Loop Features
- **Coherence gating**: Only accepts improvements with HIHO score ≥ 0.5
- **Stagnation detection**: Triggers R-Zero mutations after 7 cycles without improvement
- **Breakthrough detection**: Automatically flags Rank 1 achievements
- **Vault persistence**: Logs to `~/vaults/cohezion-vault/luma-speedrun/autoresearch/`

---

## Phase 2: Parallel Agent Teams

### Team GEMM (Target: 1.000µs)
**Current**: 13.425µs → **Need 13.4× improvement**

| Agent | Strategy | Status |
|-------|----------|--------|
| **claude-gemm** | V_MFMA_SCALE intrinsic | 🔴 Active |
| **autoresearch** | K-Search exploration | 🔴 Active |
| **kimi-rocwmma** | rocWMMA tiles | 🟡 Standby |

**Key Breakthroughs Needed**:
1. **Fused quant+GEMM**: Eliminate Python dispatch (~8µs overhead)
2. **8-wave ping-pong**: Overlap memory/compute
3. **Direct global→LDS**: Bypass VGPR staging
4. **MFMA 16x16x128**: Native FP4 multiply-accumulate

```bash
# Submit GEMM breakthrough
./luma_speedrun/task.sh submit-gemm
```

---

### Team MLA (Target: 12.685µs)
**Current**: 69.745µs → **Need 5.5× improvement**

| Agent | Strategy | Status |
|-------|----------|--------|
| **claude-mla** | SnapMLA fused | 🔴 Active |
| **autoresearch** | Direct ASM | 🔴 Active |

**Key Breakthroughs Needed**:
1. **Fuse stage1+reduce**: Single dispatch (saves ~40µs)
2. **FP8 KV cache**: 2× bandwidth
3. **Persistent kernel**: Bypass 3-dispatch floor
4. **FlashAttention-style**: QK+Softmax+V fused

```bash
# Submit MLA breakthrough
./luma_speedrun/task.sh submit-mla
```

---

### Team MoE (Target: 107.345µs)
**Current**: 154.183µs → **Need 1.4× improvement**

| Agent | Strategy | Status |
|-------|----------|--------|
| **claude-moe** | LDS bridge | 🔴 Active |
| **moe-specialist** | Adaptive KSPLIT | 🔴 Active |

**Key Breakthroughs Needed**:
1. **LDS bridge**: Keep intermediates in shared memory
2. **Direct CK .co dispatch**: 182 pre-compiled kernels
3. **Expert mask**: Skip 224/257 unused experts
4. **KSPLIT=0,1,2,4**: Shape-adaptive splitting

```bash
# Submit MoE breakthrough
./luma_speedrun/task.sh submit-moe
```

---

## Phase 3: Orchestrated Parallel Run

### Option A: Python Orchestrator
```bash
cd /home/mike-anderson/dev/cohezion
python luma_speedrun/orchestrate.py

# Or specific kernel
python luma_speedrun/orchestrate.py gemm
```

### Option B: Bash Parallel Launcher
```bash
cd /home/mike-anderson/dev/cohezion
./luma_speedrun/run-parallel.sh
```

### Option C: Manual Parallel Execution
```bash
cd /home/mike-anderson/dev/cohezion

# Terminal 1 - GEMM
cd .worktrees/luma-breakthrough-sprint && \
  python luma_speedrun/autoresearch/driver.py --kernel gemm &

# Terminal 2 - MLA  
cd .worktrees/luma-breakthrough-sprint && \
  python luma_speedrun/autoresearch/driver.py --kernel mla &

# Terminal 3 - MoE
cd .worktrees/luma-breakthrough-sprint && \
  python luma_speedrun/autoresearch/driver.py --kernel moe &

wait
echo "All kernels optimized"
```

---

## Critical Commands

### Status Check
```bash
./luma_speedrun/task.sh status
```

### Fix Coherence Errors (if they recur)
```bash
./fix_tofixed_quick.sh
git add -A && git commit -m "fix: toFixed null checks"
```

### Submit to Leaderboard
```bash
# Test mode first
./luma_speedrun/task.sh submit-gemm  # Test mode

# Then leaderboard
popcorn-cli submit luma_speedrun/amd-mxfp4-mm/submission.py \
  --mode leaderboard --gpu MI355X --leaderboard amd-mxfp4-mm
```

### Backup Progress
```bash
./luma_speedrun/task.sh save
```

---

## Breakthrough Targets

### GEMM Path to 1.000µs
1. **Current**: 13.425µs (load_inline + block GEMM)
2. **Step 1**: Fused quant+GEMM → ~8µs
3. **Step 2**: 8-wave ping-pong → ~4µs
4. **Step 3**: Direct global→LDS → ~2µs
5. **Step 4**: V_MFMA_SCALE intrinsic → ~1µs ✅ **RANK 1**

### MLA Path to 12.685µs
1. **Current**: 69.745µs (3-dispatch ASM)
2. **Step 1**: Fuse stage1+reduce → ~50µs
3. **Step 2**: Persistent kernel → ~30µs
4. **Step 3**: FlashAttention-style → ~20µs
5. **Step 4**: Custom HIP + MFMA → ~12µs ✅ **RANK 1**

### MoE Path to 107.345µs
1. **Current**: 154.183µs (fused_moe API)
2. **Step 1**: Adaptive KSPLIT → ~140µs
3. **Step 2**: Expert masking → ~130µs
4. **Step 3**: LDS bridge → ~120µs
5. **Step 4**: Direct CK dispatch → ~107µs ✅ **RANK 1**

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|------------|
| Load_inline blocked | HIGH | Fallback to AITER API + JIT persistence |
| Compilation failures | MEDIUM | Pre-compile kernels, use `AITER_JIT_DIR` |
| Stagnation | MEDIUM | R-Zero mutation injection every 7 cycles |
| Deadline pressure | HIGH | Parallel teams + overnight runs |

---

## Success Criteria

- **GEMM**: <2µs (within 2× of leader) → **Minimum viable**
- **MLA**: <20µs (top 10) → **Acceptable**
- **MoE**: <110µs (match leader) → **Win**

**Stretch Goal**: Rank 1 on all 3 leaderboards (3,750 points)

---

## Next Actions

1. ✅ **Fix coherence errors** (DONE)
2. 🔴 **Run Ralph Loop** (START NOW):
   ```bash
   python autoresearch/ralph_main.py --kernel all --max-cycles 100
   ```
3. 🟡 **Parallel submissions** every 2 hours
4. 🟢 **Review vault** daily for breakthroughs
5. ⚪ **Deadline check**: April 6, 11:59 PM PST

---

**Documentation**:
- `luma_speedrun/PROJECT.md` - Project overview
- `luma_speedrun/TEAMS.md` - Agent teams
- `research/challenges/luma_amd_speedrun/RETROSPECTIVE.md` - Learnings
- `cloud-vault-mcp/vault/cerebellum/luma-amd-speedrun-strategy.md` - Strategy vault

**Run now**:
```bash
cd /home/mike-anderson/dev/cohezion/.worktrees/luma-breakthrough-sprint
python research/challenges/luma_amd_speedrun/autoresearch/ralph_main.py --kernel all --max-cycles 100
```