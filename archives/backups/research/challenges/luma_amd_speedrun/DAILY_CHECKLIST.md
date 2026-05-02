# Daily Execution Checklist
# Luma AMD Speedrun - 12 Day Competition Timeline

**Competition**: AMD x GPU MODE E2E Model Speedrun  
**Phase**: Qualifiers (March 6 - April 6, 2026)  
**Deadline**: March 30, 2026 (11 days remaining)  
**Strategy**: Specialist Agent Pattern  
**Last Updated**: 2026-03-18 15:35 UTC  
**Current Day**: Day 1

---

## Overview

This document tracks day-by-day execution for the Luma AMD Speedrun competition using the specialist agent pattern.

### Timeline
- **Days 1-4**: Phase 1 - Baseline establishment and initial optimization
- **Days 5-8**: Phase 2 - Refinement and advanced techniques
- **Days 9-12**: Phase 3 - Final optimization and leaderboard submission

### Target Performance

| Kernel | Current | Target | Leader | Gap |
|--------|---------|--------|--------|-----|
| **GEMM** | ~23µs | ≤10µs | 9.671µs | 2.3x |
| **MLA** | ~67µs | ≤20µs | 4.335µs | 3.4x |
| **MoE** | TBD | ≤145µs | 145.177µs | Unknown |

---

## Phase 1: Days 1-4 (March 18-21)
**Goal**: Establish baselines, spawn agents, initial optimization

### Day 1 (March 18) - TODAY
**Status**: 🔄 In Progress  
**Focus**: Agent spawning and baseline establishment

#### Morning Tasks (09:00-12:00)
- [x] Align reference implementations with official luma_speedrun/
- [x] Create coordination documentation
- [x] Set up staging directories
- [ ] Spawn GEMM specialist agent
- [ ] Spawn MLA specialist agent
- [ ] Spawn MoE specialist agent
- [ ] Spawn Results monitoring agent

#### Afternoon Tasks (13:00-17:00)
- [ ] Agents begin optimization work
- [ ] Test mode submissions for all kernels
- [ ] Verify correctness passes
- [ ] Document initial results in COORDINATION.md

#### Evening Tasks (17:00-20:00)
- [ ] Review Day 1 submissions
- [ ] Update SESSION_HANDOFF.md
- [ ] Plan Day 2 priorities
- [ ] Check for auth issues

**Expected Outcomes**:
- All 4 agents spawned and working
- Baseline submissions staged
- Test mode passes for all kernels
- Initial benchmark results documented

---

### Day 2 (March 19)
**Status**: ⏳ Pending  
**Focus**: Benchmark mode and iteration

#### Tasks
- [ ] Review Day 1 results
- [ ] Benchmark mode submissions
- [ ] Agents iterate on optimizations
- [ ] Document performance improvements
- [ ] Update best results tracking

**Expected Outcomes**:
- Benchmark baselines established
- First optimization iterations complete
- Performance gaps identified

---

### Day 3 (March 20)
**Status**: ⏳ Pending  
**Focus**: Advanced optimization techniques

#### Tasks
- [ ] Continue optimization iterations
- [ ] Explore advanced techniques (tiling, vectorization)
- [ ] Document breakthroughs
- [ ] Update vault with learnings
- [ ] Compare results across agents

**Expected Outcomes**:
- Significant performance improvements
- Advanced techniques documented
- Clear leaders emerging per kernel

---

### Day 4 (March 21)
**Status**: ⏳ Pending  
**Focus**: Phase 1 completion and handoff

#### Tasks
- [ ] Finalize Phase 1 submissions
- [ ] Select best performer per kernel
- [ ] Document Phase 1 learnings
- [ ] Handoff to Phase 2 agents
- [ ] Update all coordination files

**Expected Outcomes**:
- Phase 1 complete
- Best baselines established
- Clear optimization paths identified
- Phase 2 ready to begin

---

## Phase 2: Days 5-8 (March 22-25)
**Goal**: Refine top performers, explore edge cases

### Day 5 (March 22)
**Status**: ⏳ Pending  
**Focus**: Phase 2 kickoff

#### Tasks
- [ ] Review Phase 1 results
- [ ] Spawn refinement agents for top performers
- [ ] Set Phase 2 targets (e.g., GEMM <15µs)
- [ ] Begin advanced optimization

---

### Day 6 (March 23)
**Status**: ⏳ Pending  
**Focus**: Deep optimization

#### Tasks
- [ ] Continue refinement
- [ ] Explore shape-specific optimizations
- [ ] Document tuning parameters
- [ ] Track progress vs targets

---

### Day 7 (March 24)
**Status**: ⏳ Pending  
**Focus**: Edge cases and robustness

