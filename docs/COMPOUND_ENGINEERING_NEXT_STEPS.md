# Compound Engineering — Next Steps & Architecture

**Last Updated**: 2026-02-22 (Session 70)
**Status**: Tests 3,318 passing (100%), Lint 831 errors, Skills 74 registered

---

## Modular Component Map

### Core Compound Loop (Production-Ready)
```
CompoundExecutor ──────────────────────────────────── src/cohezion/compound/executor.py
  ├── execute_skill() [NEW: Session 68]              ← Closes recursive improvement loop
  ├── RequestAlignmentAnalyzer                        src/cohezion/compound/request_alignment_analyzer.py
  ├── DegradationDetector                             src/cohezion/compound/degradation_detector.py
  ├── JourneyTracker (12D)                            src/cohezion/compound/journey_tracker.py
  │     ├── text_to_latent()   [was _text_to_latent]  ← L131: public API now
  │     └── holographic_project() [was _holographic_project]
  ├── GlobalMetricsAggregator                         src/cohezion/compound/global_metrics_aggregator.py
  └── RetrospectionEngine ──→ SkillRefiner            src/cohezion/core/compound/
```

### Resource & Reliability (Hardened: Session 70)
```
ResourceMonitor ────────────────────────────────────── src/cohezion/reliability/monitor.py
  ├── asyncio.Lock (now in __init__, not class-level)  ← L130: event loop isolation
  ├── emergency_shutdown() [curl with --max-time 5]    ← L133: no hang when Ollama down
  ├── wait_for_capacity() [30s cooldown]
  ├── predictive throttling [12D velocity gradient]    ← Session 68
  └── get_vitals() [GTT not VRAM carveout]             ← L91
```

### Test Infrastructure (Fully Green: Session 70)
```
tests/ (3,318 passing, 0 failing)
  ├── tests/compound/         ← Journey tracker, executor, alignment
  ├── tests/swarm/            ← test_specifications.py: pytestmark=asyncio added
  ├── tests/unit/             ← test_resource_monitor, test_emergency_shutdown
  ├── tests/conftest.py       ← Singleton resets: FLUME VAE, RL policy, loggers
  └── Pattern: asyncio primitives in __init__, AsyncMock for subprocesses
```

---

## Identified Improvement Targets (TDD-First)

### Priority 1: RecursiveChallenger → self_healing Module
**Goal**: Scale Session 68's RecursiveChallenger autonomous improvement loop to target `src/cohezion/healing/`.

**TDD Spec**:
```python
# Red: Write tests FIRST
def test_recursive_challenger_targets_healing_module():
    """RecursiveChallenger must identify improvement opportunities in immune_system.py"""
    challenger = RecursiveChallenger(target_module="cohezion.healing.immune_system")
    opportunities = challenger.analyze()
    assert len(opportunities) > 0
    assert all(o.has_test_coverage for o in opportunities)

def test_recursive_improvement_is_idempotent():
    """Running improvement twice should not regress test suite"""
    before = get_test_count()
    challenger.execute_improvement_cycle()
    challenger.execute_improvement_cycle()
    assert get_test_count() >= before

def test_improvement_logs_to_vault():
    """Every improvement cycle must log decision to vault"""
    with patch("vault_log_decision") as mock_vault:
        challenger.execute_improvement_cycle()
        mock_vault.assert_called_once()
```

**Architecture**:
- `RecursiveChallenger.target_module` → drives `CompoundExecutor.execute_skill()`
- Each cycle: analyze → generate improvement → write test → implement → verify → log
- Context guard: check `pilot check-context --json` before each recursion layer

### Priority 2: SurrealDB Auth Fix
**Goal**: Restore SurrealDB connectivity (currently `InvalidAuth` → falls back to InMemoryStore).

**TDD Spec**:
```python
def test_surrealdb_auth_succeeds():
    """Should connect with valid credentials, not fall back to InMemoryStore"""
    client = SurrealClient()
    result = await client.connect()
    assert result.backend == "surrealdb"  # NOT "in_memory"
    assert result.is_authenticated

def test_surrealdb_fallback_on_auth_failure():
    """Graceful fallback must still work when auth fails"""
    with patch_bad_credentials():
        client = SurrealClient()
        result = await client.connect()
        assert result.backend == "in_memory"
        assert result.is_degraded  # Signals degraded mode
```

**Investigation path**: Check `~/.surreal`, env vars `SURREAL_USER`/`SURREAL_PASS`, connection string in `pyproject.toml` or `.env`.

### Priority 3: Lint Reduction (E501 Line Length)
**Goal**: Reduce 831 → <200 lint errors by targeting the 173 E501 (line too long) violations.

**Approach**: Run `ruff check src/cohezion/ --select E501 --output-format=json | jq '.[].filename' | sort | uniq -c | sort -rn | head -10` to find the 10 worst files. Auto-wrap with `ruff check --unsafe-fixes` for the subset that's safe.

### Priority 4: Context-Aware Long Horizon Task Engine
**Goal**: Multi-session compound engineering tasks that survive context boundaries.

