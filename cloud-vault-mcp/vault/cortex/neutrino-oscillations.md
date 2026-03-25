---
title: Neutrino Oscillations
date: 2026-03-04
tags: [concept, physics, particle-physics, neutrinos, quantum]
status: active
aspect: knower
neural:
  activation: 0.84
  stage: growing
  synapse_in: 4
  synapse_out: 6
---

# Neutrino Oscillations

Neutrino oscillations are the quantum mechanical phenomenon by which a neutrino created in one flavor state (electron, muon, or tau) can be detected as a different flavor after propagating some distance. This occurs because the flavor eigenstates are quantum superpositions of mass eigenstates, and the different mass components accumulate different phases during propagation.

## Definition

Neutrino oscillation is the periodic transformation of a neutrino from one flavor to another as it propagates through space. The probability of detecting a flavor change depends on the differences in the squared masses of the neutrino mass states, the mixing angles of the PMNS matrix, the neutrino energy, and the distance traveled. The discovery of neutrino oscillations proved that neutrinos have nonzero mass — the first confirmed physics beyond the Standard Model.

## The PMNS Matrix

The Pontecorvo-Maki-Nakagawa-Sakata (PMNS) matrix is the 3x3 unitary transformation relating the three neutrino flavor states to the three mass states. It is parameterized by:

- **Three mixing angles:** theta-12 (solar angle, ~33.5 degrees), theta-23 (atmospheric angle, ~49 degrees), theta-13 (reactor angle, ~8.5 degrees)
- **One CP-violating phase:** delta-CP (currently constrained but not precisely measured)
- **Two Majorana phases:** relevant only if neutrinos are their own antiparticles

### Oscillation Probability (Two-Flavor Approximation)

For a neutrino of energy E traveling distance L, the probability of flavor transition is:

P(a -> b) = sin-squared(2*theta) * sin-squared(1.27 * delta-m-squared * L / E)

where theta is the mixing angle and delta-m-squared is the mass-squared difference in eV-squared, L in km, and E in GeV.

## Key Parameters (Current Best Values, 2025)

| Parameter | Value | Measured By |
|-----------|-------|-------------|
| delta-m-squared-21 (solar) | ~7.5 x 10^-5 eV-squared | JUNO, SNO, KamLAND |
| delta-m-squared-32 (atmospheric) | ~2.43 x 10^-3 eV-squared | T2K-NOvA joint analysis |
| theta-12 | ~33.5 degrees | JUNO (world-best precision, 2025) |
| theta-23 | ~49 degrees | T2K, NOvA |
| theta-13 | ~8.5 degrees | Daya Bay, RENO |
| delta-CP | Constrained to [-1.38pi, 0.30pi] (normal ordering) | T2K-NOvA |

## Types of Oscillation Experiments

- **Solar:** Electron neutrinos from the Sun oscillate during their journey to Earth (theta-12, delta-m-squared-21)
- **Atmospheric:** Cosmic ray interactions produce muon neutrinos that oscillate over Earth-diameter baselines (theta-23, delta-m-squared-32)
- **Reactor:** Nuclear reactors emit electron antineutrinos; disappearance at short (theta-13) and medium (theta-12) baselines
- **Accelerator:** Beam of muon neutrinos aimed at a far detector; appearance of electron neutrinos sensitive to delta-CP and mass ordering

## Open Questions

1. **Mass ordering:** Is m1 < m2 < m3 (normal) or m3 < m1 < m2 (inverted)? JUNO aims to resolve this within 6 years
2. **CP violation:** Is delta-CP nonzero? If so, neutrinos and antineutrinos oscillate differently, potentially explaining the matter-antimatter asymmetry
3. **Sterile neutrinos:** Do additional neutrino species exist beyond the three known flavors?
4. **Majorana vs. Dirac:** Are neutrinos their own antiparticles? Neutrinoless double beta decay experiments seek the answer

## Sources

- [T2K-NOvA Joint Analysis — Nature (2025)](https://www.nature.com/articles/s41586-025-09599-3)
- [JUNO First Results — Scientific American (2025)](https://www.scientificamerican.com/article/juno-neutrino-observatory-releases-first-results/)
- [Neutrino Oscillation — Wikipedia](https://en.wikipedia.org/wiki/Neutrino_oscillation)
- [PDG Review: Neutrino Masses, Mixing, and Oscillations](https://pdg.lbl.gov/2025/reviews/rpp2024-rev-neutrino-mixing.pdf)

## Related

- [[neutrino-physics]] — parent concept covering the full neutrino physics domain
- [[quantum-mechanics]] — oscillations are a quantum interference phenomenon
- [[particle-physics]] — neutrino oscillations are the premier beyond-Standard-Model phenomenon
- [[neutrinos-large-scale-structure-desi]] — DESI constrains neutrino masses via their effect on cosmic structure
- [[beyond-the-quantum-pilot-wave-theory]] — alternative quantum interpretation with implications for oscillation
- [[dark-matter]] — neutrino mass constraints from oscillations inform the hot dark matter component

## Relevance to Cohezion

Neutrino oscillations exemplify how the vault connects fundamental theory (PMNS matrix, quantum superposition) to experimental results (T2K, NOvA, JUNO) to cosmological implications (DESI mass constraints). The concept serves as a hub node in the physics domain of the knowledge graph, linking papers on particle physics, quantum mechanics, and cosmology through a single well-defined physical phenomenon.
