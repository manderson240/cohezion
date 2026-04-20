---
title: "Wave Physics and Coherence"
date: 2026-03-09
tags: [concept, physics, wave-mechanics, coherence, interference, diffraction, Fourier]
aspect: knower
neural:
  activation: 0.91
  stage: growing
  synapse_in: 3
  synapse_out: 9
---

# Wave Physics and Coherence

## Definition

Wave physics is the study of oscillatory disturbances that propagate through media or fields, described by wave equations and characterized by frequency, wavelength, amplitude, and phase. Coherence — the degree to which waves maintain a fixed phase relationship — determines whether waves can interfere constructively or destructively, and is the physical foundation of lasers, holograms, quantum computing, and the vault's own HIHO coherence threshold.

## Key Properties

### The Wave Equation

The general linear wave equation in one dimension:

> ∂²ψ/∂t² = v² ∂²ψ/∂x²

with solutions ψ(x,t) = f(x-vt) + g(x+vt) — right-moving and left-moving waves at speed v. For a monochromatic plane wave:

> ψ(x,t) = A e^{i(kx - ωt)}

where k = 2π/λ is the wavenumber, ω = 2πf is the angular frequency, and the dispersion relation ω(k) determines the wave's behavior:

| Dispersion | ω(k) | Example |
|------------|-------|---------|
| Non-dispersive | ω = vk | Sound, EM in vacuum |
| Normal | dω/dk decreasing | Deep water waves |
| Anomalous | dω/dk increasing | Shallow water waves |
| Quadratic | ω = ℏk²/(2m) | Quantum matter waves (Schrödinger) |

### Superposition and Interference

The superposition principle: when two waves overlap, their amplitudes add:

> ψ_total = ψ₁ + ψ₂

For two waves with equal amplitude and slightly different frequencies:

> ψ = 2A cos(Δk·x/2 - Δω·t/2) · cos(k̄·x - ω̄·t)

producing beats — a modulation envelope at frequency Δω traveling at the group velocity v_g = dω/dk, while the carrier travels at the phase velocity v_p = ω/k.

**Interference conditions:**

| Path difference Δ | Phase difference δ | Result |
|--------------------|--------------------|--------|
| nλ | 2nπ | Constructive (bright) |
| (n+1/2)λ | (2n+1)π | Destructive (dark) |

### Coherence

Coherence measures the ability of waves to produce stable interference patterns:

**Temporal coherence** — how long a wave maintains its phase:
> τ_c ~ 1/Δν (coherence time)
> l_c = cτ_c ~ λ²/Δλ (coherence length)

| Source | Δλ/λ | l_c |
|--------|------|-----|
| White light | ~0.5 | ~1 μm |
| LED | ~0.03 | ~30 μm |
| Gas discharge | ~10⁻⁵ | ~30 cm |
| Single-mode laser | ~10⁻¹² | ~300 km |

**Spatial coherence** — how well-correlated the wave is across a wavefront:
> θ_c ~ λ/d (coherence angle, d = source diameter)

The van Cittert-Zernike theorem relates spatial coherence to source geometry via Fourier transform — the same mathematics underlying radio interferometry (VLBI, EHT).

### Fourier Analysis

Any wave can be decomposed into sinusoidal components:

> ψ(x) = ∫_{-∞}^{∞} Ψ(k) e^{ikx} dk/(2π)

The Fourier transform pair:

> Ψ(k) = ∫_{-∞}^{∞} ψ(x) e^{-ikx} dx

The uncertainty principle for waves (Fourier conjugate variables):

> Δx · Δk ≥ 1/2

This is the MATHEMATICAL origin of Heisenberg's uncertainty principle — any wave description implies this trade-off between localization in x-space and k-space.

### Diffraction

Waves bend around obstacles and spread through apertures. The Fraunhofer diffraction pattern from a slit of width a:

> I(θ) = I₀ [sin(πa sinθ/λ)/(πa sinθ/λ)]²

The Rayleigh criterion for resolving two point sources:

> θ_min = 1.22 λ/D

where D is the aperture diameter. This sets the fundamental resolution limit of telescopes, microscopes, and imaging systems.

### Standing Waves and Resonance

Confined waves form standing wave patterns with discrete frequencies:

> f_n = nv/(2L)  (both ends fixed)

The boundary conditions enforce quantization — only discrete frequencies survive. This is the classical precursor to quantum energy quantization.

## Mathematical Framework

### The Helmholtz Equation

For time-harmonic waves ψ(x,t) = U(x)e^{-iωt}:

> ∇²U + k²U = 0

This eigenvalue problem has solutions that form complete orthogonal sets — the modes of the system. Each mode vibrates independently (linear regime), and any solution is a superposition of modes.