**Architecture**:
```
LongHorizonTask
  ├── task_spec.md (YAML frontmatter: id, goal, context_budget, progress)
  ├── CompoundExecutor.execute_multi_session(spec)
  │     ├── Check pilot check-context --json before each step
  │     ├── Checkpoint after each sub-task to vault
  │     └── Continue from checkpoint on restart
  └── RetrospectionEngine.synthesize_cross_session(checkpoints)
```

**TDD Spec**:
```python
def test_long_horizon_task_checkpoints_progress():
    task = LongHorizonTask("optimize-self-healing-module", budget_sessions=5)
    task.execute_step()
    checkpoint = task.save_checkpoint()

    # Simulate new session
    resumed = LongHorizonTask.from_checkpoint(checkpoint)
    assert resumed.progress_percent > 0
    assert resumed.steps_completed == task.steps_completed

def test_context_guard_triggers_handoff():
    """Task must halt and checkpoint at 80% context, not continue"""
    with mock_context_at(85):
        task = LongHorizonTask("big-task")
        result = task.execute_step()
        assert result.handoff_triggered
        assert result.checkpoint_saved
```

---

## Token Efficiency Architecture

### Current State
- L1 (hash) + L2 (cosine) + L3 (vault semantic) cache: 95%+ hit rate
- Context guard at 80%: forces handoff
- RequestAlignmentAnalyzer: estimates tokens before execution

### Next: Semantic Prefix Caching
**Insight from Session 70**: The vault `find_relevant_context()` queries are a natural prefix for compound tasks. If the first N tokens of a task's context are always the same vault query result, they can be cached at the API level.

```python
class TokenEfficientCompoundExecutor(CompoundExecutor):
    """Prepend cached vault context to reduce per-call token cost."""

    def _build_context(self, task: str) -> tuple[str, str]:
        # Returns (cached_prefix, dynamic_suffix)
        # cached_prefix can use Anthropic's prompt caching
        vault_context = self.vault.find_relevant_context(task, limit=5)
        return vault_context, task
```

### Next: Embedding-Guided Skill Selection
The `SkillSelector` already uses composite scoring (coherence 50% + efficiency 30% + success 20%). Next step: add **failure pattern avoidance** — track which skills failed in similar contexts and down-weight them.

```python
class SkillSelector:
    def score(self, skill: Skill, context: TaskContext) -> float:
        base = 0.5 * skill.coherence + 0.3 * skill.efficiency + 0.2 * skill.success_rate
        failure_penalty = self.failure_memory.penalty(skill, context)  # NEW
        return base - failure_penalty
```

---

## Compound Engineering Feedback Loop — Next Cycle

```
Cycle N (Session 70):
  INPUT: 83 FAILED tests, 1,724 lint errors
  EXECUTE: /heal + /test-fix
  EVALUATE: 0 FAILED, 831 lint errors
  REFLECT: 6 root cause patterns discovered
  REFINE: L130-L135 in KEY_LEARNINGS; 3 patterns in vault; 2 new skills
  OUTPUT: Improved test infrastructure, documented patterns

Cycle N+1 (Next Session):
  INPUT: 0 FAILED tests, 831 lint errors, SurrealDB auth broken
  EXECUTE: RecursiveChallenger → self_healing module
  EVALUATE: New tests added, self_healing module improved
  REFLECT: What improvement opportunities did the challenger find?
  REFINE: Update PRIME skills with improvement patterns
  OUTPUT: More robust healing system + compound loop closure
```

---

## Session-Level Spec: RecursiveChallenger Scale-Up

**Estimated scope**: 3-5 files, 15-20 new tests, 1-2 sessions

### Task 1: Analyze self_healing module for improvement opportunities
- Read `src/cohezion/healing/immune_system.py`, `deep_audit.py`, `platform_audit.py`
- Map: what functions exist, what tests cover them, what gaps exist
- Output: `docs/healing_module_analysis.md` with improvement opportunities

### Task 2: Write failing tests for identified gaps
- TDD: write tests FIRST (they must fail)
- Focus: immune system velocity thresholds, audit coverage, platform detection
- Target: 10+ new tests

### Task 3: Implement improvements
- Implement to pass the new tests
- Log each improvement to vault via `vault_log_decision()`
- Maintain HIHO coherence invariant (0.5 threshold)

### Task 4: Run RecursiveChallenger on self_healing
- `from cohezion.compound.executor import CompoundExecutor`
- `executor.execute_skill("recursive_improvement", target="cohezion.healing")`
- Verify test suite doesn't regress

### Task 5: Retrospective + skill refinement
- Run `/retrospect`
- Update `RECURSIVE_CHALLENGER_PRIME.md` with findings
- Log to vault

---

**Key Invariants for All Future Work**:
1. asyncio primitives → `__init__`, never class-level
2. All subprocess calls → `--max-time N` + `wait_for(timeout=M)`
3. Async test files with majority async → `pytestmark = pytest.mark.asyncio`
4. Rename method → grep src/ AND tests/ before marking complete
5. /heal → /test-fix order is mandatory
