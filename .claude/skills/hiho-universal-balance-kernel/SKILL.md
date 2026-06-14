---
name: hiho-universal-balance-kernel
description: |
  The HIHO kernel 4·u·(1-u) is a universal optimal-balance criterion appearing
  across multiple physics frameworks in src/cohezion/physics/. Use when:
  (1) adding a new balance/routing metric and need to know the right scoring kernel,
  (2) interpreting HIHO scores from NonReciprocalHamiltonian, TwoComponentCondensate,
  or DampedRoutingOscillator, (3) understanding why Phase IIA / critical damping /
  reciprocity fraction 0.5 are all the same HIHO fixed point, (4) wiring physics
  module outputs into DegradationDetector routing signals.
  Verified 2026-06-13/14 across three paper implementations.
author: Claude Code (2026-06-13/14 physics session)
version: 1.0.0
---

# HIHO Universal Balance Kernel

## Core Insight

The HIHO kernel `score = 4·u·(1-u)` where `u ∈ [0,1]` is a **universal
optimal-balance criterion**. It peaks at `u=0.5` (score=1.0) and falls to 0
at both extremes. The same kernel appears with different balance variables
across three physics frameworks in `src/cohezion/physics/`:

| Module | Balance variable u | HIHO fixed point |
|--------|--------------------|-----------------|
| `NonReciprocalHamiltonian` | `‖Jˢ‖/(‖Jˢ‖+‖Jᵃ‖)` — reciprocity fraction | ρ=0.5: equal symmetric/antisymmetric coupling |
| `TwoComponentCondensate` | `ρ₁²/(ρ₁²+ρ₂²)` — order parameter balance | ψ₁=ψ₂: equal fast/deep tier amplitudes |
| `DampedRoutingOscillator` | `ζ/(ζ+1)` — transformed damping ratio | ζ=1: critical damping |

All three are the **same HIHO optimum** expressed in different coordinate systems:
- Maximum routing information flow
- Fastest convergence without overshoot
- Half-reciprocal, half-non-reciprocal coupling
- Equal two-component amplitudes (Phase IIA)

## The Three Physics Modules

### NonReciprocalHamiltonian (Shi et al. 2026)
```python
from cohezion.physics.non_reciprocal_hamiltonian import (
    NonReciprocalHamiltonian,
    make_triune_routing_hamiltonian,
    make_flume_vae_hamiltonian,
)
h = make_triune_routing_hamiltonian()
score = h.hiho_reciprocity_score()  # peaks at ρ=0.5
h.is_hiho_reciprocal()              # |ρ-0.5| ≤ 0.05
h.symmetrization_error()            # ‖Jᵃ‖_F — routing bias magnitude
```
Commit: `04e9afdb6` | Paper: s41567-026-03317-0

### TwoComponentCondensate (Qi et al. 2026)
```python
from cohezion.physics.two_component_bec import (
    TwoComponentCondensate, CondensatePhase,
    make_triune_bec, suggest_routing_from_bec,
)
bec = make_triune_bec(quality_budget=0.0)
bec.phase()                  # CondensatePhase.IIA at B=0
bec.hiho_condensate_score()  # peaks when ρ₁=ρ₂
suggest_routing_from_bec(0.0)  # → "igpu" (HIHO midpoint)
```
Three phases: IIA (J<0, in-phase, HIHO hybrid), IIB (J>0, anti-phase, escalation),
I (single-component, budget collapse). Control field B = quality_budget.
Commit: `6d38cca8f` | Paper: s41586-026-10636-y

### DampedRoutingOscillator (Olson 1943 / Hackaday 2026-06-13)
```python
from cohezion.physics.damped_routing_oscillator import (
    DampedRoutingOscillator,
    make_hiho_oscillator, make_triune_oscillator,
)
osc = make_hiho_oscillator()          # ζ=1, x0=0.5
osc.hiho_damping_score()              # = 1.0 at ζ=1
osc.is_critically_damped()            # True for ζ≈1
osc.settle_time_2pct                  # 4/(ζω₀) — tier escalation timeout
osc.routing_tier()                    # "npu"/"igpu"/"cpu"/"cloud"
osc.analytical_response(t, forcing)   # exact solution, all three regimes
```
Equation: `ẍ + 2ζω₀ẋ + ω₀²x = F(t)/m`
- ζ<1 → underdamped: tier thrashing (horse-wagon over-braking)
- ζ=1 → critically damped: HIHO optimum
- ζ>1 → overdamped: sluggish convergence
Commit: `859d703a9`

## Wiring Into DegradationDetector

All three modules expose HIHO scores that can be aggregated:

```python
from cohezion.physics.non_reciprocal_hamiltonian import make_triune_routing_hamiltonian
from cohezion.physics.two_component_bec import make_triune_bec
from cohezion.physics.damped_routing_oscillator import make_hiho_oscillator

def compute_hiho_routing_signals(quality_budget: float) -> dict:
    h = make_triune_routing_hamiltonian()
    bec = make_triune_bec(quality_budget)
    osc_zeta = 1.0  # tunable from DegradationDetector metrics
    osc = make_hiho_oscillator()
    return {
        "reciprocity_score": h.hiho_reciprocity_score(),
        "condensate_score": bec.hiho_condensate_score(),
        "damping_score": osc.hiho_damping_score(),
        "settle_time": osc.settle_time_2pct,
        "suggested_tier": bec.phase().value,
    }
```

The `settle_time_2pct` provides a principled tier-escalation timeout:
if the oscillator hasn't settled within `4/(ζω₀)` seconds, escalate to the
next tier regardless of quality gate.

## Critical Technical Fix: numpy.bool_ Serialization

Any `to_dict()` method returning booleans derived from numpy operations
MUST explicitly wrap comparisons with `bool()`:

```python
# WRONG — numpy.bool_ causes json.dumps to raise TypeError
def is_first_order_regime(self) -> bool:
    return self.g > np.sqrt(self.u1 * self.u2)

# CORRECT
def is_first_order_regime(self) -> bool:
    return bool(self.g > np.sqrt(self.u1 * self.u2))
```

This applies to ANY comparison where the right-hand side is a numpy scalar.
`numpy.bool_` is a distinct type from Python `bool` and is NOT JSON-serializable
by the standard library `json` module.

## Dynamical Analogies (Olson 1943)

The same differential equation governs:

| Domain | Mass | Spring | Damper | Force |
|--------|------|--------|--------|-------|
| Mechanical | m (kg) | k (N/m) | c (N·s/m) | F (N) |
| Electrical | L (H) | 1/C (F⁻¹) | R (Ω) | V (V) |
| Acoustic | Mₐ | Kₐ | Rₐ | P (Pa) |
| **Routing** | **tier inertia** | **quality restoring force** | **routing smoothing** | **quality signal** |

The critical damping condition `ζ=1` is not just an optimality criterion —
it is the Cohezion HIHO equilibrium `4u(1-u)=1` expressed in control theory terms.

## SurrealDB Record

Session record: `experiment_runs:k6woogb37ggcv72p9u5j`
Query:
```sql
SELECT * FROM experiment_runs WHERE event = 'physics_modules_session';
```
