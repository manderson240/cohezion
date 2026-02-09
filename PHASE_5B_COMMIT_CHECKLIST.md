# Phase 5B Atomic Commit Checklist

**Version**: 1.0
**Created**: 2026-02-09
**Status**: Ready for Team Execution
**Branch**: `feature/token-efficiency-5b`

---

## Overview

This checklist ensures each Phase 5B subsystem is committed atomically with proper quality gates.

Use this as a template for each subsystem commit:
1. ✓ Implementation complete
2. ✓ Tests written and passing
3. ✓ 100% coverage verified
4. ✓ Backward compatibility check
5. ✓ Imports verified
6. ✓ Documentation complete
7. ✓ Vault decision logged
8. ✓ Commit with message

---

## Subsystem 1: Redis Semantic Cache (5B.1)

**Lead**: redis-specialist
**Estimated Time**: 4-5 hours
**Files**: redis_cache.py + tests (2 files)

### Pre-Commit Checklist

- [ ] **Implementation Complete**
  - [ ] `src/cohezion/cache/redis_cache.py` exists
  - [ ] Class: `RedisSemanticCache(SemanticCache)`
  - [ ] Methods: `get()`, `put()`, `clear()`, `stats()`
  - [ ] Error handling: Graceful fallback if Redis unavailable
  - [ ] Config: redis host, port, ttl, db_select

- [ ] **Tests Written**
  - [ ] `tests/cache/test_redis_cache.py` (unit tests)
  - [ ] `tests/cache/test_redis_distributed_integration.py` (integration)
  - [ ] Test cases: hit/miss, fallback, ttl, error handling
  - [ ] Coverage: 100% of redis_cache.py

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/cache/ -q`
  - [ ] Coverage: `coverage report --fail-under=100`
  - [ ] Ruff clean: `ruff check && ruff format`
  - [ ] Imports work: `python -c "from cohezion.cache.redis_cache import RedisSemanticCache"`

- [ ] **Backward Compatibility**
  - [ ] Existing `SemanticCache` API unchanged
  - [ ] Existing tests still pass (892 tests)
  - [ ] No breaking changes to `__init__.py`

- [ ] **Documentation**
  - [ ] Docstrings: All public methods documented
  - [ ] Example usage in docstring
  - [ ] Error cases documented

- [ ] **Vault Logging**
  - [ ] Decision logged to vault: "Phase 5B.1 RedisSemanticCache Implementation"
  - [ ] Architecture rationale documented
  - [ ] Performance expectations noted

### Commit Command

```bash
git add src/cohezion/cache/redis_cache.py
git add src/cohezion/cache/__init__.py  # Add to exports
git add tests/cache/test_redis_cache.py
git add tests/cache/test_redis_distributed_integration.py

git commit -m "feat: Phase 5B.1 Implement RedisSemanticCache for distributed L3

- Add RedisSemanticCache wrapper around SemanticCache
- L1/L2 local in-memory cache + Redis shared L3
- Graceful fallback if Redis unavailable
- Backward compatible API: .get()/.put() unchanged
- Tests: unit + integration tests (100% coverage)

Closes: Phase 5B.1 task
Co-Authored-By: redis-specialist <noreply@anthropic.com>"
```

---

## Subsystem 2: Consensus Skill Voting (5B.2)

**Lead**: consensus-engineer
**Estimated Time**: 3-4 hours
**Files**: skill_consensus_voter.py + tests (2 files)
**Status**: ✓ PARTIALLY COMPLETE (tests committed)

### Pre-Commit Checklist

- [ ] **Implementation Complete**
  - [ ] `src/cohezion/compound/skill_consensus_voter.py` exists
  - [ ] Class: `SkillConsensusVoter`
  - [ ] Strategies: majority, weighted, unanimous
  - [ ] Method: `vote(agents, request, top_k) -> (skill, confidence, strategy)`
  - [ ] Vault persistence: vote metrics recorded

- [ ] **Tests Written**
  - [ ] `tests/compound/test_skill_consensus_voter.py` (unit tests) ✓ DONE
  - [ ] Test cases: majority, weighted, unanimous, tie-breaking
  - [ ] Coverage: 100% of skill_consensus_voter.py

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/compound/test_skill_consensus_voter.py -q`
  - [ ] Coverage: `coverage report --fail-under=100`
  - [ ] Ruff clean: `ruff check src/cohezion/compound/skill_consensus_voter.py`
  - [ ] Imports work: `python -c "from cohezion.compound.skill_consensus_voter import SkillConsensusVoter"`

- [ ] **Backward Compatibility**
  - [ ] Existing `SkillSelector` API unchanged
  - [ ] Existing tests still pass (892 tests)
  - [ ] No impact on single-agent flow

