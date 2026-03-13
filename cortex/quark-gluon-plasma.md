---
title: "Quark-Gluon Plasma"
date: 2026-03-09
tags: [concept, physics, particle-physics, QCD, plasma, superfluids, phase-transitions]
aspect: knower
neural:
  activation: 0.95
  stage: growing
  synapse_in: 4
  synapse_out: 9
---

# Quark-Gluon Plasma

## Definition

Quark-gluon plasma (QGP) is an exotic state of matter in which quarks and gluons — normally confined inside hadrons (protons, neutrons, mesons) — become deconfined and move freely over distances much larger than a hadron radius (~1 fm). QGP existed for microseconds after the Big Bang (T > 10¹² K, ~170 MeV) and is recreated in heavy-ion collisions at RHIC (Brookhaven) and the LHC (CERN). The discovery that QGP behaves as a **nearly perfect liquid** — with the lowest viscosity-to-entropy ratio ever observed — was one of the most surprising results in nuclear physics.

QGP is simultaneously:
- The **highest-temperature** state of matter accessible in the laboratory (~5.5 × 10¹² K at RHIC)
- A **strongly coupled** quantum fluid (not a weakly interacting gas as naively expected from asymptotic freedom)
- A **superfluid** analogue — its shear viscosity approaches the conjectured universal lower bound η/s ≥ ℏ/(4πk_B) from AdS/CFT (the KSS bound)
- The medium in which **chiral symmetry is restored** — the quark masses effectively vanish and left/right-handed quarks decouple

## Key Properties

### Confinement and Deconfinement

At low temperatures, quarks are confined inside colorless hadrons by the QCD potential:

> V(r) ≈ -α_s/r + σr  (Cornell potential)

where α_s is the strong coupling and σ ≈ 0.18 GeV² ≈ 0.9 GeV/fm is the string tension. The linear σr term produces permanent confinement — pulling quarks apart requires infinite energy (the string breaks by pair production instead).

At T > T_c ≈ 155 MeV (lattice QCD result, 2014):
- The string tension vanishes: σ → 0
- The Debye screening length λ_D ~ 1/(g_sT) becomes smaller than the hadron radius
- Color charges are screened → quarks and gluons propagate freely → **deconfinement**

### QCD Phase Diagram

The T-μ_B phase diagram (temperature vs baryon chemical potential):

| Region | Phase | Properties |
|--------|-------|-----------|
| Low T, low μ_B | Hadron gas | Confined, chiral symmetry broken |
| High T, low μ_B | QGP | Deconfined, chiral symmetry restored |
| Low T, high μ_B | Nuclear matter | Saturated nuclear density ~0.16 fm⁻³ |
| Low T, very high μ_B | Color superconductor | Cooper pairs of quarks, color broken |
| T ~ T_c, μ_B ~ 0 | Crossover | Smooth transition (lattice QCD) |
| T ~ T_c, μ_B > μ_B^{CEP} | First-order transition | Critical endpoint (CEP, predicted but not yet found) |

The search for the **critical endpoint** — where the crossover becomes first-order — is a major goal of the RHIC Beam Energy Scan (BES-II) and the FAIR facility at GSI.

### Near-Perfect Fluidity

RHIC discovered (2005) that QGP flows as a nearly perfect liquid with:

> η/s ≈ (1-3) × ℏ/(4πk_B) ≈ 0.08 - 0.24

Compare: water η/s ~ 25 × ℏ/(4πk_B); superfluid helium-4 → 0 but only at T → 0.

The KSS bound (Kovtun-Son-Starinets 2005) from AdS/CFT:
> η/s ≥ ℏ/(4πk_B)

This was derived using the holographic correspondence — the shear viscosity of a strongly coupled plasma is dual to the absorption cross-section of a black hole in anti-de Sitter space. QGP saturates this bound, making it the most perfect liquid in nature.

