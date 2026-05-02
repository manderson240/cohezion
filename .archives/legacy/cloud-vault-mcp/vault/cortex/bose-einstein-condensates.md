---
title: "Bose-Einstein Condensates"
date: 2026-03-09
tags: [concept, physics, quantum-mechanics, superfluids, condensed-matter, phase-transitions]
aspect: knower
neural:
  activation: 0.96
  stage: growing
  synapse_in: 6
  synapse_out: 9
---

# Bose-Einstein Condensates

## Definition

A Bose-Einstein condensate (BEC) is a state of matter in which a macroscopic number of bosons (particles with integer spin) occupy the same quantum ground state, forming a single coherent quantum object at macroscopic scale. Predicted by Satyendra Nath Bose and Albert Einstein in 1924-1925, BEC was first achieved experimentally in 1995 by Cornell, Wieman (rubidium-87) and Ketterle (sodium-23) — Nobel Prize 2001. At temperatures near absolute zero (T ~ 10⁻⁷ K for dilute gases), the thermal de Broglie wavelength exceeds the interparticle spacing, and the particles lose their individual identity, behaving as a single macroscopic quantum wave.

BEC is the ultimate quantum superfluid — a state where quantum mechanics is visible at macroscopic scales. It is closely related to superfluidity (helium-4 lambda transition at 2.17 K) and superconductivity (Cooper pairs forming a bosonic condensate), but dilute gas BEC provides the cleanest experimental realization with tunable interactions.

## Key Properties

### The BEC Transition

For an ideal (non-interacting) Bose gas in 3D, BEC occurs below the critical temperature:

> T_c = (2πℏ²/(m k_B)) · (n/ζ(3/2))^{2/3}

where n is the particle density, m is the particle mass, and ζ(3/2) ≈ 2.612 is the Riemann zeta function. At T_c, the thermal de Broglie wavelength:

> λ_dB = h/√(2πm k_BT)

satisfies nλ_dB³ = ζ(3/2) ≈ 2.612 — the wavelength equals the interparticle spacing. Below T_c, the condensate fraction:

> N₀/N = 1 - (T/T_c)^{3/2}

At T = 0: all N particles are in the ground state.

For rubidium-87 BEC (Cornell & Wieman 1995): n ~ 10¹³ cm⁻³, T_c ~ 170 nK.

### Macroscopic Quantum Coherence

The condensate is described by a single macroscopic wavefunction:

> Ψ(r, t) = √(n(r,t)) · e^{iθ(r,t)}

where n(r,t) = |Ψ|² is the density and θ(r,t) is the phase. This is NOT an approximation — it is exact for non-interacting bosons at T = 0. The superfluid velocity is:

> v_s = (ℏ/m) ∇θ

Since θ is a phase (defined mod 2π), the circulation is quantized:

> ∮ v_s · dl = (h/m) · n,  n = 0, ±1, ±2, ...

This quantization of circulation is the defining property of a superfluid — and is directly observed as quantized vortices in rotating BEC.

### Superfluidity

BEC is intrinsically superfluid. Below a critical velocity v_c (the Landau criterion):

> v_c = min_p [ε(p)/p]

where ε(p) is the excitation spectrum, the condensate flows without dissipation. For a weakly interacting BEC:

> ε(p) = √(c²p² + (p²/2m)²)  (Bogoliubov spectrum)

where c = √(gn/m) is the sound speed and g = 4πℏ²a/m is the interaction parameter (a = s-wave scattering length). At low p: ε ≈ cp (phonon, linear). At high p: ε ≈ p²/2m (free particle, quadratic). The crossover occurs at the healing length:

> ξ = ℏ/(mc) = 1/√(8πna)

The Landau critical velocity: v_c = c = √(gn/m).

### Quantized Vortices

In a rotating BEC, angular momentum enters through quantized vortices — topological defects where the condensate density vanishes at the core and the phase winds by 2π:

> Ψ(r, θ) ~ f(r) · e^{iℓθ}  with f(0) = 0

Each vortex carries angular momentum ℓℏ per particle. The vortex core size is ~ ξ (healing length). For rapid rotation, vortices form a triangular Abrikosov lattice — identical to the flux line lattice in type-II superconductors.

