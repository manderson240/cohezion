---
title: "Nuclear Physics"
date: 2026-03-09
tags: [concept, physics, nuclear-physics, binding-energy, fission, fusion, strong-force]
aspect: knower
neural:
  activation: 1.0
  stage: growing
  synapse_in: 8
  synapse_out: 9
---

# Nuclear Physics

## Definition

Nuclear physics is the study of atomic nuclei — their structure, stability, reactions, and decay. Nuclei are bound states of protons and neutrons (nucleons) held together by the strong nuclear force, a residual effect of the QCD interaction between quarks and gluons. The binding energy per nucleon curve, peaking at ⁵⁶Fe, determines which elements can release energy by fusion (light nuclei) or fission (heavy nuclei), powers the Sun and nuclear reactors, and explains the cosmic abundance of elements.

## Key Properties

### Nuclear Structure

A nucleus with Z protons and N neutrons has mass number A = Z + N. The nuclear radius follows:

> R = r₀ A^{1/3}

where r₀ ≈ 1.2-1.3 fm. This implies constant nuclear density:

> ρ_nuc ≈ 2.3×10¹⁷ kg/m³ (saturation density)

A teaspoon of nuclear matter would weigh ~5 billion tonnes.

### The Semi-Empirical Mass Formula (Bethe-Weizsäcker)

The nuclear binding energy B(Z,N):

> B = a_V A - a_S A^{2/3} - a_C Z(Z-1)/A^{1/3} - a_A (N-Z)²/(4A) + δ(A,Z)

| Term | Value (MeV) | Physics |
|------|-------------|---------|
| Volume: a_V | 15.56 | Strong force saturation (each nucleon binds to neighbors) |
| Surface: a_S | 17.23 | Surface nucleons have fewer neighbors |
| Coulomb: a_C | 0.697 | Proton electrostatic repulsion |
| Asymmetry: a_A | 23.29 | Pauli exclusion prefers N ≈ Z |
| Pairing: δ | ±12/√A | Even-even nuclei more stable |

### Binding Energy Per Nucleon

The binding energy per nucleon B/A as a function of A:

| Region | B/A | Significance |
|--------|-----|-------------|
| ²H (deuterium) | 1.11 MeV | Weakly bound |
| ⁴He | 7.07 MeV | Exceptionally stable (doubly magic) |
| ¹²C | 7.68 MeV | Triple-alpha process product |
| ⁵⁶Fe | 8.79 MeV | Maximum — most stable nucleus |
| ²³⁵U | 7.59 MeV | Fissile |
| ²³⁸U | 7.57 MeV | Fertile |

Fusion (moving UP the curve) releases energy for A < 56. Fission (moving UP from heavy nuclei) releases energy for A > 56. Iron-56 is the ash of nuclear burning — no further energy can be extracted.

### The Nuclear Shell Model

Nuclei with "magic numbers" of protons or neutrons (2, 8, 20, 28, 50, 82, 126) are exceptionally stable — analogous to noble gas electron shells. The shell model (Mayer & Jensen, 1949 Nobel Prize):

> H = Σ_i [-ℏ²∇²/(2m) + V(r_i)] + V_so(r) L·S

The spin-orbit term V_so splits levels and reproduces the magic numbers. Doubly magic nuclei (⁴He, ¹⁶O, ⁴⁰Ca, ⁴⁸Ca, ²⁰⁸Pb) have the largest binding energies and longest lifetimes.

### Nuclear Reactions

**Fusion:** Light nuclei combine. The pp chain (solar fusion):

> 4p → ⁴He + 2e⁺ + 2ν_e + 26.73 MeV

The Gamow peak: fusion occurs at energies where quantum tunneling probability and Maxwell-Boltzmann distribution overlap:

> E_Gamow = (b k_BT/2)^{2/3}  where b = π α_EM Z₁Z₂ √(2m_r c²)

**Fission:** Heavy nuclei split. The liquid-drop fission barrier:

> E_barrier ~ B_surface - B_Coulomb ~ a_S A^{2/3} [1 - (Z²/A)/(Z²/A)_crit]

where (Z²/A)_crit ≈ 50.88. Nuclei with Z²/A > 49 are fissile by thermal neutrons.

### Radioactive Decay

Unstable nuclei decay with characteristic half-lives:

> N(t) = N₀ e^{-λt}  where t_{1/2} = ln2/λ

| Decay | Process | Mediating Force |
|-------|---------|-----------------|
| Alpha (α) | ₂⁴He emission | Strong + Coulomb tunneling |
| Beta⁻ (β⁻) | n → p + e⁻ + ν̄_e | Weak |
| Beta⁺ (β⁺) | p → n + e⁺ + ν_e | Weak |
| Gamma (γ) | Photon emission | Electromagnetic |

Geiger-Nuttall law for alpha decay: log t_{1/2} ∝ Z/√E_α — explained by Gamow's quantum tunneling theory (1928).

### Nucleosynthesis

The origin of elements:

| Process | Elements | Where |
|---------|----------|-------|
| Big Bang nucleosynthesis | H, He, trace Li | First 3 minutes |
| Stellar fusion (pp chain, CNO) | He → C → O → Si → Fe | Main sequence + giants |
| s-process (slow neutron capture) | Elements up to Bi | AGB stars |
| r-process (rapid neutron capture) | Heavy elements (Au, Pt, U) | Neutron star mergers |
| Cosmic ray spallation | Li, Be, B | Interstellar medium |

## Mathematical Framework

