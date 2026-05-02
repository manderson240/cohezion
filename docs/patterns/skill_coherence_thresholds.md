# Skill Coherence Thresholds (HIHO-Based)

**Document**: When skills become canonical  
**Basis**: HIHO 0.5 threshold (Shannon maximum uncertainty)
**Validated**: 2026-04-20 via telemetry analysis

---

## Coherence Levels

| Level | Range | Pattern | Action |
|-------|-------|---------|--------|
| **Optimal** | 0.75-1.0 | Stable, predictable | ✓ Extract as canonical |
| **Stable** | 0.5-0.75 | Reliable with variance | ✓ Use as standard pattern |
| **Critical** | 0.4-0.5 | At HIHO threshold | ⚠ Monitor closely |
| **Unstable** | 0.25-0.4 | High variance | ✗ Needs refinement |
| **Degraded** | 0.0-0.25 | Poor reliability | ✗ Major rework required |

## Becoming Canonical

A skill becomes **canonical** when:
1. **≥10 executions** (minimum sample size)
2. **Success rate ≥ 90%** (reliable)
3. **Coherence ≥ 0.75** (predictable)
4. **Inflection rate < 30%** (stable pattern)

## Degradation Signals

Watch for skill degradation:
- Success rate drops below 90%
- Inflection rate exceeds 30%
- Latency doubles from baseline
- Coherence falls below HIHO 0.5

## Telemetry Pattern

```python
{
    "skill_name": "validator",
    "coherence_proxy": success_rate * efficiency,
    "recommendation": _threshold_check(coherence)
}
```

## Application

Use this threshold for:
- PR approval gates
- Skill promotion/demotion
- Agent training data selection
- CI pass/fail criteria
- Compound loop feedback

**Reference**: 2026-04-20 validator analysis showed 1.0 coherence after 10 runs.