- [ ] **Documentation**
  - [ ] Docstrings: All public methods documented
  - [ ] Voting strategy documentation
  - [ ] Confidence computation explanation

- [ ] **Vault Logging**
  - [ ] Decision logged: "Phase 5B.2 SkillConsensusVoter Implementation"
  - [ ] Voting strategy design documented
  - [ ] Performance expectations noted

### Commit Command

```bash
git add src/cohezion/compound/skill_consensus_voter.py
git add tests/compound/test_skill_consensus_voter.py  # Already in 2b0e29bc

git commit -m "feat: Phase 5B.2 Implement SkillConsensusVoter

- Multi-agent voting on top-k skills
- Strategies: majority, weighted, unanimous
- Vault persistence for vote metrics
- Tests: unit tests for each strategy (100% coverage)

Closes: Phase 5B.2 task
Co-Authored-By: consensus-engineer <noreply@anthropic.com>"
```

---

## Subsystem 3: Global Metrics Aggregation (5B.3)

**Lead**: dashboard-engineer
**Estimated Time**: 3-4 hours
**Files**: global_metrics_aggregator.py + tests (2 files)

### Pre-Commit Checklist

- [ ] **Implementation Complete**
  - [ ] `src/cohezion/compound/global_metrics_aggregator.py` exists
  - [ ] Class: `GlobalMetricsAggregator`
  - [ ] Methods: `get_metrics()`, `aggregate()`, `query_vault()`
  - [ ] Queries: by team/agent/skill/time range
  - [ ] Latency: <500ms for dashboard queries

- [ ] **Tests Written**
  - [ ] `tests/compound/test_global_metrics_aggregator.py` (unit + integration)
  - [ ] Test cases: aggregation, caching, latency, edge cases
  - [ ] Coverage: 100% of global_metrics_aggregator.py

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/compound/test_global_metrics_aggregator.py -q`
  - [ ] Coverage: `coverage report --fail-under=100`
  - [ ] Ruff clean: `ruff check && ruff format`
  - [ ] Latency test: confirm <500ms for 1000 metrics
  - [ ] Imports work: `python -c "from cohezion.compound.global_metrics_aggregator import GlobalMetricsAggregator"`

- [ ] **Backward Compatibility**
  - [ ] Existing `TeamCompoundMetrics` unchanged
  - [ ] Can be used alongside existing metrics
  - [ ] Existing tests still pass

- [ ] **Documentation**
  - [ ] Docstrings: All public methods documented
  - [ ] Query examples in docstring
  - [ ] Aggregation formulas documented

- [ ] **Vault Logging**
  - [ ] Decision logged: "Phase 5B.3 Global Metrics Aggregation"
  - [ ] Architecture and query strategy documented
  - [ ] Performance targets noted

### Commit Command

```bash
git add src/cohezion/compound/global_metrics_aggregator.py
git add tests/compound/test_global_metrics_aggregator.py

git commit -m "feat: Phase 5B.3 Global Metrics Aggregation

- Cross-instance metrics aggregation with <500ms latency
- Query by team/agent/skill/time range
- Real-time dashboard widgets: utilization, cache hit rates
- Vault export for historical analysis
- Tests: aggregation + latency validation (100% coverage)

Closes: Phase 5B.3 task
Co-Authored-By: dashboard-engineer <noreply@anthropic.com>"
```

---

## Subsystem 4: Session Persistence (5B.4)

**Lead**: session-specialist
**Estimated Time**: 3-4 hours
**Files**: session_manager_persistence.py + tests (3 files)

### Pre-Commit Checklist

- [ ] **Implementation Complete**
  - [ ] `src/cohezion/compound/session_manager_persistence.py` exists
  - [ ] Class: `SessionPersistence`
  - [ ] Methods: `persist_session()`, `recover_session()`
  - [ ] Vault storage: atomic writes with tags
  - [ ] Recovery latency: <1 second

- [ ] **Tests Written**
  - [ ] `tests/compound/test_session_manager_persistence.py` (unit tests)
  - [ ] `tests/compound/test_session_persistence_integration.py` (integration)
  - [ ] Test cases: persist, recover, error handling, atomicity
  - [ ] Coverage: 100% of session_manager_persistence.py

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/compound/test_session*persistence*.py -q`
  - [ ] Coverage: `coverage report --fail-under=100`
  - [ ] Ruff clean: `ruff check && ruff format`
  - [ ] Recovery latency test: confirm <1 second
  - [ ] Imports work: `python -c "from cohezion.compound.session_manager_persistence import SessionPersistence"`