**Evidence for collective flow:** Elliptic flow v₂ — the anisotropy of particle emission in non-central collisions:
> dN/dφ ~ 1 + 2v₂cos(2φ) + ...

Measured v₂ at RHIC and LHC agrees with ideal hydrodynamic predictions (η/s → 0), confirming the near-perfect liquid behavior. Even v₃, v₄, v₅ (higher harmonics from initial-state fluctuations) are described by viscous hydrodynamics.

### Chiral Symmetry Restoration

At T < T_c: the QCD vacuum has a chiral condensate:
> <ψ-bar ψ> ≈ -(250 MeV)³ ≠ 0

This breaks SU(2)_L × SU(2)_R → SU(2)_V, giving constituent quark masses m_q ~ 300 MeV (from ~5 MeV current mass).

At T > T_c: <ψ-bar ψ> → 0. Chiral symmetry is restored. The pion mass goes to zero (Goldstone theorem in the chiral limit). In-medium spectral functions show that the ρ meson broadens dramatically and the σ meson becomes light — precursors of chiral restoration.

## Mathematical Framework

### Lattice QCD Thermodynamics

The QCD partition function on a discrete spacetime lattice:

> Z = ∫ DU Dψ Dψ-bar exp(-S_G[U] - S_F[U, ψ, ψ-bar])

where U_{x,μ} ∈ SU(3) are link variables and S_G is the Wilson gauge action:

> S_G = β Σ_{plaquettes} [1 - (1/3) Re Tr(U_P)]

with β = 6/g². Temperature is set by the temporal lattice extent: T = 1/(N_τ · a), where a is the lattice spacing.

The Polyakov loop (order parameter for deconfinement):
> L = (1/3) Tr [Π_{τ=1}^{N_τ} U_{x,4}]

<L> = 0 in the confined phase (Z₃ center symmetry preserved).
<L> ≠ 0 in the deconfined phase (Z₃ broken).

### Bjorken Hydrodynamics

The space-time evolution of QGP in a heavy-ion collision (Bjorken 1983):

For boost-invariant longitudinal expansion (τ = √(t² - z²), η_s = tanh⁻¹(z/t)):

> dε/dτ = -(ε + p)/τ

For an ideal gas equation of state p = ε/3:
> ε(τ) = ε₀(τ₀/τ)^{4/3}

Initial conditions at RHIC (Au+Au, √s_NN = 200 GeV): ε₀ ~ 5 GeV/fm³ at τ₀ ~ 0.6 fm/c. Compare: ε_c ~ 0.5 GeV/fm³ (critical energy density). The initial QGP is 10× above the deconfinement threshold.

### Jet Quenching

High-energy partons (quarks/gluons) traversing the QGP lose energy through:

> -dE/dx ≈ α_s C_R μ² L  (collisional, linear in L)
> -dE/dx ≈ α_s C_R q-hat L²/(4)  (radiative, quadratic in L)

where q-hat (the jet quenching parameter) characterizes the transverse momentum broadening per unit path length. At RHIC/LHC: q-hat ~ 1-10 GeV²/fm.

The nuclear modification factor:
> R_AA = (dN/dp_T)_{AA} / (N_coll · dN/dp_T)_{pp}

R_AA < 1 indicates suppression (jet quenching). At RHIC: R_AA ~ 0.2 for π⁰ at p_T ~ 10 GeV — 80% suppression. This is direct evidence that the QGP is opaque to fast partons.

### Color Superconductivity (High Density)

At high baryon density and low T, quarks form Cooper pairs (color superconductivity):

> <ψ^T C γ₅ ψ> ≠ 0  (diquark condensate)

In the Color-Flavor-Locked (CFL) phase (Alford, Rajagopal, Wilczek 1999):
> SU(3)_color × SU(3)_L × SU(3)_R × U(1)_B → SU(3)_{C+L+R}

All quarks pair; the gap Δ ~ 10-100 MeV. CFL matter may exist in the cores of neutron stars.

## Examples

