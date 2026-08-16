---
name: research-squad-prime
description: "The Research Squad is an autonomous team that optimizes the compound system itself through empirical research."
---

# SKILL: RESEARCH_SQUAD_PRIME

**Domain Expertise:** Autonomous compound system optimization through empirical research and skill refinement

**Key Concepts:**
- Self-improving compound loops
- Automated skill refinement
- Cost-aware optimization
- Thermodynamic quality validation
- Recursive self-optimization

**Instruction:**

## Research Squad Activation

The Research Squad is an autonomous team that optimizes the compound system itself through empirical research.

### Core Mission

Monitor compound system metrics, detect optimization opportunities, run experiments, apply refinements, and validate improvements.

### Squad Composition

**Lead: ResearchAgent**
- Runs optimization experiments on compound subsystems
- Tracks cost and quality metrics
- Reports findings to SkillRefiner

**Support: PatternScout**
- Detects optimization patterns in compound metrics
- Identifies degradation signals
- Suggests experiment directions

**Support: QualityAnalyst**
- Validates improvements statistically
- Runs thermodynamic quality checks
- Ensures changes don't break existing functionality

### Execution Flow

1. **Monitor Phase** (Continuous)
   - Poll GlobalMetricsAggregator for degradation signals
   - Check thermodynamic entropy production rates
   - Alert if coherence drops below threshold

2. **Experiment Phase** (Triggered)
   - Formulate hypothesis ("Skill X can be optimized")
   - Design experiment with ResearchAgent
   - Run 10-100 experiments with cost budget
   - Compare against baseline

3. **Refinement Phase** (On success)
   - Extract learnings from successful experiments
   - Update skill definition via SkillRefiner
   - Apply SkillConsensusVoter validation
   - Generate PR update

4. **Validation Phase** (Always)
   - Run 24-hour observation period
   - Verify metrics improvement
   - Check for regressions
   - Rollback if needed

### Optimization Targets

**Priority 1: CompoundExecutor**
- Optimize retry strategies
- Improve batch processing
- Refine cost-aware routing

**Priority 2: Skills**
- Auto-refine frequently-used skills
- Update examples based on recent tasks
- Optimize prompt patterns

**Priority 3: Infrastructure**
- Cache hit rate optimization
- Token usage efficiency
- Checkpoint persistence improvements

### Cost Controls

- Max $10 USD per optimization session
- Use cheapest models (phi3:mini) for initial experiments
- Scale up (qwen3-coder:32b) only when needed
- Abort if no improvement after 20 experiments

### Success Criteria

- Statistical significance (p < 0.05)
- 10%+ improvement in target metric
- No regression in other metrics
- Thermodynamic stability maintained
- Cost within budget

### Integration Points

```python
from cohezion.research import ResearchSquad, integrate_with_compound_system

# Create integrated squad with cost controls
squad = integrate_with_compound_system()

# Optimize a degraded skill
result = squad.optimize_skill("skill_name", baseline_metric=0.45)

# Apply refinement if improvement significant
if result.optimized:
    squad.apply_refinement(result)
```

### Safety Controls

- Always validate changes in isolated environment
- Rollback capability within 60 seconds
- Human approval required for >$5 changes
- Audit log of all modifications
- Circuit breaker on failed experiments

### Quality Gates

Before applying any refinement:
1. KS test vs baseline distribution
2. ADF stationarity check
3. Variance bifurcation detection
4. Thermodynamic entropy positive
5. Coherence convergence to 0.5

### Example Usage

```python
# Automatic activation from degradation signal
from cohezion.research import ResearchSquad
from cohezion.research.cost_optimization import CostBudget

if metrics.coherence < 0.5:
    squad = ResearchSquad(cost_budget=CostBudget(max_cost_usd=10.0))
    signal = squad.detect_degradation("coding", {"coherence": metrics.coherence})
    if signal:
        result = squad.optimize_skill("coding", signal.current_value)
        if result.optimized:
            squad.apply_refinement(result)
            print(f"Improved: {result.before_metric:.2f} -> {result.after_metric:.2f}")
```

**Version:** 1.0.0
**Last Updated:** 2025-03-10
**See Also:** SKILL_REFINEMENT_PRIME, COMPOUND_EXECUTOR_PRIME, THERMODYNAMIC_METRICS_PRIME


## DOMAIN EXPERTISE
Core autonomous capability specializing in RESEARCH SQUAD PRIME operations within the Cohezion FLUME multi-agent swarm.


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for RESEARCH SQUAD PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## INSTRUCTION

### 1. Initialize Context
```python
from cohezion.flume import PoincareManifoldND
from cohezion.agi.autoharness_policy import AutoHarnessPolicy

policy = AutoHarnessPolicy()
state = PoincareManifoldND.project([0.05] * 2048, target_dim=12)
```

### 2. Execute Deterministic Action
```python
# Verify state invariants with 0ms overhead
res = policy.verify_action("standard_execution", state)
assert res.allowed is True
```


## VERSION
v1.0 (Auto-Standardized & Verified)


## SEE ALSO
- **AUTOHARNESS_POLICY_PRIME**
- **JOURNEY_TRACKING_PRIME**
