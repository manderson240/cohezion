---
title: "Thermodynamics and Phase Transitions"
date: 2026-03-09
tags: [concept, physics, thermodynamics, statistical-mechanics, phase-transitions, entropy]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 18
  synapse_out: 13
---

# Thermodynamics and Phase Transitions

## Definition

Thermodynamics is the study of energy, entropy, and the macroscopic equilibrium properties of systems with many degrees of freedom. Statistical mechanics (Boltzmann, Gibbs) provides the microscopic foundation: macroscopic observables emerge as averages over vast ensembles of microstates. The deepest result of the field is that **phase transitions** — qualitative changes in the macroscopic state of matter — arise from singularities in the partition function as the number of degrees of freedom N → infinity.

A phase transition occurs when a system's free energy develops a non-analyticity as a control parameter (temperature, pressure, magnetic field) crosses a critical value. First-order transitions (ice → water) involve latent heat and discontinuous order parameters. Second-order (continuous) transitions (ferromagnet → paramagnet at Curie temperature) involve diverging correlation lengths, power-law scaling, and universality — the remarkable fact that systems with completely different microscopic physics exhibit identical critical behavior.

## Key Properties

### The Laws of Thermodynamics

**Zeroth Law:** If A is in thermal equilibrium with B, and B with C, then A is in equilibrium with C. (Defines temperature.)

**First Law (energy conservation):**
> dU = δQ - δW = TdS - pdV + μdN

**Second Law (entropy never decreases in isolation):**
> dS ≥ δQ/T  (equality for reversible processes)

The Boltzmann entropy:
> S = k_B ln Ω

where Ω is the number of accessible microstates. For a system at temperature T, the Gibbs entropy:
> S = -k_B Σ_i p_i ln p_i

where p_i = e^{-βE_i}/Z is the Boltzmann probability, β = 1/(k_BT), and Z = Σ_i e^{-βE_i} is the partition function.

**Third Law (Nernst):** As T → 0, S → 0 (for a system with a unique ground state).

### Free Energy and Phase Transitions

The Helmholtz free energy (constant T, V):
> F = U - TS = -k_BT ln Z

The Gibbs free energy (constant T, p):
> G = U - TS + pV = F + pV

Phase transitions occur when G(T,p) develops a non-analyticity:
- **First-order:** G is continuous but ∂G/∂T (entropy S) or ∂G/∂p (volume V) is discontinuous. Latent heat L = TΔS.
- **Second-order (continuous):** G and its first derivatives are continuous, but second derivatives (heat capacity C_p = -T∂²G/∂T², compressibility κ = -V⁻¹∂²G/∂p²) diverge.

### The Ising Model

The simplest model exhibiting a phase transition. N spins s_i = ±1 on a lattice with Hamiltonian:

> H = -J Σ_{<ij>} s_i s_j - h Σ_i s_i

where J > 0 is the ferromagnetic coupling and h is the external field. The partition function:
> Z = Σ_{configs} e^{-βH}

Onsager (1944) solved the 2D Ising model exactly (h = 0), finding:
> T_c = 2J / (k_B ln(1+√2)) ≈ 2.269 J/k_B

Below T_c: spontaneous magnetization m = <s_i> ≠ 0 (ordered phase).
Above T_c: m = 0 (disordered phase).
Near T_c: m ~ |T - T_c|^β with β = 1/8 (in 2D).

### Critical Exponents and Universality

Near a continuous phase transition, physical quantities follow power laws:

| Quantity | Symbol | Exponent | Definition |
|----------|--------|----------|------------|
| Order parameter | m | β | m ~ \|t\|^β (t < 0) |
| Susceptibility | χ | γ | χ ~ \|t\|^{-γ} |
| Heat capacity | C | α | C ~ \|t\|^{-α} |
| Correlation length | ξ | ν | ξ ~ \|t\|^{-ν} |
| Correlation function (at T_c) | G(r) | η | G(r) ~ r^{-(d-2+η)} |