- [ ] **Backward Compatibility**
  - [ ] Existing `InferenceSession` API unchanged
  - [ ] Persistence is optional (non-blocking)
  - [ ] Existing tests still pass

- [ ] **Documentation**
  - [ ] Docstrings: All public methods documented
  - [ ] Recovery procedure documented
  - [ ] Failure modes documented

- [ ] **Vault Logging**
  - [ ] Decision logged: "Phase 5B.4 Session Persistence"
  - [ ] Vault storage strategy documented
  - [ ] Recovery procedure documented

### Commit Command

```bash
git add src/cohezion/compound/session_manager_persistence.py
git add tests/compound/test_session_manager_persistence.py
git add tests/compound/test_session_persistence_integration.py

git commit -m "feat: Phase 5B.4 Session Persistence & Recovery

- Atomic vault storage for session state
- Hot-load recovery (<1sec)
- Backward compatible with InferenceSession
- Tests: persistence + recovery + atomicity (100% coverage)

Closes: Phase 5B.4 task
Co-Authored-By: session-specialist <noreply@anthropic.com>"
```

---

## Subsystem 5: Cost-Aware Router (5B.5)

**Lead**: cost-optimizer
**Estimated Time**: 4-5 hours
**Files**: cost_aware_router.py + tests (2 files)

### Pre-Commit Checklist

- [ ] **Implementation Complete**
  - [ ] `src/cohezion/swarm/cost_aware_router.py` exists
  - [ ] Class: `CostAwareRouter`
  - [ ] Methods: `route(query, context) -> ModelConfig`
  - [ ] Complexity analysis: token count + keyword scoring
  - [ ] Model selection: phi3:mini (simple) → qwen (medium) → deepseek (complex)
  - [ ] Budget enforcement: fallback to cheaper model if needed
  - [ ] Cost tracking: all decisions logged

- [ ] **Tests Written**
  - [ ] `tests/swarm/test_cost_aware_router.py` (unit + integration)
  - [ ] Test cases: complexity analysis, model selection, budget fallback
  - [ ] Coverage: 100% of cost_aware_router.py

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/swarm/test_cost_aware_router.py -q`
  - [ ] Coverage: `coverage report --fail-under=100`
  - [ ] Ruff clean: `ruff check && ruff format`
  - [ ] Cost reduction test: confirm ≥30% queries to phi3:mini
  - [ ] Imports work: `python -c "from cohezion.swarm.cost_aware_router import CostAwareRouter"`

- [ ] **Backward Compatibility**
  - [ ] Existing `ExecutionContext` API unchanged
  - [ ] Can be used alongside existing routers
  - [ ] Existing tests still pass

- [ ] **Documentation**
  - [ ] Docstrings: All public methods documented
  - [ ] Complexity thresholds documented
  - [ ] Model selection logic explained

- [ ] **Vault Logging**
  - [ ] Decision logged: "Phase 5B.5 Cost-Aware Router"
  - [ ] Routing strategy documented
  - [ ] Budget enforcement logic documented

### Commit Command

```bash
git add src/cohezion/swarm/cost_aware_router.py
git add src/cohezion/cost_optimization/__init__.py  # Update exports
git add tests/swarm/test_cost_aware_router.py

git commit -m "feat: Phase 5B.5 Cost-Aware Router & Budget Integration

- Complexity-based model selection (simple/medium/complex)
- Route 30%+ queries to phi3:mini for cost reduction
- BudgetEnforcer integration with hard/soft limits
- Cost tracking and fallback on budget exhaustion
- Tests: router logic + budget enforcement (100% coverage)

Closes: Phase 5B.5 task
Co-Authored-By: cost-optimizer <noreply@anthropic.com>"
```

---

## Subsystem 6: Integration Testing (5B.6)

**Lead**: qa-lead
**Estimated Time**: 3-4 hours
**Files**: test_phase_5b_integration.py (1 file)

### Pre-Commit Checklist

- [ ] **Tests Complete**
  - [ ] `tests/test_phase_5b_integration.py` exists
  - [ ] 46+ integration tests covering all subsystems
  - [ ] Test scenarios: Redis + Consensus + Metrics end-to-end
  - [ ] Performance tests: latency, throughput, cache hit rates
  - [ ] Vault persistence tests: atomic writes, recovery

- [ ] **Quality Gates**
  - [ ] All tests pass: `uv run pytest tests/test_phase_5b_integration.py -q`
  - [ ] Integration with existing tests: `uv run pytest tests/ -q` → 892+ passing
  - [ ] Coverage: integration tests contribute to 85%+ overall
  - [ ] Ruff clean: `ruff check tests/test_phase_5b_integration.py`
  - [ ] All imports work: `python -c "import tests.test_phase_5b_integration"`

- [ ] **Documentation**
  - [ ] Test scenarios documented
  - [ ] Performance expectations documented
  - [ ] How to run integration tests documented

- [ ] **Vault Logging**
  - [ ] Decision logged: "Phase 5B Integration Testing"
  - [ ] Test scenarios documented
  - [ ] Performance baselines recorded

### Commit Command

```bash
git add tests/test_phase_5b_integration.py

