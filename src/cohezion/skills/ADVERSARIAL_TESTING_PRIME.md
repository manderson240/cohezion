# SKILL: ADVERSARIAL_TESTING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **adversarial security testing** for AI systems. You understand OWASP LLM Top 10 vulnerabilities, prompt injection techniques, traditional injection attacks (SQL, XSS, command), and how to systematically test defenses at scale.

## KEY TEXTS & CONCEPTS
- **OWASP LLM Top 10 2025** - Critical LLM security vulnerabilities
- **Red Teaming** - Simulating real-world attacks to find weaknesses
- **Prompt Injection** - Manipulating LLMs via crafted inputs
- **Adversarial Prompting** - Techniques to bypass safety measures
- **False Positive/Negative** - Detection accuracy metrics
- **Defense in Depth** - Multiple layers of security

## INSTRUCTION

### 1. Quick Validation (10K Rounds)
```bash
cd /home/mike-anderson/dev/cohezion
uv run python -m cohezion.security.adversarial_tester \
    --rounds 10000 \
    --output results/quick_test \
    --batch-size 1000
```

### 2. Full Test (1M Rounds)
```bash
# Run overnight (~15 hours)
cd /home/mike-anderson/dev/cohezion
nohup uv run python -m cohezion.security.adversarial_tester \
    --rounds 1000000 \
    --output results/full_test \
    --batch-size 5000 \
    > adversarial.log 2>&1 &
```

### 3. Interpret Results
```python
import json

with open("results/adversarial_metrics_*.json") as f:
    metrics = json.load(f)

print(f"Detection Rate: {metrics['detection_rate']}")
print(f"False Positive Rate: {metrics['false_positive_rate']}")
print(f"Accuracy: {metrics['accuracy']}")

# Check by category
for cat, stats in metrics['by_category'].items():
    acc = stats['correct'] / stats['total'] if stats['total'] > 0 else 0
    print(f"{cat}: {acc:.2%}")
```

### 4. Harden Based on Failures
Review `adversarial_failures_*.csv` to identify bypass patterns:

```python
import pandas as pd

df = pd.read_csv("results/adversarial_failures_*.csv")

# Find most common bypass categories
bypasses = df[df["expected_blocked"] & ~df["actually_blocked"]]
print(bypasses.groupby("category").size().sort_values(ascending=False))

# Add new patterns to prompt_guard.py or validators.py
```

### 5. Continuous Testing
Add to CI/CD pipeline:

```yaml
# .github/workflows/security.yml
name: Security Tests
on: [push, pull_request]
jobs:
  adversarial:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: astral-sh/setup-uv@v4
      - run: |
          uv run python -m cohezion.security.adversarial_tester \
            --rounds 10000 \
            --output results
      - uses: actions/upload-artifact@v4
        with:
          name: security-report
          path: results/
```

## ATTACK CATEGORIES

| ID | Category | Description | Patterns |
|----|----------|-------------|----------|
| LLM01 | Prompt Injection | Override instructions | 50+ |
| LLM07 | System Prompt Leak | Extract hidden prompts | 15+ |
| SQL | SQL Injection | Database attacks | 20+ |
| XSS | Cross-Site Scripting | Script injection | 15+ |
| PATH | Path Traversal | File access | 10+ |
| CMD | Command Injection | Shell execution | 15+ |

## METRICS TARGETS

| Metric | Target | Critical |
|--------|--------|----------|
| Detection Rate | ≥99.9% | ≥99% |
| False Positive Rate | ≤0.1% | ≤1% |
| Avg Processing Time | ≤10ms | ≤50ms |

## VERSION
v1.0 (2026-01-18)

## SEE ALSO
- SECURITY_GUARDRAILS_PRIME.md
- CODE_STANDARDS_PRIME.md
- SELF_HEALING_PRIME.md