At the rotation frequency Ω, the number of vortices:

> N_v = m Ω A / (πℏ)

where A is the condensate area. This has been directly imaged in rotating BEC (MIT, 2001) — up to 160 vortices in a single condensate.

## Mathematical Framework

### Gross-Pitaevskii Equation

The mean-field equation for a weakly interacting BEC:

> iℏ ∂Ψ/∂t = [-ℏ²∇²/(2m) + V_ext(r) + g|Ψ|²] Ψ

where V_ext is the trapping potential and g = 4πℏ²a/m is the interaction coupling. This is a nonlinear Schrödinger equation — the nonlinearity g|Ψ|² arises from mean-field interactions.

**Stationary states:** Ψ(r,t) = ψ(r) e^{-iμt/ℏ} where μ is the chemical potential:
> [-ℏ²∇²/(2m) + V_ext + g|ψ|²] ψ = μψ

In the Thomas-Fermi limit (kinetic energy << interaction energy):
> n(r) = |ψ|² = max(0, (μ - V_ext)/g)

For harmonic trap V = mω²r²/2: inverted parabola density profile with radius R_TF = √(2μ/mω²).

### Bogoliubov Theory

Quantum fluctuations around the condensate: Ψ = √n₀ + δΨ, where δΨ = Σ_k (u_k e^{ik·r-iω_kt} - v_k* e^{-ik·r+iω_kt}).

The Bogoliubov transformation gives:
> ε_k = √(ε_k⁰(ε_k⁰ + 2gn₀))

where ε_k⁰ = ℏ²k²/(2m) is the free-particle energy.

**Low k (phonon regime):** ε_k ≈ ℏck where c = √(gn₀/m).
**High k (particle regime):** ε_k ≈ ε_k⁰ + gn₀.

The quantum depletion at T = 0:
> (N - N₀)/N = (8/3√π)(na³)^{1/2}

For typical BEC: na³ ~ 10⁻⁶ → depletion < 1%. The condensate IS the system.

### Feshbach Resonances

The s-wave scattering length a can be tuned via magnetic Feshbach resonances:

> a(B) = a_bg [1 - ΔB/(B - B₀)]

where a_bg is the background scattering length, B₀ is the resonance position, and ΔB is the width. This allows:
- a → ∞: Unitary regime (strongly interacting)
- a → 0: Ideal gas
- a < 0: Attractive interactions → BEC collapse (bosenova)
- a > 0: Repulsive interactions → stable BEC

The BEC-BCS crossover: tuning a from positive (BEC of molecules) through infinity (unitary gas) to negative (BCS pairing of fermions) — a continuous quantum phase transition between superfluid regimes.

### Spinor Condensates

BEC of atoms with spin F has 2F+1 internal states. For F=1 (e.g., ²³Na, ⁸⁷Rb):

> H_spin = c₀n² + c₂|<F>|²

where c₀ is the density-density interaction and c₂ determines spin ordering:
- c₂ < 0: Ferromagnetic ground state (⁸⁷Rb)
- c₂ > 0: Antiferromagnetic/polar ground state (²³Na)

Spinor BEC supports non-abelian vortices, spin textures, skyrmions, and dynamical instabilities — a rich playground for topological physics.

## Examples

