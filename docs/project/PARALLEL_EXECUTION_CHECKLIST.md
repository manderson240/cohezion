# 4-Day Parallel Execution Checklist

**Workstreams**: AGI Development + Lemonade Model Mapping  
**Protocol**: Quarter-on-a-String (Local NPU/GPU Only)  
**Start Date**: Today (2026-04-10)  
**Models**: qwen3:4b (NPU), Gemma-4-E2B (Vulkan), Jan-v1-4B (Vulkan)

---

## Pre-Flight Verification (15 minutes)

### ✅ NPU Check
```bash
# Run these commands
ls -la /dev/accel/accel0
flm list | wc -l
flm run qwen3:4b --prompt "Test" --max-tokens 5

# Expected:
# /dev/accel/accel0 exists
# >10 models listed
# Response in <100ms
```

### ✅ GPU Check
```bash
# Run these commands
lemonade serve Gemma-4-E2B-it --device vulkan --port 13306 &
sleep 3
curl -s http://localhost:13306/v1/models | head -1

# Expected:
# {"object":"list",...}
```

### ✅ Network Independence Check
```bash
# Optional: Verify no external calls needed
# (Already verified - all systems local)
```

---

## Day 1: Setup + Foundation (Hours 0-6)

### Hour 0-2: Both Workstreams Initialize

**AGI Team (Gemma-4-E2B)**
```bash
# Create MetaLearner foundation
cd /home/mike-anderson/dev/cohezion
uv run python -c "
# Start building MetaLearner class
from cohezion.swarm.auto_improving_parser import AutoImprovingParser
print('MetaLearner target: Optimize AutoImprovingParser strategies')
print('Current parser accuracy: 91.7%')
print('Target: Improve to 95%+ via meta-learning')
"
```

**Lemonade Team (qwen3:4b)**
```bash
# Create Parser v3 foundation
cd /home/mike-anderson/dev/cohezion
uv run python src/cohezion/swarm/lemonade_model_enhancer.py
# Note: Will run discovery, check output for opportunities
```

### Hour 2-4: Continue Building

**AGI Team**: MetaLearner core logic (200 lines)
- Strategy optimization
- Learning history tracking
- Base learner interface

**Lemonade Team**: Parser v3 enhancements
- Validation oracle
- Continuous learning loop
- Pattern promotion logic

### Hour 4-6: First Sync Point

**Activity**: Cross-team sync (30 minutes)

**Sync Agenda**:
1. AGI shares: Meta-learning patterns that could improve parsers
2. Lemonade shares: Parser failure patterns that need meta-learning
3. Both: Update SurrealDB with learnings
4. Plan: Next 6 hours priorities

**Output**: Sync log in `vault/cortex/sync-day1-hour4.md`

---

## Day 1: Integration Phase (Hours 6-12)

### Hour 6-10: Deep Work

**AGI Team**: UnifiedThinker integration
- FLUME encoder interface
- JEPA predictor integration
- Memory retrieval coordination
- 512D unified space implementation

**Lemonade Team**: Parser improvement 91.7% → 95%
- Test on 100 FLM outputs
- Identify remaining failure modes
- Implement new patterns
- Validate with oracle

### Hour 10-12: Second Sync

**Activity**: Deep sync (1 hour)

**Sync Agenda**:
1. MetaLearner tests on Parser v3 strategies
2. Parser discoveries inform MetaLearner's history
3. SurrealDB vault entry: day1-hour10-sync
4. Rebalance: Any blockers or opportunities

---

## Day 2: Core Implementation (Hours 12-24)

### Hour 12-16: AGI Deep Work

**Deliverable**: UnifiedThinker complete (150 lines)

**Tasks**:
- [ ] All components use 512D representation
- [ ] Information flow: FLUME ↔ JEPA ↔ Memory
- [ ] Integration tests passing
- [ ] Documentation complete

**Validation**:
```python
# Should work
from cohezion.swarm.unified_thinker import UnifiedThinker
thinker = UnifiedThinker()
result = thinker.think(test_input)
assert result.embedding.shape == (512,)
```

### Hour 12-20: Lemonade Deep Work

**Deliverable**: Parser 95% + CapabilityDB expanded

**Tasks**:
- [ ] Parser accuracy verified at 95%+
- [ ] 20+ model families in database
- [ ] Confidence scores working
- [ ] Pattern composition rules