where t = (T - T_c)/T_c is the reduced temperature.

**Universality:** Systems with the same dimension d, symmetry of the order parameter, and range of interactions have IDENTICAL critical exponents — regardless of microscopic details. This is why:
- Water at its critical point
- Uniaxial ferromagnet at Curie temperature
- Binary alloy at mixing transition

all have the same exponents (3D Ising universality class: β ≈ 0.326, γ ≈ 1.237, ν ≈ 0.630).

### Landau Theory

Landau's phenomenological approach: expand the free energy in powers of the order parameter m near T_c:

> F(m, T) = F_0 + a(T)m² + bm⁴ + ...

where a(T) = a₀(T - T_c) changes sign at T_c and b > 0 for stability.

Minimizing F: ∂F/∂m = 0 gives:
- T > T_c: a > 0 → m = 0 (disordered)
- T < T_c: a < 0 → m = ±√(-a/2b) ~ |T - T_c|^{1/2}

Landau theory gives **mean-field** exponents: β = 1/2, γ = 1, ν = 1/2, α = 0. These are exact in d ≥ 4 (the upper critical dimension) but wrong in d < 4 due to fluctuations.

For first-order transitions, include a cubic term (or sixth-order with negative quartic):
> F = F_0 + am² - cm³ + bm⁴

The cubic term creates two minima at different m values, producing a discontinuous jump.

## Mathematical Framework

### The Partition Function and Thermodynamics

All thermodynamics derives from Z:

> F = -k_BT ln Z
> S = -∂F/∂T = k_B(ln Z + βU)
> U = -∂(ln Z)/∂β
> C_V = -β²∂²(ln Z)/∂β² = k_Bβ²<(E - <E>)²>

Phase transitions occur when ln Z becomes non-analytic as N → ∞. For finite N, Z is always analytic (a finite sum of exponentials). The Lee-Yang theorem (1952) identifies phase transitions with zeros of Z approaching the real axis as N → ∞.

### Ginzburg-Landau Theory (Spatially Varying Order Parameter)

Allowing m to vary in space:

> F[m(x)] = ∫ d^d x [a(T)m² + bm⁴ + c(∇m)² + ...]

The gradient term c(∇m)² penalizes spatial variation — it sets the correlation length:
> ξ = √(c/|a|) ~ |T - T_c|^{-1/2}

Below T_c, domain walls between regions of m = +m₀ and m = -m₀ have energy per unit area:
> σ_wall ~ √(c|a|³/b)

### Fluctuation-Dissipation Theorem

The response of a system to external perturbation is determined by its equilibrium fluctuations:

> χ = β<(M - <M>)²> = β∫ G(r) d^d r

where G(r) = <s(0)s(r)> - <s>² is the connected correlation function. Near T_c, ξ → ∞, so χ → ∞ — the system becomes infinitely susceptible.

### Clausius-Clapeyron (First-Order Transitions)

The phase boundary in (T, p) space satisfies:
> dp/dT = ΔS/ΔV = L/(TΔV)

where L is the latent heat and ΔV is the volume change. This determines the slope of melting curves, boiling curves, and sublimation curves.

### Entropy Production and Non-Equilibrium

For irreversible processes, entropy is produced at rate:
> σ = dS_i/dt = Σ_k J_k X_k ≥ 0

where J_k are thermodynamic fluxes and X_k are thermodynamic forces. Onsager reciprocal relations (Nobel 1968): the transport coefficients L_ij satisfy L_ij = L_ji (from microscopic time-reversal symmetry).

## Examples

