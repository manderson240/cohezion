# Session Handoff Document
# Luma AMD Speedrun - Multi-Session Coordination

**Last Updated**: 2026-03-18 16:05 UTC  
**Current Session**: opencode-hip-kernels-kimi-k2-5  
**Mode**: Build Mode (Active)  
**Next Handoff**: As needed when tokens run out

---

## ⚠️ CRITICAL - READ FIRST

This document ensures seamless continuity when switching between sessions. **Update this file after every major action.**

---

## 1. Current State Snapshot

### Active Work
- **Phase**: Day 1 of 12 (March 18)
- **Strategy**: Specialist Agent Pattern (not multi-session)
- **Architecture**: Coordinator → Specialist Agents → Results
- **Status**: 🟢 Agents spawned, submissions in progress

### In-Progress Items
- [x] Spawn GEMM specialist agent - ✅ Created submission
- [x] Spawn MLA specialist agent - ✅ Created submission  
- [x] Spawn MoE specialist agent - ✅ Created submission
- [x] Spawn Results monitoring agent - ✅ Active
- [x] Begin baseline submissions - ✅ Multiple submissions staged
- [ ] Await benchmark results from agents
- [ ] Select best performers per kernel

### Blockers
- None currently

---

## 2. Architecture Overview

### Why Specialist Agents?
- **Single auth source** - No coordination needed across sessions
- **Parallel execution** - All agents work simultaneously
- **Shared context** - All agents see same files/data
- **No external dependencies** - Everything in one workspace

### Workflow Pattern
```
Coordinator (You + Current Session)
    ├─► Delegate to GEMM Agent ───────► Optimize GEMM
    ├─► Delegate to MLA Agent ────────► Optimize MLA
    ├─► Delegate to MoE Agent ───────► Optimize MoE
    └─► Results Agent monitors ───────► Track all submissions
         ↓
    Review results
         ↓
    Select best performers
         ↓
    Final leaderboard submission
```

### Key Principle
**Benchmark results decide, not bureaucracy.** Let the numbers speak.

---

## 3. File Locations

### Competition Workspace (Primary)
```
/home/mike-anderson/dev/cohezion/research/challenges/luma_amd_speedrun/
├── COORDINATION.md                    ⭐ Session coordination hub
├── SESSION_HANDOFF.md                 ⭐ This file - state capture
├── AGENT_ORCHESTRATION.md             ⭐ How to spawn/manage agents
├── DAILY_CHECKLIST.md                 ⭐ Day-by-day execution plan
├── SYNC_STATUS.md                     ⭐ Reference alignment status
├── README.md                          ⭐ Quick start guide
├── kernels/
│   ├── mixed-mla/
│   │   ├── submission.py              ← Current submission
│   │   ├── reference.py               ← Official reference (ALIGNED)
│   │   ├── reference.py.backup        ← Previous version
│   │   ├── task.py                    ← Problem definition
│   │   └── staging/                   ⭐ Session staging area
│   │       ├── submission.opencode.k2-5.20260318_150205.py
│   │       └── submission.opencode.k2-5.latest.py
│   ├── mxfp4-mm/                      ← Same structure
│   └── moe-mxfp4/                     ← Same structure
└── submission_logs/                   ← Historical Popcorn results
```

### Official References (Read-Only)
```
/home/mike-anderson/dev/cohezion/luma_speedrun/
├── amd-mixed-mla/reference_implementation.py
├── amd-mxfp4-mm/reference_implementation.py
├── amd-moe-mxfp4/reference_implementation.py
└── [Public] AMD x GPU MODE - E2E Model Speedrun Rules and T&C.md
```

### Our Workspace (Active Development)
```
/home/mike-anderson/dev/cohezion/hip-kernels-kimi-k2-5/
├── submissions/                       ← Our 29 submission variants
├── submissions/luma_official/         ← Official reference copies
├── src/                               ← HIP kernel sources
├── build/                             ← Compilation outputs
├── POPCORN_CLI_GUIDE.md              ← CLI usage guide
└── ... other development files
```

---

## 4. Auth Status

### Popcorn CLI Authentication
- **Status**: ✅ Working
- **CLI ID**: e3b9a2f1 (last 8 chars)
- **Config Location**: `~/.popcorn.yaml`
- **Owner**: This session maintains auth
- **Last Verified**: 2026-03-18 15:00 UTC

### ⚠️ CRITICAL - Auth Management Rules
1. **This session is Auth Owner** - Do not change
2. **Other sessions NEVER run** `register` or `reregister`
3. **If auth breaks**: Notify this session, we'll fix it
4. **All sessions share** the same `~/.popcorn.yaml`

