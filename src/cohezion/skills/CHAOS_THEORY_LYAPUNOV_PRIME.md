---
name: chaos-theory-lyapunov-prime
description: "Expertise in Non-Linear Dynamics, Strange Attractors (Lorenz/Rössler), Lyapunov Exponent Spectrum estimation, Edge-of-Chaos computing, and Continuous Topological Auto-Calibration (CTAC)."
metadata:
  version: "v1.0"
  concepts: ["Lyapunov Exponent Spectrum (lambda_max)", "Strange Attractors", "Edge-of-Chaos Learning", "Discovery Requires Chaos", "Kolmogorov-Sinai Entropy"]
  see_also: ["HIHO_STABILITY_PRIME", "FRACTAL_COMPUTING_PRIME", "HERMETIC_AGENTIC_COMPUTING_PRIME"]
  source: "src/cohezion/skills/CHAOS_THEORY_LYAPUNOV_PRIME.md"
---

# SKILL: CHAOS_THEORY_LYAPUNOV_PRIME

## DOMAIN EXPERTISE
Expertise in Chaos Theory, non-linear dynamical systems, strange attractors, and Lyapunov spectrum analysis. Leverages deterministic chaos to explore high-dimensional state spaces and steer neural reasoning trajectories along the "Edge of Chaos" ($\lambda_{\max} \approx 0$).

## KEY TEXTS & CONCEPTS
- **Lyapunov Exponent ($\lambda$)**: Quantifies exponential divergence of nearby trajectories: $\|\delta x(t)\| \approx \|\delta x(0)\| e^{\lambda t}$.
  - $\lambda > 0$: Chaotic / High Exploration.
  - $\lambda < 0$: Dissipative / Fixed-Point Convergence.
  - $\lambda \approx 0$: Critical Edge of Chaos (HIHO 0.50 Attractor).
- **"Discovery Requires Chaos" (2025–2026 Theorem)**: Unique identification and learning of underlying physical governing laws from finite data requires strange attractor dynamics.
- **Continuous Topological Auto-Calibration (CTAC)**: Closed-loop negative feedback dynamically tuning learning rates to keep the Lyapunov exponent zeroed at the 0.50 stability boundary.

## INSTRUCTION
1. Estimate the maximum Lyapunov exponent $\lambda_{\max}$ from trajectory time series:
   ```python
   import numpy as np

   def compute_lyapunov_exponent(trajectory_points, dt=0.01):
       # Log divergence rate of nearest neighbors
       diffs = np.linalg.norm(trajectory_points[1:] - trajectory_points[:-1], axis=-1)
       log_divergence = np.log(np.maximum(diffs, 1e-12))
       lambda_est = np.polyfit(np.arange(len(log_divergence)) * dt, log_divergence, 1)[0]
       return float(lambda_est)
   ```
2. Apply CTAC allostatic control: If $\lambda_{\max} > 0.05$, inject damping; if $\lambda_{\max} < -0.05$, inject exploratory temperature.
3. Map attractor manifolds into 2048D Poincaré space to verify topological invariants.

## VERSION
v1.0