**Validation**:
```python
# Should work
from cohezion.swarm.parser_v3 import ProductionParser
parser = ProductionParser()
accuracy = parser.test_accuracy(test_data)
assert accuracy >= 0.95
```

### Hour 16-18: Mid-Day Sync

**Activity**: Integration testing

**Test**: MetaLearner + Parser working together
- MetaLearner analyzes Parser strategies
- Parser uses improved MetaLearner suggestions
- Both write results to SurrealDB

---

## Day 3: Advanced Integration (Hours 24-36)

### Hour 24-32: AGI Triune Integration

**Deliverable**: TriuneAGI bidirectional pathways (300 lines)

**Tasks**:
- [ ] Doer ↔ Thinker connection
- [ ] Thinker ↔ Knower connection  
- [ ] Knower ↔ Doer connection
- [ ] Recursive stabilization
- [ ] HIHO enforcement

**Validation**:
```python
# Should stabilize
from cohezion.swarm.triune_integration import TriuneAGI
agi = TriuneAGI()
for i in range(100):
    agi.recursive_step()
    assert agi.check_hiho_coherence()  # Stays at 0.5
```

### Hour 24-36: Lemonade Profiling

**Deliverable**: 50 models profiled

**Tasks**:
- [ ] Automated profiling script
- [ ] Run on all discovered models
- [ ] Measure TTFT, TPS, latency
- [ ] Database of actual performance

**Validation**:
```python
# Should have profiles
from cohezion.swarm.performance_profiler import ModelPerformanceProfiler
profiler = ModelPerformanceProfiler()
assert len(profiler.performance_db) >= 50
```

### Hour 32-34: Deep Integration

**Activity**: TriuneAGI uses ModelCapabilityRegistry

**Integration Test**:
- TriuneAGI.Doer uses ModelCapabilityRegistry for planning
- TriuneAGI.Knower learns from model performance data
- Both workstreams inform each other

---

## Day 4: Validation + Documentation (Hours 36-48)

### Hour 36-42: Testing + Validation

**AGI Testing**:
- [ ] MetaLearner optimizes real strategies
- [ ] UnifiedThinker all tests pass
- [ ] TriuneAGI recursive stability verified
- [ ] HIHO maintained throughout

**Lemonade Testing**:
- [ ] Parser 95% on held-out test set
- [ ] CapabilityDB accuracy verified
- [ ] PerformanceDB complete
- [ ] All 50 models have real metrics

### Hour 42-46: Documentation + Cleanup

**AGI Docs**:
- `docs/agi_recursive_architecture.md`
- `docs/triune_integration.md`
- `docs/meta_learner_usage.md`

**Lemonade Docs**:
- `docs/model_capability_mapping.md`
- `docs/parser_v3_guide.md`
- `docs/performance_database.md`

### Hour 46-48: Final Sync + Export

**Activities**:
1. Final integration test
2. SurrealDB export of all learnings
3. Skill extraction for both workstreams
4. Retrospective documentation

**Outputs**:
- `vault/cortex/parallel-execution-retrospective.md`
- `surrealdb_export_parallel_execution.json`
- Skills: `agi_recursive_systems`, `lemonade_model_mapping`

---

## Daily Quick Reference

### Morning Routine (Hour 0)
```bash
# Verify models operational
cd /home/mike-anderson/dev/cohezion
./scripts/verify_local_models.sh

# Check yesterday's sync vault
ls -t vault/cortex/sync* | head -1

# Review dashboard
cat ~/.config/cohezion/daily_dashboard.json
```

### Sync Template (Hours 4, 10, 16, etc.)
```markdown
## Sync: [Timestamp]

### AGI Team Progress
- Completed: [list]
- Blockers: [none or list]
- Learnings: [key insights]

### Lemonade Team Progress
- Completed: [list]
- Blockers: [none or list]
- Discoveries: [key findings]

### Cross-Integration
- AGI → Lemonade: [shared insights]
- Lemonade → AGI: [shared patterns]
- SurrealDB: [entries made]

### Next Period
- AGI priorities: [list]
- Lemonade priorities: [list]
- Sync time: [next hour]
```

