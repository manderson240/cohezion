---
name: thermodynamic-compiler-prime
description: "Expertise in compiling non-equilibrium thermodynamic loss landscapes, Landauer erasure dissipation bounds, and bioelectric free-energy minimization into executable agent action policies."
metadata:
  version: "v1.0"
  concepts: ["Non-Equilibrium Thermodynamics", "Landauer Erasure Bound", "Friston Free Energy", "Onsager Reciprocal Relations"]
  see_also: ["HIHO_STABILITY_PRIME", "ADVANCED_PHYSICS_SIMULATION"]
  source: "src/cohezion/skills/THERMODYNAMIC_COMPILER_PRIME.md"
---

# SKILL: THERMODYNAMIC_COMPILER_PRIME

## DOMAIN EXPERTISE
Expertise in non-equilibrium thermodynamics, Prigogine dissipative structures, Landauer erasure limits ($k_B T \ln 2$), and Friston Active Inference free-energy minimization. Compiles continuous physical gradients into deterministic discrete agent policies.

## KEY TEXTS & CONCEPTS
- **Landauer Principle**: Minimum heat dissipation for bit erasure: $\Delta Q \ge k_B T \ln 2$. Minimizing agent memory churn minimizes thermal entropy.
- **Onsager Reciprocal Relations**: Linear coupling between thermodynamic forces $X_i$ and fluxes $J_i = \sum_j L_{ij} X_j$ with symmetric matrix $L_{ij} = L_{ji}$.
- **Friston Variational Free Energy**: $F = D_{KL}(q(\theta) || p(\theta | y)) - \ln p(y)$. Agent updates minimize epistemic surprise and drift.
- **HIHO Thermodynamic Convergence**: Equilibrium reached at $C = 0.50$, where thermodynamic microstates $W(p) = \binom{N}{pN}$ are maximized.

## INSTRUCTION
1. Compute variational free-energy loss gradients over active agent state trajectories:
   ```python
   def compute_free_energy(q_mu, p_prior_mu, precision=1.0):
       # KL divergence proxy + sensory prediction error
       kl_div = 0.5 * precision * (q_mu - p_prior_mu)**2
       return float(kl_div)
   ```
2. Minimize entropy dissipation during agent state caching and token routing.
3. Align agent action loops with the 0.50 HIHO attractor to preserve cognitive microstate diversity.

## VERSION
v1.0