git commit -m "test: Phase 5B Comprehensive Integration Framework

- 46+ integration tests covering all Phase 5B subsystems
- Test scenarios: distributed cache + consensus + metrics
- Performance validation: <500ms query latency
- Vault persistence validation: atomic writes + recovery

All 892+ tests passing
Coverage: 85%+

Co-Authored-By: qa-lead <noreply@anthropic.com>"
```

---

## Subsystem 7: Documentation & Decisions (5B.7)

**Lead**: All team members
**Estimated Time**: 1-2 hours
**Files**: Docs + Vault decisions

### Pre-Commit Checklist

- [ ] **Documentation Complete**
  - [ ] All .md files have clear explanations
  - [ ] Architecture decisions documented
  - [ ] API usage examples provided
  - [ ] Integration points explained

- [ ] **Vault Decisions**
  - [ ] Each subsystem has a vault decision file
  - [ ] Decision rationale documented
  - [ ] Trade-offs explained
  - [ ] Performance expectations recorded

- [ ] **Quality Gates**
  - [ ] Documentation builds without errors
  - [ ] No broken links in docs
  - [ ] Vault files use proper tags

### Commit Command

```bash
git add PHASE_5B_BRANCH_SETUP.md
git add PHASE_5B_IMPLEMENTATION_GUIDE.md
git add GIT_WORKFLOW_PHASE_5B.md
git add cloud-vault-mcp/vault/decisions/2026-02-09-*.md

git commit -m "docs: Phase 5B Implementation Guide & Decision Logs

- Implementation guidelines for all specialists
- Architectural principles: backward compat, non-blocking persistence
- Integration patterns: Redis, consensus, metrics
- Testing patterns: mocking, load testing
- Common pitfalls and success indicators
- All Phase 5B decisions logged to vault with rationale

Generated: 2026-02-09 Session 40
Co-Authored-By: Team <noreply@anthropic.com>"
```

---

## Final Verification Before Merge

### Pre-Merge Checklist

- [ ] **All Tests Pass**
  ```bash
  uv run pytest tests/compound/ tests/cache/ tests/security/ tests/test_*.py -q
  # Expected: ✓ 892+ tests passing, 0 failures
  ```

- [ ] **Code Coverage**
  ```bash
  coverage run -m pytest tests/ && coverage report --fail-under=85
  # Expected: ✓ 85%+ coverage on all new code
  ```

- [ ] **Code Formatting**
  ```bash
  ruff check src/ && ruff format --check src/
  # Expected: ✓ No errors or warnings
  ```

- [ ] **Imports Verified**
  ```bash
  python -c "
  from cohezion.cache import RedisSemanticCache
  from cohezion.compound import SkillConsensusVoter, GlobalMetricsAggregator, SessionPersistence
  from cohezion.swarm import CostAwareRouter
  print('✓ All imports work')
  "
  # Expected: ✓ All imports work
  ```

- [ ] **Backward Compatibility**
  - [ ] All existing tests still pass (892 tests)
  - [ ] No API breaking changes
  - [ ] New params all optional with defaults
  - [ ] Old code runs unchanged

- [ ] **Branch State**
  ```bash
  git status
  # Expected: ✓ Clean working directory
  ```

- [ ] **Commit History**
  ```bash
  git log --oneline feature/token-efficiency-5b ^develop | wc -l
  # Expected: 7+ new commits (one per subsystem)
  ```

- [ ] **Ready to Push**
  ```bash
  git push origin feature/token-efficiency-5b
  # Expected: ✓ All commits pushed to origin
  ```

---

## How to Use This Checklist

1. **For each subsystem**: Copy the checklist section
2. **Check off items** as you complete them
3. **Run quality gates** before committing
4. **Use commit command** provided in each section
5. **After all 7 subsystems**: Run final verification
6. **Create PR** to develop branch
7. **Get code review** before merging

---

## Tips

- **Don't skip tests**: 100% coverage is mandatory
- **Don't force-push shared branches**: Only feature/token-efficiency-5b
- **Don't break existing code**: Backward compatibility is required
- **Do commit atomically**: One subsystem per commit
- **Do document decisions**: Vault logs are important for learning

---

**Ready to begin Phase 5B team execution!**

Last Updated: 2026-02-09
Status: Ready for Implementation ✓
