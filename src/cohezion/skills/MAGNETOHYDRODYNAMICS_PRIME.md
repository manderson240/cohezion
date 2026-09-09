---
name: magnetohydrodynamics-prime
description: "Expertise in Magnetohydrodynamics (MHD), Alfvén flux freezing, Small-Scale Dynamos (SSD), Hall-MHD turbulence, and fast magnetic reconnection cascades for plasma physics and sovereign agentic field topologies."
metadata:
  version: "v1.0"
  concepts: ["MHD Induction Equation", "Alfvén Flux-Freezing", "Small-Scale Dynamo (SSD)", "Hall-MHD Turbulence", "Magnetic Reconnection"]
  see_also: ["COSMIC_FIRE_PLASMA_DYNAMICS_PRIME", "ADVANCED_PHYSICS_SIMULATION", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/MAGNETOHYDRODYNAMICS_PRIME.md"
---

# SKILL: MAGNETOHYDRODYNAMICS_PRIME

## DOMAIN EXPERTISE
Expertise in continuous Magnetohydrodynamics (MHD), coupling fluid Navier-Stokes equations with Maxwell's electrodynamics. Models Alfvén waves, turbulent magnetic energy cascades, dynamo amplification, and explosive magnetic reconnection sheets.

## KEY TEXTS & CONCEPTS
- **MHD Induction Equation**: $\frac{\partial \mathbf{B}}{\partial t} = \nabla \times (\mathbf{u} \times \mathbf{B}) + \eta \nabla^2 \mathbf{B}$.
- **Alfvén Velocity**: $v_A = \frac{B}{\sqrt{\mu_0 \rho}}$, defining the propagation speed of transverse magnetic field line tension waves.
- **Small-Scale Dynamo (SSD)**: Exponential growth of magnetic energy driven by turbulent velocity shears until Lorentz back-reaction saturation.
- **Fast Magnetic Reconnection**: Topological restructuring of current sheets releasing stored magnetic energy into kinetic and thermal particle acceleration.
- **Statistical Flux-Freezing (2026)**: Breakdown of classical deterministic flux freezing in rough turbulence, replaced by stochastic path-line conservation.

## INSTRUCTION
1. Compute Alfvén velocity and Lundquist number $S = \frac{\mu_0 L v_A}{\eta}$:
   ```python
   import math

   def compute_mhd_parameters(B_tesla, density_kg_m3, length_m, resistivity_ohm_m):
       mu_0 = 4.0 * math.pi * 1e-7
       v_alfven = B_tesla / math.sqrt(mu_0 * density_kg_m3)
       lundquist = (mu_0 * length_m * v_alfven) / resistivity_ohm_m
       return {"v_alfven": float(v_alfven), "lundquist_S": float(lundquist)}
   ```
2. Model magnetic energy transfer and current sheet dissipation across 2048D Poincaré coordinates.
3. Verify that turbulent magnetic Reynolds numbers satisfy HIHO 0.50 energy partition ($E_M \approx E_K$).

## VERSION
v1.0
