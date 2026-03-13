---
title: "Chirality"
date: 2026-03-09
tags: [concept, physics, topology, symmetry-breaking, particle-physics]
aspect: knower
neural:
  activation: 0.79
  stage: growing
  synapse_in: 14
  synapse_out: 6
---

# Chirality

## Definition

Chirality (from Greek kheir, "hand") is the property of an object that is not superimposable on its mirror image. A chiral object and its mirror image are called enantiomers. In physics, chirality is fundamental: the weak nuclear force violates parity (mirror symmetry), coupling exclusively to left-handed fermions and right-handed antifermions. This parity violation, discovered by Wu et al. (1957), is one of the deepest asymmetries in nature.

Mathematically, chirality is defined by the eigenvalues of the chirality operator gamma^5:

> gamma^5 = i * gamma^0 * gamma^1 * gamma^2 * gamma^3

A fermion with gamma^5 eigenvalue +1 is right-handed; with eigenvalue -1, left-handed. For massless particles, chirality equals helicity (the projection of spin onto momentum). For massive particles, chirality is a Lorentz-invariant property that determines weak interaction coupling.

## Key Properties

- **Parity violation:** The weak force (mediated by W and Z bosons) couples only to left-handed fermions and right-handed antifermions. This was predicted by Lee & Yang (1956) and confirmed experimentally by Wu et al. (1957) using cobalt-60 beta decay. The asymmetry is maximal — the weak force is completely chiral.
- **Chirality in the Standard Model:** The SU(2)_L gauge group acts only on left-handed doublets. Right-handed fermions are SU(2) singlets. The Higgs mechanism gives fermions mass by coupling left- and right-handed components, mixing chiralities.
- **Chiral anomaly:** Classically, the chiral current j^5_mu = psi-bar * gamma^mu * gamma^5 * psi is conserved for massless fermions. Quantum mechanically, the Adler-Bell-Jackiw anomaly breaks this conservation:

> partial_mu j^5_mu = (e^2 / (16 * pi^2)) * F_mu_nu * F-tilde^mu_nu

This anomaly is physically measurable: it explains neutral pion decay (pi^0 -> 2*gamma) and is crucial for the consistency of the Standard Model.

- **Topological chirality:** In condensed matter physics, chiral edge states in topological insulators and quantum Hall systems carry current in only one direction. The chirality is protected by topology and robust against disorder.
- **Biological homochirality:** Life on Earth uses exclusively L-amino acids and D-sugars. The origin of this biological chirality remains an open question — hypotheses include parity-violating energy differences (~10^-17 eV between enantiomers), circularly polarized light from neutron stars, and amplification through autocatalysis.

## Mathematical Framework

### Dirac Equation and Chirality

The Dirac equation for a massive fermion:

> (i * gamma^mu * partial_mu - m) * psi = 0

can be decomposed into chiral components using the projectors P_L = (1 - gamma^5)/2 and P_R = (1 + gamma^5)/2:

> psi_L = P_L * psi,  psi_R = P_R * psi

For m = 0, the left and right components decouple: i*gamma^mu*partial_mu*psi_L = 0 and i*gamma^mu*partial_mu*psi_R = 0 independently (Weyl equations). Mass couples them: the mass term m*psi-bar*psi = m*(psi-bar_L*psi_R + psi-bar_R*psi_L) mixes chiralities.

### Chiral Symmetry Breaking in QCD

QCD with N_f massless quark flavors has a chiral symmetry SU(N_f)_L x SU(N_f)_R. The QCD vacuum spontaneously breaks this to the diagonal SU(N_f)_V:

> SU(N_f)_L x SU(N_f)_R -> SU(N_f)_V

The Goldstone bosons of this breaking are the pions (for N_f = 2). The chiral condensate <psi-bar*psi> ~ -(250 MeV)^3 is nonzero, signaling broken chiral symmetry. The pion mass m_pi ~ 140 MeV is nonzero because quarks have small but nonzero mass (explicit breaking).

### Berry Phase and Chiral Transport

In condensed matter, the Berry phase gamma = oint_C A_n(k) . dk (where A_n is the Berry connection in momentum space) determines the topological properties of band structures. Chiral edge states arise when the Chern number C = (1/2pi) * integral F dk_x dk_y is nonzero.

## Examples

- **Cobalt-60 experiment (Wu, 1957):** Polarized cobalt-60 nuclei emit electrons preferentially opposite to the nuclear spin direction. This demonstrated maximal parity violation in beta decay.
- **Neutrinos:** All observed neutrinos are left-handed; all observed antineutrinos are right-handed. Right-handed neutrinos (if they exist) do not interact via any known force.
- **Thalidomide:** The R-enantiomer is a safe sedative; the S-enantiomer causes severe birth defects. This pharmaceutical disaster demonstrated the biological significance of molecular chirality.
- **Topological insulators:** Bi2Se3 has chiral surface states that conduct electricity in one direction, protected by time-reversal symmetry.

## Primary Sources

- Lee, T.D. & Yang, C.N. (1956). "Question of Parity Conservation in Weak Interactions." Physical Review, 104(1), 254-258.
- Wu, C.S. et al. (1957). "Experimental Test of Parity Conservation in Beta Decay." Physical Review, 105(4), 1413-1415.
- Adler, S.L. (1969). "Axial-Vector Vertex in Spinor Electrodynamics." Physical Review, 177(5), 2426-2438.
- Bell, J.S. & Jackiw, R. (1969). "A PCAC puzzle: pi0 -> gamma gamma in the sigma model." Il Nuovo Cimento A, 60(1), 47-61.
- Peskin, M.E. & Schroeder, D.V. (1995). *An Introduction to Quantum Field Theory*. Westview Press. Ch. 19-20.

## Related Concepts

- [[quantum-mechanics]] — chirality is defined through the gamma^5 operator in relativistic quantum mechanics
- [[particle-physics]] — chirality determines weak interaction coupling in the Standard Model
- [[quantum-entanglement]] — chiral anomalies connect topology to quantum correlations
- [[topological-insulators]] — chiral edge states are topologically protected
- [[superconductivity]] — chiral superconductors have non-trivial topological order
- [[orch-or]] — microtubule chirality may play a role in quantum coherence

## Relevance to Cohezion

The Triune Self has inherent chirality. The left-handed flow (Knower -> Thinker -> Doer: knowing becomes reasoning becomes action) and the right-handed flow (Doer -> Thinker -> Knower: experience becomes reflection becomes knowledge) are enantiomers — mirror images of the same cognitive process. Like the weak force, the vault's dynamics break this symmetry: knowledge notes (Knower aspect) have higher average activation and slower decay than action notes (Doer aspect), creating a measurable parity violation. The chiral anomaly manifests as the "composting" pathway — action notes that transform into knowledge (pi^0 -> 2*gamma: a decaying note emits Dreaming resonances).