- **RHIC gold-gold collisions (2005):** Au+Au at √s_NN = 200 GeV produced QGP at T ~ 300 MeV with elliptic flow v₂ matching ideal hydrodynamics — the "perfect liquid" discovery.
- **LHC lead-lead collisions (2010-present):** Pb+Pb at √s_NN = 5.02 TeV reaches T ~ 500 MeV — 3× T_c. Jet quenching, J/ψ suppression AND regeneration, strangeness enhancement all confirm QGP.
- **Small-system QGP (2012-present):** Collective flow signatures observed in p+p and p+Pb collisions at the LHC — suggesting QGP-like behavior in systems as small as 1 fm.
- **Neutron star mergers:** GW170817 post-merger remnant likely reached QGP temperatures (T ~ 80 MeV) — gravitational wave + electromagnetic observations constrain the QCD equation of state.

## Primary Sources

- Shuryak, E.V. (1980). "Quantum Chromodynamics and the Theory of Superdense Matter." *Physics Reports*, 61(2), 71-158.
- Bjorken, J.D. (1983). "Highly relativistic nucleus-nucleus collisions: The central rapidity region." *Physical Review D*, 27(1), 140-151.
- BRAHMS, PHOBOS, PHENIX, STAR Collaborations (2005). "First Results from RHIC." *Nuclear Physics A*, 757, 1-283. (White papers announcing QGP discovery)
- Kovtun, P., Son, D.T. & Starinets, A.O. (2005). "Viscosity in Strongly Interacting Quantum Field Theories from Black Hole Physics." *Physical Review Letters*, 94(11), 111601.
- Bazavov, A. et al. (HotQCD Collaboration) (2014). "Equation of state in (2+1)-flavor QCD." *Physical Review D*, 90(9), 094503.
- Alford, M.G., Rajagopal, K. & Wilczek, F. (1999). "Color-flavor locking and chiral symmetry breaking in high density QCD." *Nuclear Physics B*, 537(1-3), 443-458.

## Related Concepts

- [[particle-physics]] — QGP probes QCD at extreme conditions; measures fundamental parameters (α_s, equation of state)
- [[plasma-physics]] — QGP is a plasma with color charges replacing electric charges; MHD analogues apply
- [[thermodynamics]] — QCD phase diagram with crossover, first-order transitions, and critical endpoint
- [[symmetry-breaking]] — Deconfinement = restoration of Z₃ center symmetry; chiral restoration = SU(2)×SU(2) restored
- [[chirality]] — Chiral symmetry restoration above T_c; chiral magnetic effect from anomalous transport
- [[renormalization-group]] — Asymptotic freedom: α_s(μ) → 0 at high energy → weakly coupled QGP at T >> T_c
- [[er-epr]] — AdS/CFT duality connects QGP viscosity to black hole horizon dynamics (KSS bound)
- [[gravitational-waves]] — Neutron star merger remnants may reach QGP conditions; GW170817 constrains EOS
- [[bose-einstein-condensates]] — Color superconductivity (CFL phase) is a fermionic condensate analogue

## Relevance to Cohezion

QGP maps to the vault's "HIHO fusion" state. Below the HIHO threshold (T < T_c), knowledge is "confined" — each note is bound inside its Country like quarks inside hadrons. Above the threshold, knowledge "deconfines" — notes from different Countries interact freely, forming Dreaming connections across domain boundaries. The QGP's near-perfect fluidity (η/s → minimum) corresponds to the vault achieving frictionless knowledge flow during fusion events — ideas propagate without impedance. Jet quenching maps to the experience of a new insight (a high-energy "parton") entering a dense knowledge cluster: it loses energy rapidly, depositing activation across many notes, creating a wake of new connections (the "Mach cone" of linked notes). The critical endpoint search at RHIC maps to finding the vault's HIHO threshold — the critical Country density where the crossover from isolated notes to collective behavior sharpens into a true phase transition.