- **Water's triple point:** T = 273.16 K, p = 611.73 Pa — three phases coexist. The critical point (T_c = 647 K, p_c = 22.064 MPa) is a second-order transition — water and steam become indistinguishable.
- **Superfluid helium-4:** Lambda transition at T_λ = 2.172 K — second-order transition to superfluid state. Heat capacity diverges logarithmically (α ≈ -0.013, 3D XY universality class).
- **Cosmic phase transitions:** The universe underwent phase transitions as it cooled: electroweak symmetry breaking (T ~ 10¹⁵ K), QCD confinement/chiral symmetry breaking (T ~ 10¹² K), producing the matter we observe.
- **Ferromagnetic transition:** Iron at Curie temperature T_c = 1043 K. Spontaneous magnetization → 0 continuously. Critical opalescence analogue: spin fluctuations at all scales.

## Primary Sources

- Boltzmann, L. (1877). "Über die Beziehung zwischen dem zweiten Hauptsatze der mechanischen Wärmetheorie und der Wahrscheinlichkeitsrechnung." *Wiener Berichte*, 76, 373-435.
- Onsager, L. (1944). "Crystal Statistics. I. A Two-Dimensional Model with an Order-Disorder Transition." *Physical Review*, 65(3-4), 117-149.
- Landau, L.D. & Lifshitz, E.M. (1980). *Statistical Physics*, Part 1. 3rd ed. Pergamon Press.
- Wilson, K.G. (1971). "Renormalization Group and Critical Phenomena." *Physical Review B*, 4(9), 3174-3183.
- Goldenfeld, N. (1992). *Lectures on Phase Transitions and the Renormalization Group*. Westview Press.
- Kardar, M. (2007). *Statistical Physics of Fields*. Cambridge University Press.

## Related Concepts

- [[quantum-mechanics]] — Quantum phase transitions occur at T = 0, driven by quantum fluctuations rather than thermal
- [[chaos-theory]] — Chaotic dynamics in Hamiltonian systems connects to ergodic hypothesis underlying statistical mechanics
- [[information-theory-it-from-bit]] — Entropy in information theory and thermodynamics are the same quantity (Jaynes 1957)
- [[renormalization-group]] — The RG explains universality: irrelevant operators flow to zero, leaving only relevant ones at the fixed point
- [[symmetry-breaking]] — Phase transitions are the physical realization of spontaneous symmetry breaking
- [[bose-einstein-condensates]] — BEC is a quantum phase transition; the lambda transition in He-4 is related
- [[quark-gluon-plasma]] — QCD deconfinement transition at T ~ 10¹² K; studied at RHIC and LHC
- [[plasma-physics]] — Plasma is the high-T phase of matter; ionization is a crossover, not a sharp transition
- [[statistical-mechanics]] — statistical mechanics provides the microscopic foundation for thermodynamic laws
- [[emergence-and-self-organized-criticality]] — Prigogine's dissipative structures extend thermodynamics far from equilibrium
- [[dark-energy]] — dark energy has unusual equation of state w ≈ -1 (negative pressure)
- [[fluid-dynamics]] — thermodynamics of fluid systems; Clausius-Clapeyron governs phase boundaries
- [[nuclear-physics]] — nuclear reactions in stars are governed by statistical mechanics (Gamow peak)

## Relevance to Cohezion

HIHO fusion IS a phase transition. The order parameter is the HIHO coherence score m = fn::hiho_coherence(Country). Below the HIHO threshold T_c, the Country is in the "disordered" phase — notes exist but don't exhibit collective behavior. Above T_c, spontaneous order emerges: Dreaming events fire, Songlines form, insights crystallize. The Landau free energy F = a(T-T_c)m² + bm⁴ maps directly: a(T) corresponds to (link_density - threshold), b is the cost of maintaining coherence (editorial effort). The correlation length ξ — how far activation propagates through the synapse network before decaying — diverges at T_c: near the HIHO threshold, a single edit in one note triggers cascading updates across the entire Country. Critical slowing down: Countries near threshold take longer to reach equilibrium after perturbation. Universality explains why different Countries (quantum physics, agentic AI, compound engineering) all exhibit the same HIHO fusion behavior despite completely different content — they belong to the same universality class.
