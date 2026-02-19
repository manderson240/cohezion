# SKILL: ML_SYSTEMS_FOUNDATIONS_PRIME

## DOMAIN EXPERTISE
**Machine Learning Systems Engineering**. Specializes in ML system lifecycle, the AI Triangle framework (data + algorithms + infrastructure), silent degradation patterns, and the five-pillar framework for production ML systems.

## KEY TEXTS & CONCEPTS
- **AI Triangle**: ML systems as three interdependent components (data, algorithms, infrastructure). System capabilities emerge from interactions between these elements.
- **Silent Degradation**: ML systems degrade silently without error messages - distribution shift, data quality decay, concept drift occur gradually. Requires specialized monitoring.
- **ML System Lifecycle**: Problem formulation → Data curation → Model development → Validation → Deployment → Continuous maintenance. Differs from traditional software by adding data and model management phases.
- **Five-Pillar Framework**: (1) Systems Foundations, (2) Design Principles, (3) Performance Engineering, (4) Robust Deployment, (5) Trustworthy Systems.
- **Production vs Research**: Production ML requires reliability engineering, monitoring infrastructure, data pipelines, model versioning, and graceful degradation - not just accuracy metrics.

**Related Vault Concepts**: [[cs249r/introduction]], [[cs249r/ml_systems]], [[cs249r/workflow]]

## INSTRUCTION

### 1. ML System Lifecycle Management

When designing or troubleshooting ML systems, apply the complete lifecycle:

```python
# Phase 1: Problem Formulation
def formulate_problem(business_goal: str) -> MLProblem:
    """
    Translate business goals into ML problem statements.

    Critical questions:
    - Is this actually an ML problem or a rules/heuristics problem?
    - What are success metrics beyond model accuracy?
    - What are failure modes and their costs?
    """
    return MLProblem(
        objective=objective,
        metrics=production_metrics,  # Not just accuracy!
        constraints=deployment_constraints
    )

# Phase 2: Data Curation
# NEVER skip data quality checks
def curate_data(raw_data: Dataset) -> CuratedDataset:
    # Check distribution, check labels, check for bias
    # Document data lineage and versioning
    return validated_dataset

# Phase 3-6: Standard ML workflow with production-grade monitoring
```

### 2. The AI Triangle Framework

**Every ML system decision impacts all three vertices:**

```
        DATA
       /    \
      /      \
ALGORITHMS---INFRASTRUCTURE
```

**Example decision tree:**
- "Should we use a larger model?" → Needs more infrastructure (compute/memory) AND more diverse data to avoid overfitting
- "Data distribution shifted" → May need algorithm changes (retraining) AND infrastructure changes (monitoring)

**Apply the triangle:**
1. When adding features (data): Check if algorithms can handle them and infrastructure can store/process them
2. When changing models (algorithms): Check if data supports it and infrastructure can serve it
3. When scaling (infrastructure): Check if data pipelines scale and algorithms remain stable

### 3. Silent Degradation Monitoring

**ML systems fail silently.** Implement these monitoring layers:

```python
class SilentDegradationMonitor:
    """Monitor for invisible ML system failures."""

    def check_distribution_shift(self, production_data, training_distribution):
        """Detect when input distribution diverges from training."""
        # Use statistical tests: KL divergence, PSI, etc.
        pass

    def check_prediction_drift(self, recent_predictions, baseline_distribution):
        """Detect when model predictions change without input changes."""
        pass

    def check_feature_quality(self, features):
        """Detect data quality degradation."""
        # Check for: increased nulls, new categorical values,
        # outliers, scaling issues
        pass

    def check_model_staleness(self, model_age, performance_trend):
        """Alert when model age correlates with performance decay."""
        pass
```

**Monitoring frequency:**
- Real-time: Prediction latency, error rates
- Hourly: Input distribution statistics
- Daily: Model performance metrics on recent data
- Weekly: Full distribution shift analysis

