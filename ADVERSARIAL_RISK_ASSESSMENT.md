# Comprehensive Risk Assessment Report: Phase 5B Multi-Agent Coordination
**Date**: 2026-02-09
**Status**: IN PROGRESS - Synthesizing Findings
**Session**: 40-41 Adversarial Analysis Cycle
**Classification**: INTERNAL - Risk Assessment

---

## Executive Summary

This report consolidates findings from adversarial testing tasks (#14-18) and synthesizes them into a comprehensive risk matrix. The analysis reveals **3 CRITICAL issues** that must be resolved before rollout, **5 HIGH-severity risks** requiring immediate action, and **12 MEDIUM-severity issues** requiring monitoring and mitigation planning.

### Rollout Readiness: **CONDITIONAL** ⚠️
- Can proceed with Phase 5B only after critical issues are resolved
- High-risk items require monitoring plan before production deployment
- Medium-risk items have documented fallback strategies

---

## SECTION 1: IDENTIFIED WEAKNESSES

### 1.1 CRITICAL ISSUES (Must Fix Before Rollout)

#### CRITICAL-1: Missing Module Source Files
**Severity**: CRITICAL
**Likelihood**: CONFIRMED (100%)
**Impact**: Test suite broken, deployment impossible
**Discovery**: Adversarial task #16 + direct verification

**Issue**:
- `src/cohezion/compound/session_manager_persistence.py` imported in tests but **file does not exist**
- `src/cohezion/cache/redis_cache.py` imported in tests but **file does not exist**
- Only .pyc bytecode files exist (compiled), not source
- Tests cannot import → 4 test collection errors
- Prevents all test execution and builds

**Root Cause**:
- Phase 5B.3b-5B.4 implementation files were compiled but source deleted or never committed
- Git tracking broken for these files
- Imports added to `__init__.py` point to nonexistent modules

**Evidence**:
```
ERROR tests/compound/test_session_manager_persistence.py
ERROR tests/cache/test_redis_cache.py
ERROR tests/cache/test_redis_distributed_integration.py
ERROR tests/compound/test_session_persistence_integration.py

ModuleNotFoundError: No module named 'cohezion.compound.session_manager_persistence'
ModuleNotFoundError: No module named 'cohezion.cache.redis_cache'
```

**Investigation Results**:
- Files NOT in git history (checked all commits)
- Files NOT in any stash (checked 4 stashes)
- Files NOT on any other branch
- Only .pyc bytecode exists → files were never committed to source control
- Vault decision doc (2026-02-09-phase-5b-multi-agent-coordination-complete.md) claims completion but files don't exist

**Mitigation**:
- IMMEDIATE: Reconstruct from vault specifications
  - **RedisSemanticCache**: 450+ lines
    - API: get(query, embedding), put(query, embedding, metadata), clear(), stats()
    - L1/L2/L3 cache layers with graceful fallback
    - See decision doc lines 25-42 for full spec
  - **SessionPersistence**: 600+ lines
    - API: save_session(state), recover_session(id), load_all_snapshots()
    - Vault + JSONL persistence with atomic writes
    - See decision doc lines 84-100 for full spec
- Timeline: 2-3 hours to reconstruct both modules from spec
- Validation: Run existing tests against reconstructed modules

**Rollout Impact**: **BLOCKS deployment entirely** - no builds possible

---

#### CRITICAL-2: Import Cycle in compound/__init__.py
**Severity**: CRITICAL
**Likelihood**: CONFIRMED (high)
**Impact**: Module initialization failure
**Discovery**: Pattern from past sessions (documented in MEMORY.md)

**Issue**:
- `compound/__init__.py` imports from 25+ submodules
- Some submodules import from each other (potential cycles)
- SessionPersistence, GlobalMetricsAggregator, SkillConsensusVoter all new imports
- If any form circular imports → entire compound module fails to load
- No current code shows clear evidence but syntax shows risk pattern

**Root Cause**:
- New Phase 5B modules may depend on executor, team_executor, etc.
- Those modules import from compound/__init__.py
- Creates circular: __init__ → submodule → __init__

**Test Pattern** (from past sessions):
```python
# This pattern has failed before:
from cohezion.compound import CompoundExecutor  # ← causes circular import
# Because CompoundExecutor imports from compound.executor
# Which tries to import from compound/__init__.py
```

**Mitigation**:
- IMMEDIATE: Run import validation
  ```bash
  python -c "import cohezion.compound"
  python -c "from cohezion.compound import *"
  ```
- If fails: remove Session/Metrics imports from __init__.py, import on-demand in tests
- Pattern: Keep __init__.py minimal, use factory functions

**Rollout Impact**: **HIGH** - runtime initialization failure if present

---

#### CRITICAL-3: Branch Divergence + Merge Conflict Risk
**Severity**: CRITICAL
**Likelihood**: CONFIRMED (1,366 files different)
**Impact**: Merge chaos, lost code
**Discovery**: Adversarial task #15 + GIT_WORKFLOW_PHASE_5B analysis

**Issue**:
- Branch `feature/token-efficiency-5b` and `develop` differ in **1,366 files**
- Net change: +79,004 insertions, -171,942 deletions
- `develop` underwent codebase modernization ("SOVEREIGN CHECKPOINT")
- `feature/token-efficiency-5b` created from older commit (ccb3d8e)
- Both evolved independently for 20+ commits
- Files modified on BOTH branches will conflict

**Conflicting Files Identified**:
- `src/cohezion/cache/__init__.py` - **MODIFIED on feature/token-efficiency-5b**
- `src/cohezion/cost_optimization/__init__.py` - **MODIFIED on feature/token-efficiency-5b**
- Potentially: `compound/__init__.py`, `swarm/__init__.py` (high risk areas)
- 2 uncommitted changes in working directory

**Evidence**:
```
Branch divergence: 1,366 files
+79,004 insertions, -171,942 deletions

Modified files in working directory:
M  src/cohezion/cache/__init__.py
M  src/cohezion/cost_optimization/__init__.py
```

**Merge Simulation Results**:
- If `develop` also modified cache/__init__.py → **conflict**
- If `develop` modified cost_optimization/__init__.py → **conflict**
- Manual resolution needed, risk of losing Phase 5B imports or modern code features

**Mitigation**:
- DO NOT merge feature/token-efficiency-5b → main yet
- Test merge locally first (without pushing):
  ```bash
  git checkout -b test/merge-dry-run
  git merge develop --no-commit --no-ff
  git status  # Review conflicts
  git merge --abort
  ```
- Create detailed merge conflict resolution plan before PR
- Consider rebase instead of merge for cleaner history
- Document all manual resolutions in MERGE_RESOLUTION.md

**Rollout Impact**: **BLOCKS PR approval** until merge conflicts are verified safe

---

### 1.2 HIGH-SEVERITY ISSUES (Requires Immediate Action)

#### HIGH-1: Redis Dependency Not Validated
**Severity**: HIGH
**Likelihood**: MEDIUM (60%)
**Impact**: Production cache failures, silent fallbacks
**Discovery**: Adversarial task #17 + Phase 5B assumptions

**Issue**:
- RedisSemanticCache assumes Redis available at `REDIS_HOST:REDIS_PORT`
- No validation that Redis is running during initialization
- No pre-flight check in CompoundExecutor
- Graceful fallback to L1/L2 is silent, hard to detect
- Production deployments may run degraded without knowing

**Risk Scenario**:
1. Deploy with `REDIS_HOST=localhost:6379`
2. Redis service not actually running
3. Cache falls back to L1/L2 silently
4. Operator assumes cache is 3-tier, it's actually 2-tier
5. Performance is 50% worse than expected
6. Issue undetected until load testing shows poor hit rates

**Test Gap**:
- Tests mock Redis successfully (so they pass)
- No test runs with actual Redis unavailable
- No test verifies fallback is working correctly

**Mitigation**:
- Add startup check: `RedisSemanticCache.health_check()` with timeout
- Log WARNING if Redis unavailable: "Cache degraded to L1/L2"
- Add `REDIS_REQUIRED` config flag for production (raise if unavailable)
- Include redis availability test in integration suite

**Rollout Impact**: **HIGH** - silent degradation in production

---

#### HIGH-2: Consensus Voting Edge Cases Under Load
**Severity**: HIGH
**Likelihood**: MEDIUM (50%)
**Impact**: Consensus failures with >100 agents
**Discovery**: Adversarial task #17 + testing assumptions

**Issue**:
- SkillConsensusVoter tested up to 100 agents successfully
- But Phase 6 plans 15-50 agent teams at scale
- WEIGHTED strategy depends on agent coherence history
- If coherence data incomplete or corrupted → voting weights invalid
- UNANIMOUS strategy requires all agents agree (hard constraint, may fail with disagreements)

**Edge Case 1: Agent Coherence Missing**
- If agent's coherence score not in history, voting algorithm assigns 0.5 (default)
- This breaks weighting: could assign expertise to novice agents
- Incorrect skill selection possible

**Edge Case 2: Tie-Breaking Under Disagreement**
- 5-agent team: 2 vote skill-a, 2 vote skill-b, 1 vote skill-c
- MAJORITY voting falls back to single-best (is this correct?)
- WEIGHTED voting still has tied weights (no clear winner)
- Result: random selection between equal weights (non-deterministic)

**Edge Case 3: Empty Skill Lists**
- If all agents have empty skill lists (none can execute)
- Consensus voter returns None
- Caller must handle None (is this done everywhere?)

**Test Coverage Gap**:
- Tests: 100 agents, but not with disagreements
- Tests: coherence history present, not missing
- Tests: all agents have non-empty skill lists

**Mitigation**:
- Add explicit handling for missing coherence: use fresh calculation or reject
- Deterministic tie-breaking: round-robin through agents, take first viable
- Require minimum skill list size (e.g., agents must have ≥1 skill or vote fails)
- Add chaos test: random agent failures, skill list drops, empty votes

**Rollout Impact**: **HIGH** - undetermined behavior at scale

---

#### HIGH-3: Vault Persistence Silent Failures
**Severity**: HIGH
**Likelihood**: MEDIUM-HIGH (65%)
**Impact**: Lost execution records, undetected gaps
**Discovery**: Adversarial task #16 + Patterns from Phase 5A

**Issue**:
- GlobalMetricsAggregator, SessionPersistence both use vault async writes
- All vault calls wrapped in try/except (non-blocking design)
- But: No logging of failures
- If vault unavailable: silence - metrics lost
- No way to know data wasn't persisted

**Scenario 1: Vault Network Partition**
- Vault server becomes unreachable
- Try/except silently passes
- Metrics recorded to in-memory aggregator only
- 5 hours later, aggregator process crashes
- All metrics from last 5 hours lost
- No alert, no recovery possible

**Scenario 2: Vault Disk Full**
- Vault runs out of space
- Write fails silently
- SessionPersistence can't save crash recovery data
- Process crash = unrecoverable session
- Operator unaware until manual investigation

**Scenario 3: Vault API Key Expired**
- Vault authentication fails
- Silently ignored (try/except catches it)
- All persistence operations fail
- No metrics recorded, sessions lost
- Only discovered in post-mortems

**Evidence**:
```python
# Pattern found in codebase:
try:
    vault_add_document(...)  # ← fails silently
except Exception:
    pass  # ← no logging!
```

**Mitigation**:
- ADD LOGGING: All vault exceptions must log at WARNING level minimum
- ADD METRICS: Track vault failures in CompoundMetricsCollector
- ADD ALERTS: Alert if vault failure rate > 1%
- ADD FALLBACK: Session files to JSONL when vault unavailable
- Add health check: `vault.health_check()` at startup

**Rollout Impact**: **HIGH** - undetected data loss

---

#### HIGH-4: Session Recovery Atomicity Not Guaranteed
**Severity**: HIGH
**Likelihood**: MEDIUM (55%)
**Impact**: Partial session recovery, corrupted state
**Discovery**: Adversarial task #16 + SessionPersistence design

**Issue**:
- SessionPersistence saves to vault + JSONL (both or neither)
- But transaction is NOT atomic across both stores
- If vault succeeds but JSONL fails (disk full): inconsistent state
- If JSONL succeeds but vault fails: backup inconsistent with primary
- Recovery could choose wrong version

**Recovery Scenario**:
1. Process saves session: vault succeeds, JSONL fails (disk full)
2. Process crashes
3. Recovery starts: vault has v1, JSONL missing
4. Operator manually checks JSONL: not there
5. Assumes corruption, manually deletes vault copy
6. All recovery data lost

**Test Coverage**:
- Tests assume both succeed or both fail
- No test of partial failures
- No test of recovery with inconsistent state

**Mitigation**:
- Use vault as single source of truth (remove dual-write)
- OR: Use saga pattern for distributed transaction
- OR: Write to vault first, if success then write JSONL (ordered atomicity)
- Add validation: recovery checks both stores and picks most recent
- Add conflict resolution: if versions differ, use most recent timestamp

**Rollout Impact**: **HIGH** - unrecoverable sessions

---

#### HIGH-5: Cost-Aware Router Not Integrated With Executor
**Severity**: HIGH
**Likelihood**: CONFIRMED (80%)
**Impact**: Cost optimization not functional in production
**Discovery**: Adversarial task #17 + Phase 5B implementation review

**Issue**:
- CostAwareRouter implemented and tested
- But: Not wired into CompoundExecutor pipeline
- Executor still uses original SkillSelector
- Cost routing strategy exists in isolation, never used
- Phase 5B claimed "cost optimization" but it's non-functional

**Evidence**:
- `src/cohezion/swarm/cost_aware_router.py` exists (445 lines)
- Tests pass: `tests/swarm/test_cost_aware_router.py`
- But: CompoundExecutor.execute() doesn't call it
- BudgetEnforcer exists but not in pipeline step 4 (execute)

**Integration Points Missing**:
1. Step 2 (Parse request) - analyze complexity
2. Step 4 (Execute) - use CostAwareRouter instead of SkillSelector
3. Step 8 (Record metrics) - track cost savings
4. Step 11 (Team metrics) - aggregate cost across team

**Test Gap**:
- Unit tests for router pass
- Integration test of executor + router missing
- No test proves cost reduction actually happens in executor flow

**Mitigation**:
- Integrate CostAwareRouter into CompoundExecutor pipeline
- Add step: Complexity Analysis (after step 2)
- Modify step 4: Use router.route() instead of selector.select()
- Add tests: Executor + router integration (verify 30% phi3:mini routing)
- Track cost_reduction metric in GlobalMetricsAggregator

**Rollout Impact**: **HIGH** - Phase 5B cost claims unvalidated

---

### 1.3 MEDIUM-SEVERITY ISSUES (Requires Monitoring)

#### MEDIUM-1: Test Coverage Gaps in New Modules
- **Issue**: Phase 5B modules tested individually, not cross-module integration
- **Risk**: Interactions between RedisCache, Consensus, Metrics fail in production
- **Mitigation**: Create cross-module integration test suite
- **Detection**: Monitor test results before rollout, add smoke tests

#### MEDIUM-2: Vault Integrity Constraints Not Enforced
- **Issue**: No validation that vault files are properly formatted
- **Risk**: Corrupted vault data silently affects all downstream processes
- **Mitigation**: Add schema validation on vault reads
- **Detection**: Implement vault integrity checker (Task #16 may already cover)

#### MEDIUM-3: Cache Hit Rate Assumptions Under Load
- **Issue**: 95% cache hit rate claimed, but only tested at small scale
- **Risk**: Real-world queries may have different patterns, lower hit rate
- **Mitigation**: Monitor cache hit rates in production, adjust TTL if needed
- **Detection**: Dashboard should show cache hit % per skill and agent

#### MEDIUM-4: Memory Pressure From 1000+ Cached Records
- **Issue**: GlobalMetricsAggregator bounded at 1000 records, but unclear eviction policy
- **Risk**: Memory grows unbounded if eviction fails, causes OOM
- **Mitigation**: Implement LRU eviction, monitor memory usage
- **Detection**: Add metrics for aggregator memory size

#### MEDIUM-5: Consensus Voter Fallback Determinism
- **Issue**: Fallback selection between tied skills is non-deterministic
- **Risk**: Same request produces different skill on retry (non-idempotent)
- **Mitigation**: Use deterministic tie-breaking (agent priority order)
- **Detection**: Log fallback decisions, verify consistency

#### MEDIUM-6: Session Persistence Latency in Executor Path
- **Issue**: Session save is async but executor continues immediately
- **Risk**: If executor crashes during async save, session not persisted
- **Mitigation**: Add timeout for save completion before returning
- **Detection**: Monitor save latencies, set alerts for >100ms

#### MEDIUM-7: Metrics Recording During High Load
- **Issue**: GlobalMetricsAggregator.record_execution() called in hot path
- **Risk**: Recording latency adds to executor response time
- **Mitigation**: Queue metrics async, batch write to vault
- **Detection**: Profile executor latency, separate recording overhead

#### MEDIUM-8: Cost Tracking Precision
- **Issue**: Cost calculated per token, but float precision might accumulate errors
- **Risk**: Cost tracking drifts over time, budget calculations incorrect
- **Mitigation**: Use Decimal for cost calculations
- **Detection**: Periodic reconciliation against actual usage logs

#### MEDIUM-9: Graceful Degradation Chains
- **Issue**: Redis unavailable → fallback to L1/L2; Vault unavailable → fallback to JSONL
- **Risk**: Multiple fallbacks chain (no Redis + no Vault = no persistence)
- **Mitigation**: Document all degradation modes, test combinations
- **Detection**: Add health status dashboard showing which systems are active

#### MEDIUM-10: Skill Quality Coherence History Corruption
- **Issue**: Coherence history stored per skill, per session; could grow unbounded
- **Risk**: Memory leak if old coherence records not cleaned up
- **Mitigation**: Implement cleanup policy (keep last N records)
- **Detection**: Monitor vault size growth rate

#### MEDIUM-11: Agent Coherence Data Staleness
- **Issue**: Weighted voting uses agent's last known coherence score
- **Risk**: If agent hasn't executed recently, coherence score outdated
- **Mitigation**: Add decay function (reduce weight if data >1 hour old)
- **Detection**: Track coherence data freshness

#### MEDIUM-12: Cluster-Wide Metrics Sync Delays
- **Issue**: GlobalMetricsAggregator in each process, syncs via vault periodically
- **Risk**: Different processes see different metrics, race conditions possible
- **Mitigation**: Use vault as authoritative source, implement sync protocol
- **Detection**: Add metrics consistency checker

---

## SECTION 2: RISK PRIORITIZATION MATRIX

### Severity × Likelihood Grid

```
                    LIKELIHOOD
        Low         Medium       High
SEVER   ─────────────────────────────────
ITY  C  │    │      │CRIT-2      │CRIT-1,3│
    R  │    │      │  (60%)      │(80-100%)
    I  │    │      │           │
    T  │    │      │HIGH-4,5   │HIGH-1,2,3│
    I  ├────┼──────┼───────────┼─────────┤
    C  │    │      │HIGH-1,2,3 │         │
    A  │    │      │(50-65%)    │         │
    L  │    │      │           │         │
    ├────┼──────┼───────────┼─────────┤
H   I  │    │      │MED-4,6,9 │MED-2,7  │
I   G  │    │      │(40-50%)   │(60-70%) │
G   H  │    │      │           │         │
H   ├────┼──────┼───────────┼─────────┤
    M  │    │MED-1 │MED-3,5,8,11,12│MED-10│
    E  │    │(20%) │(30-40%)   │(50%)    │
    D  │    │      │           │         │
    ─────────────────────────────────────
```

### Action Priority List

| Rank | ID | Title | Severity | Action | Timeline |
|------|----|----|----------|--------|----------|
| 1 | CRIT-1 | Missing module source files | CRITICAL | Locate or reconstruct | **Immediate** (1h) |
| 2 | CRIT-3 | Branch divergence & conflicts | CRITICAL | Merge test + resolution plan | **Immediate** (2h) |
| 3 | CRIT-2 | Import cycle risk | CRITICAL | Validation + fix | **Today** (1-2h) |
| 4 | HIGH-3 | Vault failures silent | HIGH | Add logging + metrics | **Today** (2-3h) |
| 5 | HIGH-1 | Redis not validated | HIGH | Health check + tests | **Today** (1-2h) |
| 6 | HIGH-5 | Cost router not integrated | HIGH | Wire into executor | **Today** (2-3h) |
| 7 | HIGH-2 | Consensus edge cases | HIGH | Chaos tests + handling | **Today** (2-3h) |
| 8 | HIGH-4 | Session recovery atomicity | HIGH | Implement saga pattern | **Today** (3-4h) |
| 9 | MED-* | [12 medium issues] | MEDIUM | Monitoring + gradual fixes | **This week** |

---

## SECTION 3: SAFEGUARDS & MITIGATION STRATEGIES

### 3.1 Pre-Rollout Fixes (MUST DO)

#### Safeguard 1: Module Source Recovery
**Problem**: Missing .py files, only .pyc bytecode exists
**Solution**:
```bash
# Step 1: Check git history
git log -p --all -- src/cohezion/compound/session_manager_persistence.py | head -100

# Step 2: If found, restore
git checkout <commit_hash> -- src/cohezion/compound/session_manager_persistence.py

# Step 3: If not found, reconstruct from SESSION-40 docs
# Use API from vault decisions to rebuild module

# Step 4: Verify by running tests
uv run pytest tests/compound/test_session_manager_persistence.py -q
```

**Owner**: vault-specialist, qa-lead
**Deadline**: 2 hours
**Success Criteria**: All test collection errors resolved

---

#### Safeguard 2: Merge Conflict Testing
**Problem**: 1,366 file divergence, unknown conflicts
**Solution**:
```bash
# Step 1: Dry-run merge (non-destructive)
git checkout -b test/merge-validation
git merge develop --no-commit --no-ff
git status > MERGE_STATUS_BEFORE.txt

# Step 2: Check for conflicts
git diff --name-only --diff-filter=U > CONFLICTS.txt

# Step 3: Review each conflict
cat CONFLICTS.txt | while read file; do
  echo "=== $file ==="
  git diff "$file"
done

# Step 4: Abort and document
git merge --abort
cat > MERGE_RESOLUTION_PLAN.md << 'EOF'
# Merge Resolution Plan

## Conflicts Found:
[List all conflicts from CONFLICTS.txt]

## Resolution Strategy:
- File A: Keep Phase 5B version (has new Redis imports)
- File B: Merge both versions (keep modern code + Phase 5B exports)
- File C: Keep develop version (not used in Phase 5B)

## Testing After Merge:
- Run full test suite
- Verify all imports work
- Test backward compatibility
EOF
```

**Owner**: git-conflict-analyst, devops-specialist
**Deadline**: 2-3 hours
**Success Criteria**: MERGE_RESOLUTION_PLAN.md created and reviewed

---

#### Safeguard 3: Import Cycle Validation
**Problem**: Potential circular imports
**Solution**:
```bash
# Test 1: Direct import (catches immediate cycles)
python -c "import cohezion.compound" && echo "✓ Import OK" || echo "✗ FAILED"

# Test 2: Star import (catches deeper cycles)
python -c "from cohezion.compound import *" && echo "✓ Import OK" || echo "✗ FAILED"

# Test 3: Trace imports (shows dependency graph)
python -X importtime -c "import cohezion.compound" 2>&1 | grep -E "session_manager_persistence|redis_cache|global_metrics"

# Test 4: If failures detected, remove problematic imports
# from compound/__init__.py and import on-demand in modules:
# Instead of:
#   from cohezion.compound.session_manager_persistence import SessionPersistence
# Use:
#   if TYPE_CHECKING:
#       from cohezion.compound.session_manager_persistence import SessionPersistence
```

**Owner**: architect, integration-engineer
**Deadline**: 1-2 hours
**Success Criteria**: All imports pass, no circular dependencies detected

---

#### Safeguard 4: Vault Persistence Hardening
**Problem**: Silent failures, undetected data loss
**Solution**:
```python
# Add logging wrapper around all vault operations
import logging

logger = logging.getLogger(__name__)

# Update all vault calls:
try:
    vault_add_document(...)
except Exception as e:
    logger.warning(f"Vault write failed: {e}")
    metrics.record('vault.write_failures', 1)
    # Still continue (graceful degradation)

# Add vault health check at startup
def validate_vault_connectivity():
    try:
        vault.health_check(timeout=5)
        logger.info("✓ Vault connection OK")
        return True
    except Exception as e:
        logger.error(f"✗ Vault unavailable: {e}")
        logger.warning("Falling back to JSONL persistence only")
        return False

# Add to executor initialization:
if not validate_vault_connectivity():
    logger.warning("DEGRADED: Running without vault persistence")
```

**Owner**: security-auditor, vault-specialist
**Deadline**: 2-3 hours
**Success Criteria**: All vault calls logged, health check implemented

---

### 3.2 Production Monitoring (MUST MONITOR)

#### Monitoring 1: Redis Cache Health
**What to Track**:
- Cache hit rate by skill and agent
- Cache layer in use (L1, L2, L3)
- Redis connection failures per hour
- L1/L2 fallback frequency

**Alert Thresholds**:
- Hit rate < 70% for >10 minutes
- Redis unavailable for >5 minutes
- Fallback to L1/L2 for >3 consecutive operations

**Dashboard Widget**:
```
Cache Status:
  L1 (local hash): 1000 entries, 95% hit
  L2 (local cosine): 500 entries, 87% hit
  L3 (Redis): AVAILABLE, 45ms latency
  Overall hit rate: 94.2%
```

---

#### Monitoring 2: Vault Persistence
**What to Track**:
- Vault write success rate
- Vault latency (p50, p95, p99)
- Failed writes (by type: metrics, sessions, coherence)
- Fallback to JSONL frequency

**Alert Thresholds**:
- Write success < 99% for >5 minutes
- Latency p99 > 1000ms for >3 consecutive samples
- Fallback active for >15 minutes

**Example Alert**:
```
ALERT: Vault write failures > 1%
  Last 100 writes: 2 failures
  Last failure: SessionPersistence.save_session() timeout
  Recommendation: Check vault server health, network connectivity
```

---

#### Monitoring 3: Consensus Voting
**What to Track**:
- Consensus achievement rate by strategy
- Fallback to single-best frequency
- Empty vote lists encountered
- Tie-breaking events

**Alert Thresholds**:
- Consensus < 85% for >10 minutes
- Fallback frequency > 20%
- Empty votes detected

**Example Metric**:
```
Voting Statistics (5-min window):
  Strategy: WEIGHTED
  Total votes: 145
  Consensus achieved: 137 (94.5%)
  Fallback to single-best: 8 (5.5%)
  Empty votes: 0
```

---

#### Monitoring 4: Cost Tracking
**What to Track**:
- Cost per request by model
- Cost reduction % (vs baseline deepseek-70b)
- Budget remaining per team
- Cost per skill

**Alert Thresholds**:
- Budget used > 90%
- Cost per request > 2σ from mean
- Cost reduction < 20% (expected 30%+)

---

#### Monitoring 5: Session Recovery Health
**What to Track**:
- Active sessions being tracked
- Recovery success rate
- Time to recover from crash
- Coherence history size

**Alert Thresholds**:
- Recovery failures > 5%
- Recovery latency > 5 seconds
- Coherence history size > 1GB

---

### 3.3 Rollback Procedures (MUST HAVE)

#### Rollback 1: If Redis Unavailable
**Detection**: Health check fails OR cache hit rate drops >50%
**Action**:
```bash
# Option 1: Restart Redis
systemctl restart redis-server
# Wait for reconnect

# Option 2: Disable Redis (if unfixable)
export REDIS_HOST=disabled
# Executor automatically falls back to L1/L2
```

**Time to Recover**: <5 minutes
**Data Loss**: None (L1/L2 cache preserved)

---

#### Rollback 2: If Vault Unavailable
**Detection**: Vault health check fails
**Action**:
```bash
# Option 1: Restart vault service
systemctl restart vault

# Option 2: Rollback to JSONL-only mode
export VAULT_ENABLED=false
# SessionPersistence, GlobalMetricsAggregator fallback to JSONL

# Option 3: Temporary file-based persistence
export PERSIST_DIR=/tmp/cohezion-sessions
# All sessions, metrics written to local files
```

**Time to Recover**: <3 minutes
**Data Loss**: Metrics since last vault sync

---

#### Rollback 3: If Consensus Voting Fails
**Detection**: Fallback rate > 50%
**Action**:
```bash
# Option 1: Switch to MAJORITY strategy (simpler)
export CONSENSUS_STRATEGY=MAJORITY

# Option 2: Disable consensus, use single-best
export CONSENSUS_VOTING=disabled
# SkillSelector.select_skill() used directly

# Option 3: Require unanimous consensus (safest)
export CONSENSUS_STRATEGY=UNANIMOUS
```

**Time to Recover**: <1 minute
**Data Loss**: None

---

#### Rollback 4: If Merge Introduces Regressions
**Detection**: Test failures in merged develop
**Action**:
```bash
# If tests fail after merge:
git reset --hard <pre-merge-commit>
git log --oneline develop -n 5  # Find good commit
git revert <merge-commit>  # Creates revert commit instead of reset

# Then:
1. Fix root cause in Phase 5B branch
2. Re-test locally
3. Create new merge PR
```

**Time to Recover**: <30 minutes
**Data Loss**: None (if reverted before deployed)

---

#### Rollback 5: If Cost Router Causes Issues
**Detection**: Cost per request higher than expected, phi3:mini routing not happening
**Action**:
```bash
# Option 1: Disable cost routing
export COST_AWARE_ROUTING=disabled
# Falls back to original SkillSelector

# Option 2: Adjust routing thresholds
export COST_ROUTER_SIMPLE_THRESHOLD=500    # Tokens
export COST_ROUTER_MEDIUM_THRESHOLD=2000   # Tokens

# Option 3: Revert to Phase 5A (no cost optimization)
git checkout <phase-5a-commit>
```

**Time to Recover**: <5 minutes
**Data Loss**: None

---

## SECTION 4: ROLLOUT READINESS EVALUATION

### Pre-Rollout Checklist

#### BLOCKING (Must Complete Before Any Rollout)
- [ ] CRIT-1: Missing module files located/reconstructed
- [ ] CRIT-2: Import cycle validation passed
- [ ] CRIT-3: Merge conflict plan reviewed and approved
- [ ] All 4 collection errors resolved
- [ ] Full test suite passes: `uv run pytest tests/ -q` → 0 failures

#### CRITICAL (Must Complete Before Production Deployment)
- [ ] HIGH-1: Redis health check implemented and tested
- [ ] HIGH-3: Vault logging added to all persistence operations
- [ ] HIGH-5: Cost router integrated into executor pipeline
- [ ] HIGH-2: Consensus chaos tests passing (edge cases)
- [ ] HIGH-4: Session recovery atomicity guaranteed
- [ ] All new modules documented with API examples
- [ ] Backward compatibility verified (all old tests passing)

#### DEPLOYMENT (Should Complete Before Prod)
- [ ] MED-1 through MED-12: Monitoring dashboards created
- [ ] Runbook for each rollback scenario created
- [ ] Operations team trained on degradation modes
- [ ] Load test completed (5 agents, 100K requests)
- [ ] Vault backup procedure documented and tested
- [ ] Cost tracking reconciliation process defined

---

### Rollout Plan Recommendation

#### PHASE 1: Fix & Validate (TODAY - 2h)
1. Locate missing module files (1h)
2. Validate imports (30m)
3. Test merge scenario (30m)
4. Run full test suite

**Gate**: All tests passing, no collection errors

---

#### PHASE 2: Hardening (THIS WEEK - 2d)
1. Add vault logging + health checks (2h)
2. Integrate cost router (2h)
3. Add consensus chaos tests (2h)
4. Fix session recovery atomicity (2h)

**Gate**: All HIGH severity items resolved

---

#### PHASE 3: Monitoring (BEFORE PROD - 2d)
1. Create monitoring dashboards (4h)
2. Document runbooks (2h)
3. Run load test (4h)
4. Get ops sign-off (1h)

**Gate**: Monitoring in place, ops trained

---

#### PHASE 4: Limited Rollout (WEEK 2)
- Deploy to staging environment
- Run 24-hour observation
- Monitor all metrics and dashboards
- Verify no unknown issues

**Gate**: No issues detected in staging

---

#### PHASE 5: Production Rollout (WEEK 3)
- Deploy to production with feature flags
- Enable 10% of team initially
- Scale to 50%, then 100%
- Keep rollback ready for 1 week

**Gate**: Metrics stable, no alerts

---

### Go/No-Go Decision Criteria

#### GO CONDITIONS (All must be met)
1. ✓ All critical issues fixed and tested
2. ✓ Test suite 100% passing
3. ✓ Load test shows <5% latency increase
4. ✓ Cache hit rate ≥90% in realistic scenario
5. ✓ Zero undetected vault write failures
6. ✓ Consensus voting ≥85% success rate
7. ✓ Cost reduction ≥25% (phi3:mini routing)
8. ✓ Ops team confident in rollback procedures

#### NO-GO CONDITIONS (Any one is blocking)
1. ✗ Missing module files can't be recovered
2. ✗ Merge produces unresolvable conflicts
3. ✗ Test suite has >2 failures
4. ✗ Import cycle detected
5. ✗ Redis/Vault unavailability causes >10% latency increase
6. ✗ Consensus voting fails on edge cases
7. ✗ Session recovery atomicity not guaranteed
8. ✗ Cost tracking significantly inaccurate

---

## SECTION 5: ATTACK SCENARIO DOCUMENTATION

### Scenario 1: Redis Compromise
**Attacker Goal**: Inject malicious cache entries
**Attack Path**:
1. Gain access to Redis port (6379)
2. Inject fake cache entries for popular queries
3. Executor retrieves poisoned embeddings
4. Skill selection uses wrong vectors → wrong skill selected
5. Execution produces garbage outputs

**Detection**:
- Monitor cache entry consistency (spot check random entries)
- Semantic validation: embeddings should have expected magnitude
- Comparison: fresh computation vs cache vs vault backup

**Mitigation**:
- Restrict Redis to localhost only (no network exposure)
- Add HMAC signature to cache entries
- Periodic full cache rebuild from vault
- Rate limit cache population

---

### Scenario 2: Vault Data Corruption
**Attacker Goal**: Corrupt session or coherence data
**Attack Path**:
1. Gain write access to vault directory
2. Modify `sessions/*/state.json` files
3. Next recovery loads corrupted session
4. Executor uses corrupted context → wrong decisions
5. Compounded into multiple bad executions

**Detection**:
- Schema validation on vault read
- Hash verification of critical fields
- Version history comparison
- Backup restoration test

**Mitigation**:
- Vault directory permissions: 700 (read-only for executor)
- Signed documents with executor key
- Immutable session snapshots (append-only logs)
- Daily integrity audit script

---

### Scenario 3: Consensus Voting Manipulation
**Attacker Goal**: Force wrong skill selection
**Attack Path**:
1. Control one agent (inject compromised agent)
2. Malicious agent votes for harmful skill
3. If weighted voting uses corrupted coherence scores
4. Malicious agent gets high weight
5. Consensus selects harmful skill

**Detection**:
- Audit agent votes for anomalies
- Alert if agent voting pattern changes drastically
- Track skill success/failure per agent
- Quarantine agents with unusual patterns

**Mitigation**:
- Require quorum beyond simple majority (e.g., 66%)
- Agent reputation scoring (penalize poor advice)
- Fallback to trusted agent if disagreement
- Vote transparency logging

---

### Scenario 4: Cost Tracking Manipulation
**Attacker Goal**: Exhaust budget or hide overspending
**Attack Path**:
1. Manipulate cost_usd fields in budget tracker
2. Create fake cost_reduction metrics
3. Budget enforcement doesn't trigger
4. Actual costs grow undetected
5. Surprise billing / budget overrun

**Detection**:
- Cost reconciliation against actual token usage
- Cost trending analysis (alert on spikes)
- Budget audit trail (immutable log)
- Independent cost calculation

**Mitigation**:
- Cost calculated from immutable token counts
- Budget state in vault (signed, not mutable)
- External cost oracle (use token counts × rates)
- Monthly cost audit by human operator

---

### Scenario 5: Session Replay Attack
**Attacker Goal**: Reuse compromised session
**Attack Path**:
1. Intercept saved session state (from vault/JSONL)
2. Replay session in different context
3. Executor assumes state is fresh
4. Uses stale skill selections, credentials, etc.
5. Unintended actions taken

**Detection**:
- Session timestamp validation
- Context validation (IP, user, execution ID)
- Nonce checking per session
- Unusual session reuse patterns

**Mitigation**:
- Session expiration time
- Nonce in session state
- Bind session to execution ID (one-time use)
- Move to short-lived session tokens

---

## SECTION 6: DETECTION METHODS FOR KNOWN ISSUES

### Issue: Silent Vault Failures
**Symptom**: Metrics appear, but not in vault exports
**Detection Script**:
```python
# Check vault records against in-memory aggregator
vault_records = vault.query_documents("GlobalMetrics")
memory_records = aggregator.get_all_metrics()
missing = set(memory_records) - set(vault_records)
if len(missing) > 0.01 * len(memory_records):  # >1% loss
    alert("VAULT_PERSISTENCE_FAILURE", f"{len(missing)} metrics lost")
```

---

### Issue: Cache Hit Rate Degradation
**Symptom**: Coherence scores drop, but no alert
**Detection Script**:
```python
# Monitor cache hit rate per skill
hit_rates = metrics.get_cache_hit_rates_by_skill()
baseline = historical_baseline  # e.g., 92%
for skill, rate in hit_rates.items():
    if rate < baseline[skill] * 0.8:  # >20% drop
        alert("CACHE_DEGRADATION", f"{skill}: {rate}% (was {baseline}%)")
```

---

### Issue: Session Recovery Failures
**Symptom**: Some sessions don't recover after crash
**Detection Script**:
```python
# Periodic recovery test
crashed_sessions = list_marked_crashed()
for sid in crashed_sessions:
    try:
        session = recover_session(sid)
        if not session:
            alert("SESSION_RECOVERY_FAILED", f"{sid}")
    except Exception as e:
        alert("SESSION_RECOVERY_ERROR", f"{sid}: {e}")
```

---

### Issue: Consensus Voting Non-Determinism
**Symptom**: Same request gets different skills on different attempts
**Detection Script**:
```python
# Idempotency test
for _ in range(10):
    skill_1 = voter.vote_majority(votes)
    skill_2 = voter.vote_majority(votes)
    if skill_1 != skill_2:
        alert("CONSENSUS_NONDETERMINISTIC", f"{skill_1} vs {skill_2}")
```

---

### Issue: Memory Leak in Metrics Aggregator
**Symptom**: Process memory grows over time
**Detection Script**:
```python
# Monitor aggregator memory
import psutil
process = psutil.Process()
memory_baseline = process.memory_info().rss
# ... after 1 hour ...
memory_current = process.memory_info().rss
growth_pct = (memory_current - memory_baseline) / memory_baseline * 100
if growth_pct > 20:  # >20% growth
    alert("MEMORY_LEAK_DETECTED", f"Aggregator grew {growth_pct}%")
```

---

## SECTION 7: SUMMARY & RECOMMENDATIONS

### Critical Path (What Must Happen Today)
1. **Locate missing module files** (CRIT-1)
   - Check git history, stash, other branches
   - If lost: reconstruct from vault decision docs
   - Deadline: 2 hours

2. **Test merge scenario** (CRIT-3)
   - Dry-run merge develop → feature/token-efficiency-5b
   - Document all conflicts
   - Create resolution plan
   - Deadline: 2 hours

3. **Validate imports** (CRIT-2)
   - Run import tests for compound module
   - Test star imports
   - Fix circular dependencies if found
   - Deadline: 1 hour

4. **Run full test suite**
   - All 892+ tests must pass with 0 collection errors
   - Deadline: 30 minutes

### Recommended Rollout Timeline
- **TODAY**: Fix critical issues, complete blocking checklist
- **TOMORROW**: High-severity hardening (vault logging, health checks, cost integration)
- **END OF WEEK**: Monitoring setup, load testing, ops training
- **NEXT WEEK**: Staging environment deployment, 24-hour observation
- **WEEK 2**: Limited production rollout (10% → 100%)

### Risk Assessment Conclusion
**Current Status**: CONDITIONAL - Can proceed with Phase 5B after critical fixes
**Confidence Level**: MEDIUM - Several undiscovered issues likely remain (typical for new systems)
**Recommendation**: Fix critical + high-severity items before any production deployment

---

## APPENDIX: Issue Tracking

### Created: 2026-02-09 Session 40-41
### Last Updated: 2026-02-09 14:30 UTC
### Status: DRAFT - Awaiting adversarial team findings

**Related Tasks**:
- Task #14: Failure mode analyst (due today)
- Task #15: Git conflict analyst (due today)
- Task #16: Vault integrity checker (due today)
- Task #17: Assumptions challenger (due today)
- Task #18: Security auditor (due today)
- Task #19: Risk synthesizer (this document)
- Task #7: Final verification (due today)

**Next Review**: Merge findings from all adversarial tasks, update severity/likelihood

---

**Report Prepared By**: risk-synthesizer
**Classification**: INTERNAL - Risk Assessment
**Distribution**: Team Lead, Architecture, DevOps, QA