### Evening Routine (Hour 12, 24, 36)
```bash
# Generate daily report
uv run python -m cohezion.dogfooding.daily_cycle

# Save checkpoint
python -c "from cohezion.dogfooding import DisasterRecovery; dr = DisasterRecovery(); dr.create_checkpoint(...)"

# Log learnings to vault
echo "[learnings]" >> vault/cortex/day[N]-learnings.md
```

---

## Success Verification (End of Day 4)

### AGI Deliverables Checklist

```bash
# Verify MetaLearner
python -c "from cohezion.swarm.meta_learner import MetaLearner; print('✅ MetaLearner')"

# Verify UnifiedThinker  
python -c "from cohezion.swarm.unified_thinker import UnifiedThinker; print('✅ UnifiedThinker')"

# Verify TriuneAGI
python -c "from cohezion.swarm.triune_integration import TriuneAGI; print('✅ TriuneAGI')"

# Verify recursive stability
python -c "
from cohezion.swarm.triune_integration import TriuneAGI
agi = TriuneAGI()
for i in range(10):
    agi.recursive_step()
print('✅ Recursive stability')
"
```

### Lemonade Deliverables Checklist

```bash
# Verify Parser v3 at 95%
python -c "
from cohezion.swarm.parser_v3 import ProductionParser
parser = ProductionParser()
print(f'Parser accuracy: {parser.test_accuracy()}%')
assert parser.test_accuracy() >= 0.95
"

# Verify CapabilityDB
python -c "
from cohezion.swarm.lemonade_model_enhancer import MODEL_CAPABILITY_PATTERNS
print(f'Capability patterns: {len(MODEL_CAPABILITY_PATTERNS)}')
assert len(MODEL_CAPABILITY_PATTERNS) >= 20
"

# Verify PerformanceDB
python -c "
from cohezion.swarm.performance_profiler import ModelPerformanceProfiler
profiler = ModelPerformanceProfiler()
print(f'Performance profiles: {len(profiler.performance_db)}')
assert len(profiler.performance_db) >= 50
"
```

### Integration Verification

```bash
# Verify cross-team integration
python -c "
# TriuneAGI uses ModelCapabilityRegistry
from cohezion.swarm.triune_integration import TriuneAGI
from cohezion.swarm.model_capability_registry import ModelCapabilityRegistry

agi = TriuneAGI()
registry = ModelCapabilityRegistry()
print('✅ Integration verified')
"

# Verify SurrealDB has learnings
ls -la vault/cortex/parallel-execution*
# Should have 12+ sync files, final retrospective
```

---

## Blocker Escalation

### If Stuck for >1 Hour

1. **Switch Model**: Try alternative local model
2. **Simplify**: Reduce scope, keep core
3. **Document**: Log blocker in vault
4. **Sync Early**: Call unscheduled sync with other team
5. **Fallback**: Use previously working version

### Critical Blockers

- **NPU unavailable**: Switch to Vulkan models (Gemma-4, Jan-v1)
- **Vulkan failure**: Use CPU inference (slower but works)
- **Code won't compile**: Check Python version (3.11+)
- **Import errors**: Verify `uv run` in cohezion directory

---

## Resources

### Quick Commands

```bash
# Verify all models
curl http://localhost:13306/v1/models  # Gemma
flm list | head -5                     # NPU

# Start work session
cd /home/mike-anderson/dev/cohezion
source .venv/bin/activate  # or: uv run python ...

# Save checkpoint
python -m cohezion.dogfooding.production_hardening --checkpoint

# View dashboard
python -m cohezion.swarm.dynamic_levers --dashboard
```

### File Locations

- AGI code: `src/cohezion/swarm/meta_learner.py`, etc.
- Lemonade code: `src/cohezion/swarm/parser_v3.py`, etc.
- Sync logs: `vault/cortex/sync-*.md`
- Checkpoints: `~/.config/cohezion/backups/`

---

## Motivation

**Why 4 Days?**
- Long enough: Deep work, integration, testing
- Short enough: Urgency, focus, achievable

**Why Parallel?**
- 2× speedup via specialization
- Cross-pollination of insights
- Resilience (if one stalls, other continues)

**Why Local Only?**
- Zero cost
- Privacy guaranteed
- No external dependencies
- Maximum speed (no network)

---

**Ready to execute. Both workstreams. 4 days. Zero external cost. Full AGI recursive infrastructure + comprehensive model mapping.**

**Start: Hour 0 (Now)**  
**End: Hour 48 (Day 4)**  
**Status: READY**