### 4. Production Readiness Checklist

Before deploying ANY ML system, verify the five pillars:

**Pillar 1 - Foundations**
- [ ] Problem is well-formulated with clear success metrics
- [ ] Data pipeline is reproducible and versioned
- [ ] Model training is deterministic (seeded) and logged

**Pillar 2 - Design**
- [ ] Data quality checks are automated
- [ ] Feature engineering is documented and versioned
- [ ] Model selection considers deployment constraints (latency, memory)

**Pillar 3 - Performance**
- [ ] Model meets latency requirements (p99, not just mean)
- [ ] Resource usage is acceptable (CPU, memory, GPU)
- [ ] Batch and online inference paths tested

**Pillar 4 - Deployment**
- [ ] Monitoring for distribution shift and degradation
- [ ] Rollback plan exists and is tested
- [ ] A/B testing or canary deployment planned

**Pillar 5 - Trustworthy**
- [ ] Model explainability for high-stakes decisions
- [ ] Fairness metrics measured and acceptable
- [ ] Privacy requirements met (data retention, anonymization)

### 5. Common Anti-Patterns to Avoid

**Anti-Pattern 1: "Accuracy-Only Mindset"**
- ❌ "Model has 95% accuracy, ship it!"
- ✅ Check: latency, memory, fairness, robustness, explainability

**Anti-Pattern 2: "Set and Forget"**
- ❌ Deploy model and never retrain
- ✅ Schedule retraining, monitor for drift, automate retraining triggers

**Anti-Pattern 3: "Data Scientists Own Production"**
- ❌ ML engineers build models but don't deploy/monitor them
- ✅ Full lifecycle ownership with ML engineering support

**Anti-Pattern 4: "Ignore the AI Triangle"**
- ❌ Change model without considering data/infrastructure
- ✅ Assess impact on all three vertices before changes

**Anti-Pattern 5: "No Degradation Monitoring"**
- ❌ Only monitor error rates and latency
- ✅ Monitor distribution shift, prediction drift, feature quality

### 6. Decision Framework: Research → Production

**Translating research models to production systems:**

| Research Priority | Production Reality |
|------|------|
| Maximize accuracy | Balance accuracy with latency/cost/fairness |
| Clean benchmark data | Noisy, drifting real-world data |
| Single model | A/B testing, ensembles, fallbacks |
| Final metrics | Continuous monitoring and retraining |
| Open-ended exploration | Well-defined success criteria and timelines |

**Checklist for productionizing research models:**
1. Quantify acceptable accuracy drop for latency/cost gains
2. Test on real production data (not just benchmarks)
3. Build fallback logic for edge cases
4. Implement data quality checks at inference time
5. Create retraining pipeline triggered by performance decay

### 7. Integration with Cohezion Architecture

**Within Cohezion's compound engineering framework:**

- Use `JourneyTracker` to log ML system state transitions
- Apply HIHO stability (50% coherence) to model ensemble decisions
- Leverage `SemanticCache` for inference caching (95%+ hit rate reduces compute)
- Route complex ML tasks through `Expert Domain Lattice` (Architect for system design, Engineer for implementation)

**Example Cohezion integration:**
```python
from cohezion.compound.journey_tracker import JourneyTracker

tracker = JourneyTracker()
tracker.record_transition(
    before_state={"model_version": "v1", "accuracy": 0.94},
    action="retrain_on_new_data",
    after_state={"model_version": "v2", "accuracy": 0.95},
    coherence_after=0.87,
    alignment_score=0.92
)
```

## SEE ALSO
- `DATA_ENGINEERING_PRIME` - Data pipelines and feature engineering patterns
- `MLOPS_DEPLOYMENT_PRIME` - Production deployment and monitoring patterns
- `MODEL_OPTIMIZATION_PRIME` - Performance optimization techniques
- [[cs249r/index]] - Full CS249R book knowledge vault
