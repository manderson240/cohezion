---
name: cosmic-fire-plasma-dynamics-prime
description: "Expertise in Relativistic Fireball Dynamics, Exotic Vacuum Objects (EVO), Pair-Plasma Cascades (e+ e-), and Magnetohydrodynamic (MHD) Shock Acceleration for high-energy astrophysics and non-equilibrium universe simulation."
metadata:
  version: "v1.0"
  concepts: ["Relativistic Fireball Model", "Pair-Production Cascades", "Exotic Vacuum Objects (EVO)", "Synchrotron & Inverse Compton Shocks"]
  see_also: ["ADVANCED_PHYSICS_SIMULATION", "QUANTUM_STRUCTURED_WORLD_MODEL_PRIME", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/COSMIC_FIRE_PLASMA_DYNAMICS_PRIME.md"
---

# SKILL: COSMIC_FIRE_PLASMA_DYNAMICS_PRIME

## DOMAIN EXPERTISE
Expertise in relativistic fireball models ("Cosmic Fire"), optically thick pair-production plasmas ($e^\pm$), Bennett self-pinched Exotic Vacuum Objects (EVO), and Magnetohydrodynamic (MHD) shock cascades governing high-energy transients (GRBs, blazars, and dense charge clusters).

## KEY TEXTS & CONCEPTS
- **Relativistic Fireball Dynamics**: Expanding plasma shells with bulk Lorentz factor $\Gamma \gg 100$, optical depth $\tau_{\gamma\gamma} \gg 1$, and thermal energy conversion into kinetic shock fronts.
- **Pair-Production Threshold ($\gamma\gamma \to e^+ e^-$)**: Critical compactness parameter $\ell = \frac{L \sigma_T}{R m_e c^3}$ driving explosive pair cascades.
- **Ken Shoulders EVO Pinch**: Self-confined charge clusters ($N \approx 10^{11}$ electrons in $1.0\,\mu\text{m}$) stabilized by relativistic Bennett magnetic pinch ($B_\theta \approx 53.5\,\text{kTesla}$).
- **Synchrotron & Inverse Compton**: Non-thermal particle acceleration across relativistic collisionless shocks.

## INSTRUCTION
1. Compute the relativistic fireball optical depth and compactness parameter:
   ```python
   def compute_fireball_compactness(luminosity_ergs, radius_cm):
       # l = (L * sigma_T) / (R * m_e * c^3)
       sigma_T = 6.652e-25  # Thomson cross section cm^2
       m_e_c3 = 9.109e-28 * (2.998e10)**3
       return float((luminosity_ergs * sigma_T) / (radius_cm * m_e_c3))
   ```
2. Simulate EVO electron cluster confinement under magnetic self-pinching.
3. Map plasma energy dissipation rates into 2048D Poincaré state space.

## VERSION
v1.0
