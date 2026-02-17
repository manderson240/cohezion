# Leslie Matrix Population Dynamics Specification

## Overview
Age-structured population dynamics for 10,000 quantum agents using Leslie matrix formalism from population ecology.

## Mathematical Model

### Leslie Matrix Structure
```
L = [fertility | survival]

[f0  f1  f2  ...  f59]  <- Fertility row (age-specific reproduction)
[s0  0   0   ...  0   ]  <- Survival from age 0 to 1
[0   s1  0   ...  0   ]  <- Survival from age 1 to 2
[...                  ]
[0   0   0   ...  s58 ]  <- Survival from age 58 to 59
```

Where:
- n = 60 age classes (epochs)
- f_i = fertility at age i (mitosis probability)
- s_i = survival from age i to i+1

### Age Classes
- **Juvenile (0-9)**: f_i = 0, high survival (s = 0.98)
- **Mature (10-50)**: Gaussian fertility peaked at 30, high survival
- **Elderly (51-59)**: f_i = 0, declining survival (s = 0.5 → 0.1)

### Fertility Curve
```python
f_i = 0.3 * exp(-((i - 30)^2) / 200) for i in [10, 50]
```

### Population Projection
```
n_{t+1} = L @ n_t
```

### Dominant Eigenvalue
```
λ = max(eigenvalues(L))
```
- λ > 1: Population grows
- λ = 1: Stable population (target)
- λ < 1: Population declines

## Implementation Classes

### LeslieMatrix
- Builds L matrix
- Computes eigenvalues/vectors
- Projects population forward
- Auto-tunes to λ ≈ 1.0

### AgeStructuredPopulation
- Manages 10,000 agents by age
- Applies survival rates
- Handles reproduction (mitosis)
- Enforces carrying capacity
- Tracks demographics

### Agent Lifecycle
1. **Birth**: Age 0, inherits split quantum state
2. **Growth**: Age += 1 each epoch
3. **Survival**: Probabilistic based on s_i
4. **Reproduction**: If mature + energy + coherence
5. **Death**: Apoptosis with pattern extraction

## Key Metrics
- Population size: 10,000 ± 500
- Age distribution: Matches stable eigenvector
- Growth rate: λ ≈ 1.0
- Doubling time: ~50 epochs (if λ > 1)

## Integration Points
- QuantumAgent: age attribute
- BioelectricMorphospace: age determines preferred well
- ZPEMiner: reproduction costs energy
- JourneyTracker: log lifecycle events
