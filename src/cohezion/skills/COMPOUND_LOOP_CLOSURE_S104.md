---
id: skill-compound-loop-closure
name: Closing the Compound Engineering Loop with HIHO
domain: Compound AI
version: v1.0
tier: PRIME
coherence: 1.0
parent: meta-learning
related:
  - [[skill-telemetry-analysis]]
  - [[skill-journey-analyzer]]
  - [[skill-coherence-thresholds]]
aliases:
  - Execute-Telemetry-Refinement Loop
  - Canonical Skill Extraction
created: 2026-04-20
session: S104
---

# Skill: Closing the Compound Engineering Loop

## Context
The compound engineering loop was incomplete: telemetry was generated but never fed back to skill refinement.

## The Closed Loop
```
Before (Broken):
  Execute → Telemetry → .telemetry/ (sits unused)

After (Working):
  Execute → Telemetry → JourneyAnalyzer → SkillRefiner → Better Skills ↺
```

## Implementation

### 1. Generate Telemetry at Scale
```python
# Run skill multiple times WITH telemetry
from cohezion.compound.telemetry import CompoundTelemetry

telemetry = CompoundTelemetry()
for i in range(10):
    with telemetry.span('validation', request_id=f'sv-{i}', skill_name='validator'):
        # Run actual skill
        run_skill_validator()
```

### 2. Analyze Patterns
```bash
# Extract coherence metrics
uv run python src/cohezion/scripts/analyze_telemetry.py

# Output: .telemetry/analysis.json
{
  "validator": {
    "executions": 20,
    "success_rate": 1.0,
    "coherence_proxy": 1.0,
    "recommendation": "Pattern stable - extract as canonical"
  }
}
```

### 3. Auto-Refine Based on HIHO Thresholds
| Coherence | Classification | Action |
|-----------|---------------|--------|
| ≥0.75 | **Canonical** | Extract as pattern |
| 0.5-0.75 | Stable | Use as standard |
| 0.4-0.5 | Critical | Monitor |
| <0.4 | Unstable | Refine |

### 4. Extract Canonical Skill
```bash
# When coherence ≥0.75 after 10+ executions
# Skill becomes canonical
# Documented in docs/patterns/canonical_skills.jsonl
```

## Key Metric: Compound Returns
Each execution improves future executions.

Validation: `validator` skill went from 0 executions → 20 executions → **canonical status**

## V-Model Application
| Phase | Activity | Evidence |
|-------|----------|----------|
| Requirements | Define coherence threshold | HIHO 0.5 |
| Implementation | Build telemetry + analysis | ✅ Complete |
| Unit Test | Verify single execution | ✅ Works |
| Integration | Chain: telemetry → analysis | ✅ Working |
| System Test | 10+ executions aggregated | ✅ 20 executions |
| Validation | Canonical extraction | ✅ validator canonical |

## HIHO as Gateway
**HIHO 0.5** is the decision boundary:
- <0.5: Block execution, decompose
- =0.5: Uncertainty maximum, monitor
- >0.5: Proceed with confidence
- ≥0.75: Extract pattern

## Backlinks
- [[CompoundExecutor]]
- [[HIHO 0.5 threshold]]
- [[RetrospectionEngine]]
- [[Session 104]]

---
canonical: true
coherence_verified: 2026-04-20
success_rate: 1.0
executions: 20