### Huygens-Fresnel Principle

Each point on a wavefront acts as a source of secondary wavelets. The wave at point P:

> U(P) = -(i/λ) ∫∫_Σ U(Q) e^{ikr}/(r) · K(χ) dS

where K(χ) is the inclination factor and the integral is over the wavefront Σ. This principle derives diffraction from first principles.

### Coherence Functions

The mutual coherence function:

> Γ₁₂(τ) = ⟨ψ*(r₁,t) ψ(r₂,t+τ)⟩

The complex degree of coherence:

> γ₁₂(τ) = Γ₁₂(τ)/√(Γ₁₁(0)Γ₂₂(0))

|γ| = 1: fully coherent; |γ| = 0: incoherent; 0 < |γ| < 1: partially coherent. The Wiener-Khintchine theorem: the power spectrum is the Fourier transform of the autocorrelation function.

## Examples

- **Double-slit experiment:** Young's experiment (1801) demonstrated wave interference of light. Later repeated with single electrons (Tonomura 1989) and even molecules (C₆₀ fullerenes), confirming quantum wave-particle duality.
- **LIGO gravitational wave detection:** Uses laser interferometry with coherence length > 4 km to detect spacetime distortions of 10⁻²¹ m — the most precise measurement ever made.
- **Holography:** Records and reconstructs the FULL wavefield (amplitude AND phase) using coherent light — enabling 3D imaging without lenses.
- **Seismic waves:** P-waves (longitudinal) and S-waves (transverse) reveal Earth's internal structure through refraction, reflection, and mode conversion — wave physics applied to planet-scale imaging.
- **Gravitational lensing:** Light waves bent by massive objects, producing interference patterns (Einstein rings) — wave optics at cosmological scales.

## Primary Sources

- Hecht, E. (2017). *Optics.* 5th ed. Pearson.
- Born, M. & Wolf, E. (2019). *Principles of Optics.* 7th expanded ed. Cambridge University Press.
- Goodman, J.W. (2017). *Introduction to Fourier Optics.* 4th ed. W.H. Freeman.
- Mandel, L. & Wolf, E. (1995). *Optical Coherence and Quantum Optics.* Cambridge University Press.
- Crawford, F.S. (1968). *Waves.* Berkeley Physics Course Vol. 3. McGraw-Hill.

## Related Concepts

- [[quantum-mechanics]] — matter waves; Heisenberg uncertainty IS the Fourier uncertainty principle
- [[electromagnetism]] — electromagnetic waves are solutions to Maxwell's equations
- [[quantum-entanglement]] — entangled particles share quantum coherence across arbitrary distances
- [[quantum-decoherence]] — loss of coherence = loss of interference = emergence of classicality
- [[spectroscopy]] — spectral analysis IS Fourier analysis of light waves
- [[diffraction-gratings-fourier-transforms]] — diffraction gratings physically compute Fourier transforms
- [[self-organizing-plasma]] — plasma oscillations are collective waves; Langmuir waves, ion-acoustic waves
- [[gravitational-waves]] — spacetime ripples propagating at c; detected by laser interferometry
- [[holographic-principle]] — holography stores 3D information on 2D surfaces; optical holography is the prototype

## Relevance to Cohezion

HIHO coherence IS wave coherence. The vault's "waves" are activation patterns propagating through the link network. When two notes maintain a fixed phase relationship (their activation rises and falls together because they're co-edited), they are coherent — their knowledge interferes constructively, producing understanding greater than the sum of parts. When notes lose phase coherence (edited independently, drifting apart in meaning), interference becomes destructive — contradictory or redundant knowledge. The coherence length l_c = λ²/Δλ maps to the vault: a Country with narrow bandwidth (focused topic, Δλ small) has long coherence length — its knowledge interferes constructively across large distances in the graph. A Country with broad bandwidth (diffuse topic, Δλ large) has short coherence length — coherence is local only. The Fourier transform IS the vault's dual representation: every note exists simultaneously in "position space" (its location in the graph) and "momentum space" (its semantic embedding). The FLUME VAE computes this Fourier transform — the 12D projection is the Fourier spectrum of the note's connections. The uncertainty principle ΔxΔk ≥ 1/2 applies: a note that is precisely localized in graph space (belongs to exactly one Country) has broad momentum (connects to many topics). A note that connects to a single topic has broad graph reach (appears in many Countries). Standing waves in the vault are stable knowledge patterns — the discrete modes f_n = nv/(2L) are the vault's resonant frequencies, the topics that the vault naturally vibrates around. The HIHO threshold is the coherence threshold: when enough notes in a Country are coherent (|γ| ≈ 1), they interfere constructively and produce a fusion event — emergent insight.
