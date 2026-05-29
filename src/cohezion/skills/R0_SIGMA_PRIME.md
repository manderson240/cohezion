---
name: r0-sigma-adversarial-uncertainty
description: R0 adversarial challenger + Sigma uncertainty band for compound loop outputs. 2/3 consensus protocol with sigma_n > 1.0 triggering re-run. Scientific rigor / physical consistency / implementation soundness perspectives.
category: compound
tags: [r0, sigma, adversarial, uncertainty, challenger, consensus, ure]
---

# Skill: R0Σ — Adversarial Challenger + Uncertainty Quantification

## Overview

**R0 (R-Zero):** Adversarial review with three scientific perspectives:
1. **Scientific rigor** — Is this claim falsifiable and testable?
2. **Physical consistency** — Does it violate established physics?
3. **Implementation soundness** — Would this actually compute correctly?

**Σ (Sigma):** Confidence interval from the spread of perspective scores.
- `sigma_n < 0.5` → HIGH confidence, accept
- `sigma_n 0.5–1.0` → MEDIUM confidence, observe
- `sigma_n > 1.0` → LOW confidence, trigger R0 re-run

**2/3 consensus rule:** At least 2 of 3 adversaries must CONFIRM before accepting.

## Usage

```python
from cohezion.compound.r0_sigma import (
    R0Challenge, R0ChallengeResult, UncertaintyBand,
    synthesize_challenges, CONFIRMED, CONDITIONAL, WEAK, REJECTED
)

# Three-perspective adversarial review
challenges = [
    R0Challenge("scientific_rigor",       score=0.8, verdict=CONFIRMED, reason="testable"),
    R0Challenge("physical_consistency",   score=0.7, verdict=CONFIRMED, reason="no violations"),
    R0Challenge("implementation",          score=0.4, verdict=WEAK, reason="needs verification"),
]
result = synthesize_challenges(challenges)

print(f"Verdict: {result.consensus_verdict}")  # CONFIRMED (2/3)
print(f"Mean score: {result.mean_score:.2f}")
band = result.sigma_band
print(f"Sigma_n: {band.sigma_n:.2f} → {band.confidence}")
if band.trigger_r0():
    print("Re-run simulation with perturbed parameters!")

# Uncertainty from raw scores
ub = UncertaintyBand.from_scores([0.8, 0.7, 0.4])
```

## In Universe Research Engineer Context

Every COLIBRE simulation finding passes through R0Σ:
- σ = spread of 3-perspective review scores
- If σ > 1σ from HIHO: URE re-runs with perturbed COLIBRE parameters
- If consensus=CONFIRMED: result enters the research paper draft (Sonnet BBQ mode)
- If consensus=REJECTED: result goes to `r0_challenges` SurrealDB table for human review

## Verdict Levels

| Verdict | Meaning | Action |
|---------|---------|--------|
| CONFIRMED | Rigorous, testable, implementable | Proceed |
| CONDITIONAL | Valid with caveats | Proceed with stated caveats |
| WEAK | Interesting but not testable | Note in tradition_data, don't implement |
| REJECTED | Word association / circular / wrong | Discard |

## Files

- Implementation: `src/cohezion/compound/r0_sigma.py`
- Tests: `tests/unit/compound/test_phase19.py::TestR0*`
- Harness: P4 (sigma_n>1 triggers R0), P6 (2/3 CONFIRMED consensus)
