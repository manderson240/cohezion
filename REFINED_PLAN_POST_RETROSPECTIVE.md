# Refined Plan: Post-Retrospective Execution

**Date:** 2026-04-11
**Status:** Recovery Complete, Refined Plan Active
**Session Type:** Post-Hallucination Recovery

---

## Executive Summary

This plan replaces the previous "Hour 1-2, Hour 3-4, ..." parallel execution roadmap with an **honest, phased approach** that prioritizes verification over velocity.

**Core Principle:** Every claim must be backed by execution evidence.

---

## Phase 0: Foundation (Immediate - Complete)

### What Was Done
- ✅ 5 modules created (1,535 lines)
- ✅ 2 bugs found and fixed
- ✅ 26/26 existing tests passing
- ✅ All imports working
- ✅ Demos running

### What Was Learned
- Import ≠ Functionality
- Demo functions must be executed
- Placeholder code (ellipsis) breaks things
- Reality checks prevent hallucinations

---

## Phase 1: Test Coverage (Next 1-2 Sessions)

### Goal
Achieve >80% test coverage on all Phase 0 modules.

### Tasks

#### 1.1 Unified Thinker Tests
```python
# tests/swarm/test_unified_thinker.py
- test_simplified_encoder()
- test_jepa_prediction()
- test_episodic_memory_retrieval()
- test_reasoning_integration()
- test_embed_dim_initialization()  # Regression test
- test_normalization()  # Cosine similarity
```

#### 1.2 Parser v3 Tests
```python
# tests/swarm/test_parser_v3.py
- test_validation_oracle()
- test_parse_with_validation()  # Not fuzzy_parse!
- test_correction_suggestions()
- test_five_validation_layers()
- test_accuracy_measurement()
- test_95_percent_target()  # Known fail until trained
```

#### 1.3 Triune Integration Tests
```python
# tests/swarm/test_triune_integration.py
- test_bidirectional_connections()
- test_recursive_step()
- test_hiho_stability()
- test_doer_thinker_knower_pathways()
- test_state_integration()
- test_restoring_force()
```

#### 1.4 Meta Learner Tests
```python
# tests/swarm/test_meta_learner.py
- test_strategy_selection()
- test_meta_optimize()
- test_expected_improvement()
- test_strategy_pool()
```

#### 1.5 Lemonade Enhancer Tests
```python
# tests/swarm/test_lemonade_enhancer.py
- test_model_family_patterns()
- test_multi_source_discovery()
- test_12_patterns_loaded()
```

### Success Criteria
- All new tests pass
- Coverage >80% for new modules
- No regressions in existing 26 tests
- Reality check passes for all

### Estimated Effort
2-3 hours

---

## Phase 2: Parser Accuracy (Following Phase 1)

### Goal
Achieve actual 95% parser accuracy (current: ~50% baseline).

### Tasks

#### 2.1 Collect Ground Truth Dataset
```python
# From FLM outputs
dataset = [
    ("qwen3:4b ⏬", {"name": "qwen3:4b", "backend": "NPU"}),
    ("gemma-4-E2B-it ⏬", {"name": "gemma-4-E2B-it", "backend": "GPU_VULKAN"}),
    # ... 100+ examples
]
```

#### 2.2 Implement Feedback Loop
- Parse line → Validate → Compare to ground truth
- Log false positives/negatives
- Adjust confidence thresholds

#### 2.3 Tune for 95%
```python
parser = ParserV3()
results = []
for raw, expected in ground_truth:
    actual = parser.parse_with_validation(raw)
    results.append(actual == expected)

accuracy = sum(results) / len(results)
assert accuracy >= 0.95
```

### Success Criteria
- Measured accuracy ≥ 95%
- Validation feedback loop working
- Known failure modes documented

### Estimated Effort
4-6 hours

---

## Phase 3: TriuneAGI Real Features (Following Phase 2)

### Goal
Replace placeholder/dummy implementations with real AGI features.

### Tasks

#### 3.1 Real JEPA World Model
```python
# Currently:
def predict(self, state):
    return state + np.random.randn(self.embed_dim) * 0.01

# Replace with:
def predict(self, state):
    return self.jepa_model.forward(state)
```

#### 3.2 Real Episodic Memory
```python
# Currently:
self.memories = []

# Replace with:
from cohezion.memory.episodic import EpisodicStore
self.memory = EpisodicStore(backend="surrealdb")
```

#### 3.3 Real HIHO Stabilization
```python
# Currently:
if abs(coherence - 0.5) > 0.1:
    logger.warning("Diverging!")

# Replace with:
self.hiho_controller = HIHOController()
correction = self.hiho_controller.calculate_restoring_force(current, target)
```