#### Tasks
- [ ] Test edge cases
- [ ] Verify robustness across input sizes
- [ ] Document failure modes
- [ ] Prepare for final phase

---

### Day 8 (March 25)
**Status**: ⏳ Pending  
**Focus**: Phase 2 completion

#### Tasks
- [ ] Finalize Phase 2 optimizations
- [ ] Select best of Phase 2
- [ ] Compare Phase 1 vs Phase 2
- [ ] Document overall best approach

---

## Phase 3: Days 9-12 (March 26-30)
**Goal**: Final optimization and leaderboard submission

### Day 9 (March 26)
**Status**: ⏳ Pending  
**Focus**: Final optimization push

#### Tasks
- [ ] Review all previous results
- [ ] Identify final optimization opportunities
- [ ] Spawn final refinement agents
- [ ] Set final targets

---

### Day 10 (March 27)
**Status**: ⏳ Pending  
**Focus**: Pre-submission validation

#### Tasks
- [ ] Final test mode validations
- [ ] Final benchmark runs
- [ ] Document final results
- [ ] Prepare submission packages

---

### Day 11 (March 28)
**Status**: ⏳ Pending  
**Focus**: Submission preparation

#### Tasks
- [ ] Select final submissions
- [ ] Copy to main submission.py
- [ ] Final documentation
- [ ] Pre-submission review

---

### Day 12 (March 29-30)
**Status**: ⏳ Pending  
**Focus**: Leaderboard submission

#### Tasks
- [ ] Submit to leaderboard (test mode first)
- [ ] Verify submissions accepted
- [ ] Monitor rankings
- [ ] Document final results
- [ ] Celebrate completion!

**Deadline**: March 30, 2026 11:59 PM PST

---

## Daily Routine (Every Day)

### Morning (09:00)
- [ ] Check SESSION_HANDOFF.md for current state
- [ ] Review COORDINATION.md for updates
- [ ] Check auth status
- [ ] Review overnight results

### Midday (12:00)
- [ ] Check agent progress
- [ ] Review benchmark results
- [ ] Update coordination files
- [ ] Address any blockers

### Evening (17:00)
- [ ] Summarize day's progress
- [ ] Update SESSION_HANDOFF.md
- [ ] Plan next day priorities
- [ ] Check for auth issues

### End of Day (20:00)
- [ ] Final documentation update
- [ ] Ensure all files saved
- [ ] Prepare for next session if needed

---

## Critical Milestones

| Date | Milestone | Status |
|------|-----------|--------|
| Mar 18 | Day 1: Agents spawned, baselines established | 🔄 Current |
| Mar 21 | Phase 1 complete: Best baselines identified | ⏳ Pending |
| Mar 25 | Phase 2 complete: Optimizations done | ⏳ Pending |
| Mar 28 | Final submissions selected | ⏳ Pending |
| Mar 30 | **DEADLINE**: Leaderboard submission | ⏳ Pending |

---

## Success Criteria

### By Day 4 (Phase 1)
- [ ] All kernels have working submissions
- [ ] Test mode passes for all
- [ ] Benchmark baselines established
- [ ] Clear optimization paths identified

### By Day 8 (Phase 2)
- [ ] Significant performance improvements
- [ ] Advanced techniques documented
- [ ] Best performers selected
- [ ] Robustness verified

### By Day 12 (Phase 3)
- [ ] Final submissions submitted to leaderboard
- [ ] All submissions pass correctness
- [ ] Performance targets met or exceeded
- [ ] Documentation complete

---

## Risk Mitigation

### Auth Failure
- **Mitigation**: This session maintains auth, others never touch it
- **Recovery**: Re-register and announce to all agents

### Submission Failure
- **Mitigation**: Always test mode first
- **Recovery**: Iterate and resubmit

### Time Running Out
- **Mitigation**: Prioritize working submissions over perfect ones
- **Recovery**: Submit current best if deadline approaching

### Coordination Conflicts
- **Mitigation**: Clear documentation in SESSION_HANDOFF.md
- **Recovery**: Check current state before acting

---

## Quick Reference

### Check Current Status
```bash
# View handoff document
cat SESSION_HANDOFF.md

# View coordination
cat COORDINATION.md

# Check staged submissions
find kernels/*/staging/ -name "*.py" -type f

# Check auth
cat ~/.popcorn.yaml
```

### Update Status
```bash
# Edit handoff document
# Update timestamp and current session
# Document actions taken
```

### Spawn Agents
```
Task: Spawn {kernel} optimization agent
Prompt: Optimize {kernel} kernel...
```

---

**Document Owner**: Multi-session coordination team  
**Next Review**: End of each day  
**Status**: ACTIVE - Day 1 in progress

---

*End of DAILY_CHECKLIST.md*
