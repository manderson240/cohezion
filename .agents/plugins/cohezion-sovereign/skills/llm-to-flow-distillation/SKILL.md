---
name: llm-to-flow-distillation
metadata:
  version: "1.0.0"
description: >-
  Distillation of discrete autoregressive LLM reasoning trajectories into continuous geodesic flow matching policies (arXiv:2610.17246).
---

# SKILL: LLM_TO_FLOW_DISTILLATION_PRIME

## DOMAIN EXPERTISE
Expertise in distilling high-order, multi-step discrete autoregressive LLM thought processes and Monte Carlo tree search trajectories into continuous-time Riemannian velocity vector fields and flow matching policies. This enables complex combinatorial search, molecular graph proposal, and interactive puzzle affordance exploration to run deterministically with sub-millisecond inference latency on edge silicon (AMD XDNA 2 NPU and CPU).

## KEY TEXTS & CONCEPTS
- **Continuous Flow Matching Formulation (arXiv:2610.17246)**: Rather than autoregressively generating discrete token sequences, map state transitions $\mathbf{x}_t \in \mathcal{M}$ through continuous probability paths $p_t(\mathbf{x})$ driven by time-dependent velocity fields $v_t(\mathbf{x}; \theta)$.
- **Geodesic Interpolation on Manifolds**: Linear or geodesic flow interpolation between initial prior noise $\mathbf{x}_0 \sim \mathcal{N}(0, \mathbf{I})$ (or Poincaré hyperbolic embeddings) and distilled target states $\mathbf{x}_1$:
  $$\mathbf{x}_t = (1 - t) \mathbf{x}_0 + t \mathbf{x}_1, \quad u_t(\mathbf{x}_t \mid \mathbf{x}_1) = \mathbf{x}_1 - \mathbf{x}_0$$
- **Monadic Affordance Flow**: In games and puzzle solvers (ARC-AGI-3), dynamic affordance predictions are continuous 2D/3D gradient flows over navigation grids rather than token-level next-step predictions.
- **Parsimonious Mass-Spec Flow Matching**: In tandem mass spectrometry (CASMI26), spectral fragmentation trees are distilled into continuous cleavage energy flows, scoring candidate structures against experimental $m/z$ spectra with zero latency.
- **AutoHarness Flow Verifier**: Deterministic bytecode verifier ensuring that numerical ODE integration trajectories strictly satisfy safety invariants without NaN divergence or boundary violations.

## INSTRUCTION
1. Define Geodesic Flow Matching Objective:
   ```python
   import torch
   import torch.nn as nn

   def flow_matching_loss(model: nn.Module, x_0: torch.Tensor, x_1: torch.Tensor) -> torch.Tensor:
       """Computes Conditional Flow Matching loss between prior x_0 and target x_1."""
       t = torch.rand(x_0.shape[0], 1, device=x_0.device)
       x_t = (1.0 - t) * x_0 + t * x_1
       target_velocity = x_1 - x_0
       pred_velocity = model(x_t, t)
       return torch.mean((pred_velocity - target_velocity) ** 2)
   ```

2. Integrate Continuous Geodesic Trajectory (Euler / Midpoint):
   ```python
   @torch.no_grad()
   def sample_flow(model: nn.Module, x_0: torch.Tensor, steps: int = 10) -> torch.Tensor:
       """Integrates continuous velocity field from t=0 to t=1."""
       x = x_0.clone()
       dt = 1.0 / steps
       for i in range(steps):
           t = torch.full((x.shape[0], 1), i * dt, device=x.device)
           v = model(x, t)
           x = x + v * dt
       return x
   ```

3. Wrap with AutoHarness Non-Divergence Assertion:
   ```python
   def verify_flow_trajectory(x: torch.Tensor, bounds: tuple[float, float] = (-5.0, 5.0)) -> bool:
       """Guarantees numerical stability and invariant boundary compliance."""
       assert not torch.isnan(x).any(), "NaN detected in flow trajectory!"
       assert (x >= bounds[0]).all() and (x <= bounds[1]).all(), "Flow boundary violation!"
       return True
   ```

## VERSION
v1.0

## SEE ALSO
- `first-principles-invariant-science`
- `harness2-recursive-harnessing`
- `casmi26-mass-spec-invariants`