### Success Criteria
- JEPA predictions use actual model
- Memory persists across restarts
- HIHO maintains 0.5±0.1 coherence
- Integration tests pass

### Estimated Effort
6-8 hours

---

## Phase 4: Integration (Following Phase 3)

### Goal
Full integration of all components.

### Tasks

#### 4.1 MetaLearner + UnifiedThinker
- Connect learning strategies to reasoning
- Enable recursive self-improvement

#### 4.2 Parser v3 + Registry
- Use validation oracle for registry updates
- Maintain consistency

#### 4.3 TriuneAGI + MetaLearner
- MetaLearner improves Doer/Thinker/Knower
- Recursive optimization

#### 4.4 End-to-End Demo
```python
# Full system working
cohezion = CohezionSystem()
cohezion.initialize()
result = cohezionage.execute_task("Create a Python function", 
    use_triune=True,
    use_meta_learning=True
)
```

### Success Criteria
- End-to-end workflow functional
- All components integrated
- Performance acceptable
- Documentation complete

### Estimated Effort
8-10 hours

---

## Honest Progress Tracking

### Metrics We Track
| Metric | Current | Phase 1 | Phase 2 | Phase 3 | Phase 4 |
|--------|---------|---------|---------|---------|---------|
| Test Coverage | 0% | 80%+ | 80%+ | 85%+ | 90%+ |
| Parser Accuracy | 50% | 50% | 95% | 95% | 95% |
| HIHO Coherence | 0.50 | 0.50 | 0.50 | 0.50±0.1 | 0.50±0.05 |
| Module Tests | 0 | 50+ | 50+ | 60+ | 80+ |
| Integration Tests | 0 | 0 | 0 | 10+ | 20+ |

### Metrics We DON'T Track
- ❌ Lines of code (inflatable)
- ❌ Percentage completion (meaningless)
- ❌ "Working" claims without proof
- ❌ Hours "completed" vs verified

---

## Anti-Pattern Prevention

### Built Into This Plan

1. **No Forward Planning Without Verification**
   - Phase N+1 only starts when Phase N tests pass
   - No speculative "Hour X" claims

2. **Test-First for All Features**
   - Every module needs tests before Phase 1 ends
   - No "we'll add tests later"

3. **Reality Check Every Phase**
   - Phase completion requires:
     - All tests pass
     - Demo runs
     - User confirmation

4. **Honest Status Reporting**
   - If something fails, we report it
   - If something's not done, we say so
   - No completion inflation

---

## Success Criteria for This Plan

### Overall Success
- All phases complete
- All tests pass
- Parser accuracy ≥ 95%
- HIHO coherence maintained
- No hallucination events
- User trust maintained

### Phase Success Criteria
Each phase must:
1. Pass reality check
2. Have >80% test coverage
3. Run demo successfully
4. Get user sign-off
5. Document completion honestly

---

## Risk Mitigation

### Risk: Scope Creep
**Mitigation:** Strict phase gates, no Phase N+1 before Phase N completion

### Risk: Hallucination Return
**Mitigation:** Mandatory reality_check skill at each phase gate

### Risk: Test Writing Delay
**Mitigation:** Tests are Phase 1, not deferred

### Risk: Integration Hell
**Mitigation:** Continuous integration testing, not big-bang

---

## Timeline (Honest Estimate)

| Phase | Effort | Cumulative |
|-------|--------|------------|
| Phase 0 (Done) | - | Complete |
| Phase 1 | 2-3 hrs | +2-3 hrs |
| Phase 2 | 4-6 hrs | +6-9 hrs |
| Phase 3 | 6-8 hrs | +12-17 hrs |
| Phase 4 | 8-10 hrs | +20-27 hrs |

**Total:** 20-27 hours of focused work

**Note:** Previous "4-day parallel execution" claim was hallucinated. This is a single-threaded, verified approach.

---

## Checkpoints

### Before Each Phase
- [ ] Previous phase tests pass
- [ ] Reality check complete
- [ ] User confirmation obtained

### After Each Phase
- [ ] All tests pass
- [ ] Demo runs successfully
- [ ] Documentation complete
- [ ] SurrealDB export created
- [ ] Honest status report written

---

## References

- **Retrospective:** `cloud-vault-mcp/vault/cortex/retrospective-hallucination-recovery-2026-04-11.md`
- **SurrealDB Export:** `surrealdb_export_retrospective_2026-04-11.json`
- **Reality Check Skill:** `.pi/skills/reality-check/SKILL.md`

---

## Conclusion

This plan replaces optimistic claims with honest verification. The goal is not speed but **sustainable correctness**.

**Key Principle:** >98% honest accuracy beats fictional 100%.

**Ready to Begin:** Phase 1 awaits user confirmation.
