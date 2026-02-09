# Phase 5B Streamlined Delivery Plan

**Objective**: Get Phase 5B into production with minimal delay while maintaining quality

**Current State**: 4 of 5 components ready, SessionPersistence missing, 4 redis test failures

---

## Recommended Path: INCREMENTAL MERGE

### Stage 1: Immediate (Next 30 minutes)

**Goal**: Fix redis test API mismatches, commit, ready for merge

**Tasks**:
1. Fix redis_cache test file API mismatches (4 tests)
   - Change `_ensure_redis_connection()` → `_init_redis_connection()`
   - Remove `async` from `get_stats()` calls in sync tests
   - Estimated: 15 minutes

2. Run redis tests to confirm fixes
   - Estimated: 5 minutes

3. Commit fixes to feature/token-efficiency-5b
   - Message: "fix: Resolve redis cache test API mismatches for Phase 5B merge"
   - Estimated: 5 minutes

### Stage 2: PR & Code Review (1-2 hours)

**Goal**: Create PR from feature/token-efficiency-5b → main

**Actions**:
- devops-lead: Create PR with 4 core components (SkillConsensusVoter, CostAwareRouter, GlobalMetricsAggregator, Integration tests + RedisSemanticCache)
- architect: Lead code review
- qa-lead: Final regression testing
- Result: Merge to main

**Deliverables in PR**:
- ✅ 4 components (822 tests)
- ✅ Full backward compatibility
- ✅ Production-ready code

### Stage 3: Phase 5B.2 Parallel Track (Can start immediately after Stage 1)

**Goal**: Implement SessionPersistence + other Phase 5B.2 features in parallel

**Team**:
- session-specialist: Implement SessionPersistence (4 hours)
- architect: Plan Cost Opt Phase 3-4 (2 hours)
- New: adversarial-tester: Security/chaos testing (3-4 hours)

**Deliverables**:
- SessionPersistence (vault + JSONL fallback)
- Cost Opt Phase 2 architecture docs
- Security audit of Phase 5B components
- Chaos testing results

**Timeline**: Runs in parallel with PR review (1-2 hours), then submits Phase 5B.2 branch

---

## Alternative Path: COMPLETE BEFORE MERGE

If SessionPersistence is critical:

### Single Comprehensive Merge

**Timeline**: +4-5 hours vs. incremental approach

**Advantage**: Cleaner git history (1 PR with all 5 components)
**Disadvantage**: Delays Phase 5B entering production

**Tasks**:
1. Implement SessionPersistence (4 hours)
2. Fix redis tests (30 min)
3. Run full test suite (10 min)
4. Create PR with all 5 components (10 min)
5. Code review (1-2 hours)
6. Merge to main

---

## Execution Plan (Recommended: Incremental)

### IMMEDIATE (Right Now - 30 min)
```
Phase 5B Fix (30 min):
├─ redis test fix (15 min)
├─ test verification (5 min)
└─ commit (5 min)
└─ git push

Phase 5B.2 Start (Parallel - 4 hours):
├─ session-specialist: SessionPersistence implementation
├─ architect: Cost Opt Phase 2 planning
└─ adversarial-tester: Security/chaos testing
```

### NEXT STEP (1-2 hours)
```
Phase 5B.1 PR:
├─ Create PR (feature/token-efficiency-5b → main)
├─ Code review (architect lead)
├─ Final testing (qa-lead)
└─ Merge to main
└─ Deploy to production
```

### FOLLOW-UP (After PR approved, 4 hours)
```
Phase 5B.2 Merge:
├─ SessionPersistence implementation complete
├─ Create PR (Phase 5B.2 branch → main)
├─ Code review
└─ Merge to main
```

---

## Resource Allocation

### Available Specialists
- architect: PR code review + Phase 5B.2 planning
- redis-specialist: Assist with test fixes (optional)
- consensus-engineer: Available for Phase 5B.2
- cost-optimizer: Available for Phase 5B.2
- dashboard-engineer: Available for Phase 5B.2
- session-specialist: Implement SessionPersistence
- qa-lead: Final regression testing
- devops-lead: Create PR + manage merge gate

### New Specialist Needed
- adversarial-tester: Security/chaos testing Phase 5B

---

## Success Criteria

### Phase 5B.1 (4 components)
- ✅ Redis test fixes applied
- ✅ PR created and approved
- ✅ 822+ tests passing
- ✅ Zero regressions
- ✅ Merged to main
- ✅ Deployed to production

### Phase 5B.2 (SessionPersistence + security)
- ✅ SessionPersistence implementation complete
- ✅ 34+ tests passing for SessionPersistence
- ✅ Security audit completed
- ✅ Chaos testing validated
- ✅ PR created and approved
- ✅ Merged to main

---

## Risk Assessment

**Low Risk** (Incremental approach):
- 4 components already tested extensively (822 tests)
- Backward compatible
- SessionPersistence doesn't block other features
- Can ship Phase 5B.1 independently

**Medium Risk** (Complete before merge):
- 4-5 hour delay to get Phase 5B into production
- SessionPersistence implementation untested on main
- Tighter timeline for PR review

---

## Decision Required

**Choose one**:

**A. Incremental (Recommended)**
- Fix + commit (30 min)
- Create Phase 5B.1 PR (1-2 hours)
- Start Phase 5B.2 in parallel (4 hours)
- Total to Phase 5B.1 production: 2 hours
- Total to all Phase 5B: 6 hours

**B. Complete Before Merge**
- Implement SessionPersistence (4 hours)
- Fix + commit (30 min)
- Create comprehensive PR (10 min)
- Code review (1-2 hours)
- Merge to production
- Total to all Phase 5B: 6-7 hours

**RECOMMENDATION: A (Incremental)**
- Get Phase 5B.1 (4 proven components) to production faster
- No risk to shipping 822+ tested components
- SessionPersistence follows in Phase 5B.2
- Parallel work maximizes velocity

---

Generated: 2026-02-09 (Session 40 Strategy)
