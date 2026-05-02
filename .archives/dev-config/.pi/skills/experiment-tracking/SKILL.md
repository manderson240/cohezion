---
name: experiment-tracking
description: Track experiments during 4-day parallel AGI development with daily sync and cross-experiment learning.
---

# Experiment Tracking During Parallel Execution

Track ongoing experiments during 4-day parallel execution of AGI development and Lemonade model mapping.

## Active Experiments

### Experiment 1: MetaLearner Effectiveness
**Owner**: AGI Team  
**Metric**: `meta_learning_success_rate`  
**Target**: >= 0.85  
**Current**: Initializing

**Method**:
1. Apply MetaLearner to AutoImprovingParser
2. Track success rate over 20 learning cycles
3. Measure improvement vs baseline

**Update Schedule**: Daily at sync points  
**Log Location**: `experiments/meta_learner_effectiveness.jsonl`

---

### Experiment 2: Parser Accuracy Improvement (Phase 2)
**Owner**: Lemonade Team  
**Metric**: `extraction_rate`  
**Target**: >= 0.95  
**Current**: 0.917 (baseline from completed experiment)

**Method**:
1. Implement Parser v3 with validation oracle
2. Test on 100 FLM outputs
3. Iterate on failure patterns

**Update Schedule**: Every 6 hours  
**Log Location**: `experiments/parser_accuracy_phase2.jsonl`

---

### Experiment 3: Triune Integration Stability
**Owner**: AGI Team  
**Metric**: `hiho_coherence`  
**Target**: 0.5 ± 0.1  
**Current**: Measuring

**Method**:
1. Run TriuneAGI.recursive_step() 100 times
2. Monitor coherence at each step
3. Verify convergence to fixed-point

**Update Schedule**: After each recursive cycle  
**Log Location**: `experiments/triune_stability.jsonl`

---

### Experiment 4: Model Profiling Database
**Owner**: Lemonade Team  
**Metric**: `models_profiled`  
**Target**: >= 50  
**Current**: 3 (qwen3:4b, Gemma-4-E2B, Jan-v1-4B)

**Method**:
1. Automated profiling of discovered models
2. Measure TTFT, TPS, latency for each
3. Store in performance database

**Update Schedule**: After each model profiled  
**Log Location**: `experiments/model_profiling.jsonl`

---

## Experiment Integration Points

### Daily Sync (Hour 4, 10, 16...)
```python
# At each sync point
def log_experiment_progress(experiment_name, metrics):
    record = {
        "timestamp": datetime.now().isoformat(),
        "experiment": experiment_name,
        "metrics": metrics,
        "parallel_phase": get_current_phase()
    }
    
    # Append to experiment log
    with jsonlines.open(f"experiments/{experiment_name}.jsonl", "a") as f:
        f.write(record)
    
    # Also update SurrealDB for cross-team visibility
    surrealdb.create("experiment_tracking", record)
```

### Cross-Experiment Learning

**MetaLearner → Parser**:
- MetaLearner discovers optimal learning strategies
- Parser applies these strategies to pattern extraction

**Parser → MetaLearner**:
- Parser success/failure patterns inform MetaLearner
- MetaLearner optimizes for parser-specific challenges

**Triune → Model Registry**:
- TriuneAGI.Doer uses ModelCapabilityRegistry
- Model capability knowledge integrated into Knower

**Model Registry → Triune**:
- Model performance data informs Doer planning
- Best model selected based on task requirements

---

## Success Criteria

### Experiment 1 Success
```
MetaLearner improves base learner success rate by >10%
OR
Achieves meta_learning_success_rate >= 0.85
```

### Experiment 2 Success
```
Parser extraction rate reaches >= 0.95
AND
Validates on held-out test set
```

### Experiment 3 Success
```
HIHO coherence stays within 0.5 ± 0.1 for 100 consecutive cycles
AND
Recursive steps converge (not diverge)
```

### Experiment 4 Success
```
Profile >= 50 models
AND
Create capability inference validation >= 90% accuracy
```

---

## Quick Commands

### View Experiment Status
```bash
# View all experiment logs
ls -la experiments/

# View specific experiment
tail -20 experiments/meta_learner_effectiveness.jsonl

# Aggregate all metrics
python -m cohezion.experiments.aggregate --all
```

### Update Experiment
```python
from cohezion.experiments import ExperimentTracker

tracker = ExperimentTracker()
tracker.log_result(
    experiment="parser_accuracy_phase2",
    metric_value=0.93,
    notes=["Improved pattern matching"]
)
```

---

## Files

- `experiments/meta_learner_effectiveness.jsonl`
- `experiments/parser_accuracy_phase2.jsonl`
- `experiments/triune_stability.jsonl`
- `experiments/model_profiling.jsonl`

---

**Status**: Experiments defined, ready for tracking during parallel execution
