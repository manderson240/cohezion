---
name: greek-parameters-control
description: Five Greek letter control parameters (alpha-omega-gamma-delta-beta) governing compound loop dynamics for the Universe Research Engineer. Lyapunov-stable convergence to HIHO attractor.
category: compound
tags: [greek, parameters, control, hiho, convergence, universe-research-engineer]
---

# Skill: Greek Parameters Control System

## Overview

Five dimensionless parameters govern the Universe Research Engineer compound loop:

| Symbol | Name | Default | Role |
|--------|------|---------|------|
| **α** (alpha) | Learning rate | 0.05 | SkillRefiner step size per cycle |
| **Ω** (omega) | Destiny attractor | 0.5 | Sarfatti HIHO fixed point |
| **γ** (gamma) | HIHO kernel | 4x(1-x) | Universal coherence formula |
| **δ** (delta) | R0 perturbation | 0.05 | Adversarial challenge magnitude |
| **β** (beta) | KL weight | 0.01 | FLUME VAE regularization (A3 invariant) |

## Equation of Motion

```
x(t+1) = x(t) + (α×γ(x) + β - δ×r0) × (Ω - x)
```

- γ(x) modulates the strength of the destiny pull (maximum at HIHO)
- β×(Ω-x) is Sarfatti's retrocausal correction
- δ×r0 is adversarial resistance from the R0 challenger

**Basin of attraction:** x ∈ (0.082, 0.918) → converges to Ω=0.5.
Below 0.082 or above 0.918: adversarial force overwhelms learning.

## Usage

```python
from cohezion.compound.greek_parameters import GreekParameters

gp = GreekParameters(alpha=0.05, omega=0.5, delta=0.05, beta=0.01)

# Single step
x_next = gp.update(x=0.3, r0_score=0.5)

# Full trajectory
path = gp.trajectory(x0=0.2, steps=50)

# Check convergence
if gp.converged(x_next):
    print("Compound loop at HIHO attractor")

# Serialize for SurrealDB
record = gp.to_dict()  # {alpha, omega, delta, beta, gamma_at_hiho}
```

## Invariants

- β must not exceed 0.015 (A3 invariant: posterior collapse threshold)
- γ(Ω) = 4×0.5×0.5 = 1.0 (peak learning force at HIHO)
- System is Lyapunov-stable at Ω when α×γ(Ω)+β > δ×r0_score

## Files

- Implementation: `src/cohezion/compound/greek_parameters.py`
- Tests: `tests/unit/compound/test_phase19.py::TestGreekParameters`
- Harness: P1 (convergence), P2 (β A3 guard)