### Auth Recovery Procedure
If auth error occurs:
1. Check `~/.popcorn.yaml` exists and has valid CLI ID
2. If invalid, run: `popcorn-cli reregister github`
3. Update this file with new CLI ID (last 8 chars)
4. Announce to other sessions: "Auth restored, continue submitting"

---

## 5. Active Submissions

### GEMM (amd-mxfp4-mm)
- **Current Best**: ~23µs (gemm_a4w4)
- **Location**: `kernels/mxfp4-mm/staging/submission.opencode.k2-5.latest.py`
- **Status**: ✅ Test passed, needs optimization
- **Target**: ≤10µs
- **Gap**: 2.3x

### MLA (amd-mixed-mla)
- **Current Best**: ~67µs (reference)
- **Location**: `kernels/mixed-mla/staging/submission.opencode.k2-5.latest.py`
- **Status**: ✅ Test passed, needs optimization
- **Target**: ≤20µs
- **Gap**: 3.4x

### MoE (amd-moe-mxfp4)
- **Current Best**: TBD
- **Location**: Not yet staged
- **Status**: ⏳ Not started
- **Target**: ≤145µs
- **Gap**: Unknown

---

## 6. Next Steps (Immediate Actions)

### For New Session Taking Over:
1. **Read COORDINATION.md** - Current status and session registry
2. **Read AGENT_ORCHESTRATION.md** - How to spawn specialist agents
3. **Check staging/ directories** - See what submissions exist
4. **Spawn agents** as documented
5. **Update this file** after every major action

### Immediate Actions (Priority Order):
```markdown
1. [ ] Spawn GEMM Specialist Agent
   - Input: kernels/mxfp4-mm/reference.py
   - Goal: Optimize to <15µs (first milestone)
   - Timeline: Day 1-2

2. [ ] Spawn MLA Specialist Agent
   - Input: kernels/mixed-mla/reference.py
   - Goal: Optimize to <40µs (first milestone)
   - Timeline: Day 1-2

3. [ ] Spawn MoE Specialist Agent
   - Input: kernels/moe-mxfp4/reference.py
   - Goal: Get baseline measurement
   - Timeline: Day 1-2

4. [ ] Spawn Results Monitoring Agent
   - Track all submissions
   - Update COORDINATION.md
   - Timeline: Continuous

5. [ ] Test Mode Submissions
   - Verify all kernels pass correctness
   - Document results
   - Timeline: Day 1

6. [ ] Benchmark Mode Submissions
   - Get performance baselines
   - Document results
   - Timeline: Day 1-2
```

---

## 7. How to Continue (Handoff Procedure)

### ⚠️ MANDATORY: Update After Every Submission

**After EVERY submission to Popcorn CLI, you MUST:**

1. **Update Section 9 (Submission Log)** immediately
   - Add new row with date, time, kernel, mode, result
   - Include any error messages or notable outcomes
   - Update "Current" performance numbers if improved

2. **Update Section 1 (Current State)**
   - Mark completed tasks
   - Update "In-Progress Items"
   - Note any blockers

3. **Update "Last Updated" timestamp** at top of file

4. **Save the file** before doing anything else

### When Switching to New Session:

1. **Save this file** (SESSION_HANDOFF.md)
   - Commit or ensure it's written to disk

2. **Update timestamp and session name**
   - "Last Updated": [Current timestamp]
   - "Current Session": [New session name]

3. **Read these files in order**:
   - `SESSION_HANDOFF.md` (this file) - Current state
   - `COORDINATION.md` - Session coordination
   - `AGENT_ORCHESTRATION.md` - How to spawn agents
   - `DAILY_CHECKLIST.md` - Day-by-day plan

4. **Check critical directories**:
   - `kernels/*/staging/` - See staged submissions
   - `submission_logs/` - Recent Popcorn results

5. **Spawn agents** as needed per AGENT_ORCHESTRATION.md

6. **Update this file** after every major action

---

## 8. Critical Notes

### NEVER Do These:
- ❌ Run `popcorn-cli reregister` without checking Auth Status first
- ❌ Overwrite `kernels/*/submission.py` without checking staging/
- ❌ Delete `~/.popcorn.yaml` or backups
- ❌ Submit to leaderboard without test mode verification
- ❌ Ignore coordination documentation

### ALWAYS Do These:
- ✅ Update this file after major actions
- ✅ Check Auth Status before submitting
- ✅ Stage submissions before promoting to main
- ✅ Document learnings in vault
- ✅ Communicate blockers immediately