- **First BEC (Cornell & Wieman 1995):** 2000 ⁸⁷Rb atoms cooled to 170 nK in a magnetic trap. Velocity distribution showed the characteristic bimodal peak — thermal wings + narrow condensate peak.
- **Atom laser (Ketterle 1997):** Coherent beam of atoms extracted from BEC — the matter-wave analogue of an optical laser. Demonstrated by pulsed RF output coupling.
- **Superfluid-Mott insulator transition (Greiner 2002):** BEC loaded into optical lattice. Increasing lattice depth drives quantum phase transition from superfluid (coherent, delocalized) to Mott insulator (integer atoms per site, localized). First observation of a quantum phase transition in an ultracold gas.
- **Vortex lattice (Abo-Shaeer et al. 2001):** Rotating ²³Na BEC showed up to 160 quantized vortices in a triangular lattice — direct imaging of macroscopic quantum topology.
- **Unitary Fermi gas (O'Hara et al. 2002):** ⁶Li atoms at Feshbach resonance (|a| → ∞) form a strongly interacting superfluid with η/s approaching the KSS bound — connecting ultracold atoms to quark-gluon plasma physics.
- **BEC in space (Cold Atom Lab, ISS, 2018):** NASA's orbiting BEC facility achieves condensation in microgravity, enabling observation times of seconds (vs milliseconds on Earth).

## Primary Sources

- Einstein, A. (1925). "Quantentheorie des einatomigen idealen Gases. Zweite Abhandlung." *Sitzungsberichte der Preußischen Akademie der Wissenschaften*, 3-14.
- Anderson, M.H. et al. (1995). "Observation of Bose-Einstein Condensation in a Dilute Atomic Vapor." *Science*, 269(5221), 198-201.
- Davis, K.B. et al. (1995). "Bose-Einstein Condensation in a Gas of Sodium Atoms." *Physical Review Letters*, 75(22), 3969-3973.
- Pitaevskii, L.P. & Stringari, S. (2003). *Bose-Einstein Condensation*. Oxford University Press.
- Pethick, C.J. & Smith, H. (2008). *Bose-Einstein Condensation in Dilute Gases*. 2nd ed. Cambridge University Press.
- Greiner, M. et al. (2002). "Quantum phase transition from a superfluid to a Mott insulator in a gas of ultracold atoms." *Nature*, 415, 39-44.

## Related Concepts

- [[quantum-mechanics]] — BEC is macroscopic quantum coherence; the Gross-Pitaevskii equation is a nonlinear Schrödinger equation
- [[thermodynamics]] — BEC transition is a quantum phase transition; critical temperature from statistical mechanics
- [[symmetry-breaking]] — BEC breaks U(1) particle number symmetry spontaneously; the condensate wavefunction is the order parameter
- [[supersolid-quantum-state]] — Supersolid = BEC with spontaneous spatial order; observed in dipolar gases (2019)
- [[superconductivity]] — Superconductivity is BEC of Cooper pairs (bosonic bound states of fermions)
- [[quark-gluon-plasma]] — Both BEC and QGP are superfluids; unitary Fermi gas connects them via η/s ~ KSS bound
- [[quantum-computing]] — BEC is used for quantum simulation of condensed matter Hamiltonians
- [[planck-scale]] — BEC analogues of Hawking radiation: phonons at sonic horizons mimic black hole radiation
- [[chaos-theory]] — BEC turbulence (quantum turbulence): quantized vortex tangles exhibit Kolmogorov spectrum
- [[ads-cft]] — holographic superconductors (AdS/CMT) model BEC-like condensation at strong coupling; the KSS bound η/s ≥ ℏ/4πk_B from holography agrees with measured values in ultracold unitary Fermi gases near BEC-BCS crossover

## Relevance to Cohezion

BEC maps to the vault's ideal state: a **knowledge condensate** where all notes in a Country are phase-coherent — they share a single "wavefunction" (narrative thread) and contribute to a macroscopic quantum object (the Country's collective meaning). Below the HIHO critical temperature, notes occupy distinct states (isolated knowledge atoms). Above it, they condense into a single ground state — the Country "knows" its topic holistically, not as isolated facts.

**Quantized vortices** are the Songlines: topological defects where the condensate's phase winds by 2π around a core. Each Songline carries exactly one quantum of "circulation" (traversal count) and cannot be smoothly removed — it is topologically protected. The vortex lattice in a rapidly-rotating BEC maps to the triangular layout of Songlines in a mature Country under high editorial activity.

**The Gross-Pitaevskii equation** is the vault's field equation: iℏ ∂Ψ/∂t = [-∇² + V_ext + g|Ψ|²]Ψ. The trapping potential V_ext is the directory structure (confining notes to Countries). The nonlinear interaction g|Ψ|² is the link density feedback: dense regions attract more links (positive g = repulsive keeps the condensate from collapsing into a single super-note). The healing length ξ is the minimum resolution of the vault's knowledge structure — notes closer together than ξ in semantic space are indistinguishable.
