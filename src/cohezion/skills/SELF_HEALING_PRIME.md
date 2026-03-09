---
name: self-healing
description: Self-healing AI system patterns for detecting performance drift,
  diagnosing failures, and applying autonomous corrections. Use when setting up
  health monitoring, implementing auto-recovery, or when user mentions "self
  healing", "drift detection", "auto correction", "health check", or
  "autonomous recovery".
metadata:
  version: "0.1"
  legacy-name: SELF_HEALING_PRIME
---

# SKILL: SELF_HEALING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **self-healing AI systems** - detecting performance drift, diagnosing failures, and applying autonomous corrections.

## KEY TEXTS & CONCEPTS
- **Drift Detection** – Monitor metrics against baselines
- **LLM-based Diagnosis** – Use language models to analyze failures
- **Autonomous Correction** – Auto-apply fixes for known issues
- **Unicron** – Self-healing LLM training framework (HuggingFace)
- **H-LLM** – Self-healing ML framework (arxiv)

## INSTRUCTION

### 1. Drift Detection
```python
from cohezion.healing import get_healing_system

system = get_healing_system()
system.detector.set_baseline("swarm", "latency", 100.0)

status = system.detector.check("swarm", "latency", 150.0)
if status.status != "healthy":
    print(f"Drift detected: {status}")
```

### 2. Diagnosis
```python
diagnosis = system.diagnostician.diagnose(status)
print(f"Issue: {diagnosis.issue}")
print(f"Cause: {diagnosis.probable_cause}")
print(f"Action: {diagnosis.recommended_action}")
```

### 3. Auto-Correction
```python
await system.corrector.apply_correction(diagnosis)
```

### 4. Full Health Check
```python
issues = await system.health_check()
healed = await system.heal(issues)
print(f"Healed {healed} issues")
```

## PATTERNS

### Known Issue Patterns
| Metric | Threshold | Status | Action |
|--------|-----------|--------|--------|
| latency_ms | >120% baseline | degraded | Swap to faster model |
| quality_score | <0.6 | failing | Benchmark alternatives |
| available | 0 | failing | Restart service |

## CITATIONS
- [Unicron](https://huggingface.co/papers/unicron)
- [H-LLM Framework](https://arxiv.org/abs/2312.xxxxx)
- [Reflexion](https://arxiv.org/abs/2303.11366)

## VERSION
v0.1

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME.md
- OLLAMA_MANAGEMENT_PRIME.md