### Emergency Contacts:
- **Discord**: #amd-competition channel
- **Popcorn CLI Issues**: https://github.com/gpu-mode/popcorn-cli
- **Competition Info**: https://www.gpumode.com/

---

## 9. Overall Plan & Submission Tracking

### Competition Overview
- **Competition**: AMD x GPU MODE E2E Model Speedrun
- **Phase**: Qualifiers (March 6 - April 6, 2026)
- **Deadline**: March 30, 2026 (11 days remaining)
- **Strategy**: Specialist Agent Pattern
- **Current Day**: Day 1 (March 18)

### Target Performance

| Kernel | Current | Target | Leader | Gap | Status |
|--------|---------|--------|--------|-----|--------|
| **GEMM** | ~23µs | ≤10µs | 9.671µs | 2.3x | 🔄 Optimizing |
| **MLA** | ~67µs | ≤20µs | 4.335µs | 3.4x | 🔄 Optimizing |
| **MoE** | TBD | ≤145µs | 145.177µs | Unknown | ⏳ Not Started |

### Submission Log (Update After Every Submission)

| Date | Time | Kernel | Session | Mode | Result | Notes |
|------|------|--------|---------|------|--------|-------|
| 2026-03-18 | 15:02 | GEMM | opencode-k2-5 | Test | ✅ Passed | Baseline established |
| 2026-03-18 | 15:02 | MLA | opencode-k2-5 | Test | ✅ Passed | Reference working |
| 2026-03-18 | 15:45 | GEMM | Agent | Staging | ⏳ Pending | Multiple variants created |
| 2026-03-18 | 16:00 | MLA | Agent | Staging | ⏳ Pending | Custom HIP kernel created |
| 2026-03-18 | 15:45 | MoE | Agent | Staging | ⏳ Pending | Baseline submission created |
| 2026-03-18 | 16:15 | ALL | Coordinator | Fix | ✅ Fixed | Added missing GPU directives to 3 submissions |

### Phase Progress

**Phase 1: Days 1-4 (Baseline & Initial Optimization)**
- [x] Day 1: Documentation complete, references aligned
- [ ] Day 2: Agent spawning, baseline submissions
- [ ] Day 3: Initial optimization iterations
- [ ] Day 4: Phase 1 completion, best baselines selected

**Phase 2: Days 5-8 (Refinement)**
- [ ] Day 5-6: Advanced optimization techniques
- [ ] Day 7-8: Edge cases and robustness

**Phase 3: Days 9-12 (Final Push)**
- [ ] Day 9-10: Final optimization
- [ ] Day 11: Pre-submission validation
- [ ] Day 12: Leaderboard submission

### Next Submission Targets

1. **GEMM**: Target <20µs (from ~23µs)
   - Technique: Tile size optimization
   - ETA: Day 2

2. **MLA**: Target <50µs (from ~67µs)
   - Technique: FP8 format optimization
   - ETA: Day 2

3. **MoE**: Establish baseline
   - Technique: Reference implementation
   - ETA: Day 2

---

## 10. Session History

| Date | Session | Actions Taken | Status |
|------|---------|---------------|--------|
| 2026-03-18 09:00 | opencode-hip-k2-5 | Initial setup, coordination files | ✅ Complete |
| 2026-03-18 15:00 | opencode-hip-k2-5 | Aligned references with luma_speedrun/ | ✅ Complete |
| 2026-03-18 15:25 | opencode-hip-k2-5 | Created handoff documentation | ✅ Complete |
| 2026-03-18 15:40 | opencode-hip-k2-5 | Added submission tracking section | ✅ Complete |
| 2026-03-18 16:05 | opencode-hip-k2-5 | Spawned all 4 specialist agents | 🟢 ACTIVE |

---

## 11. Quick Reference

### Submission Commands
```bash
# Test mode (verify correctness)
popcorn-cli submit submission.py --gpu MI355X --mode test --no-tui

# Benchmark mode (get performance)
popcorn-cli submit submission.py --gpu MI355X --mode benchmark --no-tui

# Leaderboard mode (official)
popcorn-cli submit submission.py --gpu MI355X --mode leaderboard --no-tui
```

### Check Submissions
```bash
# List recent submissions
popcorn-cli submissions list --leaderboard amd-mixed-mla

# Check auth status
cat ~/.popcorn.yaml
```

### File Directives (in submission.py)
```python
#!POPCORN leaderboard amd-mixed-mla
#!POPCORN gpu MI355X
```

---

**Document Owner**: Multi-session coordination team  
**Next Review**: After every major submission or handoff  
**Status**: ACTIVE - Ready for specialist agent spawning

---

*End of SESSION_HANDOFF.md*