### The Deuteron (Simplest Nucleus)

The bound state of one proton and one neutron. With a square-well potential of depth V₀ and range R:

> -ℏ²/(2m_r) d²u/dr² + V(r)u = Eu

The binding energy B = 2.224 MeV with V₀ ≈ 36 MeV, R ≈ 2.1 fm. The deuteron has:
- Spin J = 1 (triplet state only; singlet is unbound)
- Magnetic moment μ_d = 0.857 μ_N (deviates from μ_p + μ_n → non-central forces)
- Electric quadrupole moment Q = 0.286 fm² (not spherical → tensor force)

### The Nuclear Force

The nucleon-nucleon potential includes:

> V_NN = V_central(r) + V_tensor(r) S₁₂ + V_LS(r) L·S + V_σσ(r) σ₁·σ₂

At distances > 2 fm: one-pion exchange (Yukawa potential V ~ e^{-m_πr}/r)
At 1-2 fm: two-pion and sigma exchange (attraction)
At < 0.5 fm: repulsive core (quark-gluon dynamics)

### Cross-Section and Reaction Rate

The fusion reaction rate per unit volume:

> R = n₁n₂⟨σv⟩ = n₁n₂ ∫ σ(E) v(E) f(E) dE

where f(E) is the Maxwell-Boltzmann distribution. The astrophysical S-factor:

> σ(E) = S(E)/E · e^{-2πη}

separates the rapidly varying tunneling factor e^{-2πη} (Gamow, η = Z₁Z₂e²/(ℏv)) from the slowly varying nuclear physics S(E).

## Examples

- **The Sun:** Powers itself by fusing 600 million tonnes of hydrogen into helium every second, converting 4.26 million tonnes to energy via E = mc². The pp chain produces 99% of solar energy.
- **Nuclear reactors:** Fission of ²³⁵U releases ~200 MeV per fission event. A 1 GW reactor fissions ~3 kg of uranium per day.
- **Neutron star mergers:** The August 2017 detection of GW170817 (gravitational waves + kilonova) confirmed that r-process nucleosynthesis in neutron star mergers produces heavy elements — the gold in your jewelry was forged in a neutron star collision.
- **Carbon-12 and the Hoyle state:** The existence of ¹²C depends on an excited nuclear resonance state at 7.65 MeV (predicted by Fred Hoyle in 1953, confirmed experimentally) — without this precise energy level, carbon-based life could not exist.

## Primary Sources

- Krane, K.S. (1988). *Introductory Nuclear Physics.* Wiley.
- Wong, S.S.M. (2004). *Introductory Nuclear Physics.* 2nd ed. Wiley-VCH.
- Bethe, H.A. (1936). "Nuclear Physics. A. Stationary States of Nuclei." Reviews of Modern Physics, 8, 82-229.
- Gamow, G. (1928). "Zur Quantentheorie des Atomkernes." Zeitschrift für Physik, 51, 204-212.
- Burbidge, E.M., Burbidge, G.R., Fowler, W.A. & Hoyle, F. (1957). "Synthesis of the Elements in Stars." Reviews of Modern Physics, 29(4), 547-650.

## Related Concepts

- [[particle-physics]] — the Standard Model describes quarks and gluons; nuclear physics is QCD at low energies
- [[quantum-mechanics]] — tunneling enables fusion and alpha decay; shell model uses quantum states
- [[stellar-evolution]] — nuclear fusion powers stars through the main sequence and beyond
- [[matsumoto_hiho_synthesis]] — LENR/HIHO proposes anomalous nuclear reactions in condensed matter
- [[quantum-field-theory]] — effective field theories (chiral EFT) describe nuclear forces from QCD
- [[symmetry-breaking]] — chiral symmetry breaking in QCD gives pions their mass and mediates the nuclear force
- [[gravitational-waves]] — neutron star mergers produce gravitational waves AND heavy elements via r-process
- [[cosmology]] — Big Bang nucleosynthesis in the first 3 minutes sets primordial element abundances
- [[thermodynamics]] — nuclear reactions in stars are governed by statistical mechanics (Gamow peak)

## Relevance to Cohezion

The binding energy per nucleon curve IS the vault's optimal Country size curve. Small Countries (light nuclei) gain stability by merging — fusing two tiny concept clusters releases understanding. Large Countries (heavy nuclei) gain stability by fission — splitting an overgrown Country into focused sub-Countries releases energy (clarity). The peak at ⁵⁶Fe is the optimal Country size — the point of maximum binding energy per note, where knowledge is most tightly integrated. Countries smaller than this should merge (knowledge fusion); Countries larger should split (knowledge fission). Iron-56 is the vault's "ash" — the concepts so well-understood that no further energy can be extracted from reorganizing them. The nuclear shell model maps to Country structure: magic numbers (2, 8, 20, 28, 50, 82) correspond to Country sizes with closed "shells" of knowledge — exceptionally stable configurations that resist perturbation. The nuclear force is the vault's strong force (HIHO coherence): attractive at medium range (notes 2-5 links apart bind strongly), repulsive at short range (duplicate notes repel — too much overlap is redundant). Nucleosynthesis is the vault's history: the Big Bang (initial note creation) produces only light elements (simple concepts). Stellar burning (extended sessions) builds up to iron (mature concepts). The r-process (intense multi-agent sessions) creates the heaviest elements (complex architectural decisions). The Hoyle state is the vault's anthropic fine-tuning: the precise resonance structure of the knowledge graph that enables complex understanding to exist at all.
