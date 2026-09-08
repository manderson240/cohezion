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

### Priority 1: RecursiveChallenger → self_healing Module ✅
**Implemented: Session 69**. `RecursiveChallenger` now targets the `cohezion.healing` module and successfully identifies code duplication in `immune_system.py`. It surgically removes the duplication in a TDD-driven autonomous cycle.

### Priority 2: SurrealDB Auth Fix ✅
**Implemented: Session 69**. The `AsyncSurreal` client now natively supports correct authentication and connecting without falling back.

### Priority 3: Lint Reduction (E501 Line Length)
**Goal**: Reduce 831 → <200 lint errors by targeting the 173 E501 (line too long) violations.

**Approach**: Run `ruff check src/cohezion/ --select E501 --output-format=json | jq '.[].filename' | sort | uniq -c | sort -rn | head -10` to find the 10 worst files. Auto-wrap with `ruff check --unsafe-fixes` for the subset that's safe.

### Priority 4: Context-Aware Long Horizon Task Engine ✅
**Implemented: Session 69**. `LongHorizonTask` engine checkpoints progress across session boundaries, respecting an 80% context utilization guardrail to avoid context degradation.


---

## Token Efficiency Architecture

### Current State
- L1 (hash) + L2 (cosine) + L3 (vault semantic) cache: 95%+ hit rate
- Context guard at 80%: forces handoff
- RequestAlignmentAnalyzer: estimates tokens before execution

### Next: Semantic Prefix Caching ✅
**Implemented: Session 69**. The `TokenEfficientCompoundExecutor` now segregates static context (vault + core instructions) into a `cacheable_prefix`. This leverages API-level prompt caching, dropping latency and cost for recursive compound tasks.

```python
from cohezion.compound.token_efficient_executor import TokenEfficientCompoundExecutor

executor = TokenEfficientCompoundExecutor(mcp_client, token_client=client)
result = await executor.execute_task_efficient(
    task_description="Refine this module",
    skill_name="refiner",
    operation_type="transform",
    execute_fn=my_async_llm_call,  # Receives (prefix, suffix)
)
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
