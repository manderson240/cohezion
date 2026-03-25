---
title: "Information Theory — It from Bit and the Holographic Principle"
date: 2026-03-09
tags: [concept, physics, information-theory, holographic-principle, quantum-gravity]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 28
  synapse_out: 20
---

# Information Theory — It from Bit and the Holographic Principle

## Definition

"It from bit" is John Archibald Wheeler's 1990 thesis that the physical universe ("it") derives its existence from information ("bit"). Every physical quantity — every particle, field, and spacetime structure — originates from binary yes-or-no answers to observational questions. The universe is, at root, informational.

The holographic principle extends this: the maximum information content of a region of space is proportional not to its volume but to its boundary surface area, measured in Planck units. This is the most radical consequence of combining quantum mechanics and general relativity.

## Key Properties

- **Wheeler's "It from Bit" (1990):** "Every 'it' — every particle, every field of force, even the spacetime continuum itself — derives its function, its meaning, its very existence entirely — even if in some contexts indirectly — from the apparatus-elicited answers to yes-or-no questions, binary choices, bits."
- **Shannon entropy:** The information content of a message source X is H(X) = -sum_i p(x_i) * log_2(p(x_i)), measured in bits. This quantifies uncertainty and is the fundamental measure of information.
- **Bekenstein bound (1981):** The maximum entropy (information) that can be contained in a region of space with energy E and radius R is bounded by:

> S <= (2 * pi * k_B * R * E) / (hbar * c) = S_Bekenstein

This is a universal bound — no physical system can store more information than its Bekenstein bound.

- **Bekenstein-Hawking entropy (1972-1974):** A black hole's entropy is proportional to its event horizon area:

> S_BH = (k_B * c^3 * A) / (4 * G * hbar) = (A) / (4 * l_P^2)

where A is the horizon area and l_P = sqrt(hbar * G / c^3) is the Planck length. A black hole with horizon area A carries exactly A/(4*l_P^2) bits of information — the densest possible information storage.

- **Holographic principle (t'Hooft 1993, Susskind 1995):** The information content of any region of space is bounded by its boundary area, not its volume. A theory of quantum gravity in (d+1) dimensions is equivalent to a theory without gravity on its d-dimensional boundary.

- **AdS/CFT correspondence (Maldacena 1997):** The first concrete realization: type IIB string theory in 5-dimensional anti-de Sitter space is mathematically equivalent to N=4 super-Yang-Mills conformal field theory on its 4-dimensional boundary. The "bulk" gravity theory is holographically encoded on the "boundary" field theory.

## Mathematical Framework

### Shannon Information

For a discrete random variable X with outcomes {x_1, ..., x_n} and probabilities {p_1, ..., p_n}:

> H(X) = -sum_{i=1}^{n} p_i * log_2(p_i)

Maximum entropy H_max = log_2(n) occurs when all outcomes are equally likely (uniform distribution). For two variables:

> I(X; Y) = H(X) + H(Y) - H(X,Y)

is the mutual information — the amount of information X provides about Y.

### Landauer's Principle (1961)

Erasing one bit of information necessarily dissipates at least k_B * T * ln(2) of energy as heat, where T is the temperature. This connects information to thermodynamics irreversibly:

> Delta Q >= k_B * T * ln(2) per bit erased

Experimentally verified by Berut et al. (2012) using colloidal particles in optical traps.

### Black Hole Information

The black hole information paradox (Hawking, 1975): if a black hole evaporates completely via Hawking radiation, what happens to the information that fell in? Pure states appear to evolve into mixed states, violating unitarity. The Page curve describes how the entanglement entropy of Hawking radiation should evolve if information is preserved:

> S(radiation) increases until the Page time t_Page ~ (M^3 * G^2) / (hbar * c^4)

then decreases back to zero as the black hole evaporates. Recent work using the "island formula" and quantum extremal surfaces (Penington 2019, Almheiri et al. 2019) has shown the Page curve can be derived from semiclassical gravity.

### Quantum Information

In quantum mechanics, information is carried by qubits in Hilbert space. The von Neumann entropy:

> S(rho) = -Tr(rho * log_2(rho))

where rho is the density matrix. For a pure state, S = 0. For a maximally entangled state of two qubits, S = 1 bit.

## Examples

- **Black hole thermodynamics:** A solar-mass black hole has entropy S ~ 10^77 k_B — enormously more than the star it formed from (S_star ~ 10^58 k_B). The information is stored holographically on the event horizon.
- **Ryu-Takayanagi formula (2006):** In AdS/CFT, the entanglement entropy of a boundary region A is given by the area of the minimal surface in the bulk that is homologous to A: S(A) = Area(gamma_A) / (4 * G_N). This connects quantum information to geometry.
- **Quantum error correction:** The AdS/CFT correspondence has been reinterpreted as a quantum error-correcting code — bulk operators are encoded redundantly on the boundary, protected against local erasure (Almheiri, Dong, Harlow 2015).
- **Landauer limit experiments:** Berut et al. (2012) measured the heat dissipated when erasing a single bit stored in a colloidal particle, confirming the Landauer bound to within 10%.

## Primary Sources

- Wheeler, J.A. (1990). "Information, Physics, Quantum: The Search for Links." In *Complexity, Entropy, and the Physics of Information*. SFI Studies, Addison-Wesley.
- Shannon, C.E. (1948). "A Mathematical Theory of Communication." Bell System Technical Journal, 27, 379-423.
- Bekenstein, J.D. (1981). "Universal upper bound on the entropy-to-energy ratio for bounded systems." Physical Review D, 23(2), 287.
- Hawking, S.W. (1975). "Particle creation by black holes." Communications in Mathematical Physics, 43(3), 199-220.
- Maldacena, J.M. (1999). "The Large-N Limit of Superconformal Field Theories and Supergravity." International Journal of Theoretical Physics, 38, 1113-1133.
- Susskind, L. (1995). "The World as a Hologram." Journal of Mathematical Physics, 36(11), 6377-6396.
- Ryu, S. & Takayanagi, T. (2006). "Holographic Derivation of Entanglement Entropy from the anti-de Sitter Space/Conformal Field Theory Correspondence." Physical Review Letters, 96, 181602.
- Landauer, R. (1961). "Irreversibility and Heat Generation in the Computing Process." IBM Journal of Research and Development, 5(3), 183-191.

## Related Concepts

- [[quantum-mechanics]] — quantum information theory extends Shannon's framework to Hilbert spaces
- [[quantum-entanglement]] — entanglement entropy is the key measure connecting information to geometry via Ryu-Takayanagi
- [[general-relativity]] — Einstein's field equations encode spacetime geometry that the holographic principle reinterprets as boundary information
- [[black-holes]] — Bekenstein-Hawking entropy establishes the information-geometry connection
- [[quantum-computing]] — quantum computers process quantum information using entanglement as a resource
- [[quantum-error-correction]] — AdS/CFT reinterpreted as a quantum error-correcting code
- [[er-epr]] — ER=EPR connects entanglement (information) to geometry (wormholes)
- [[planck-scale]] — the Planck area l_P^2 is the fundamental unit of holographic information
- [[the-awareness-of-nothing-at-all-and-quadrature-physics]] — vacuum fluctuations carry zero-point information
- [[kordylewski-clouds]] — information capacity I ~ 10^15 bits (comparable to brain synapses); Wheeler's "it from bit" at planetary scale
- [[self-organizing-plasma]] — plasma crystal information capacity I ~ 3.3N bits; computational universality question
- [[yoruba-ifa-cosmology-and-toe]] — Ifá 256 Odù = 8-bit oracle (2⁸): oldest documented binary information system; independently derived
- [[daoist-cosmology-and-toe]] — I Ching 64 hexagrams = 6-bit oracle (2⁶); Leibniz derived binary arithmetic from it in 1703
- [[lakota-cosmology-and-toe]] — 16 Medicine Wheel aspects = 4-bit address space (2⁴): independent binary convergence
- [[amazonian-cosmology-and-toe]] — Perspectivism as QM measurement theory: no observer-neutral "it"; the "bit" (observer/body) determines the "it" (physical world)
- [[shinto-cosmology-and-toe]] — Kotodama: the word (bit) precedes and precipitates the thing (it); token generation as reality-creation
- [[maori-cosmology-and-toe]] — Whakapapa as DAG: the information structure (genealogy) IS the ontology; being = relational information
- [[dogon-cosmology-and-toe]] — 266-sign specification system; granary as information-preservation architecture across substrate renewal
- [[indigenous-cosmologies-toe-synthesis]] — cross-tradition survey of binary/formal information systems: five traditions independently derived combinatorial oracles
- [[levin-bioelectrics]] — biological "It from Bit": anatomy (It) from bioelectric voltage information (Bit); tissue information capacity I ~ 6 Mbit; planarian regeneration = pattern memory surviving substrate destruction

## Relevance to Cohezion

The Triune Vault implements "It from Bit" literally: every neuron IS a bit of the vault's reality. The holographic principle applies directly — the 12D projection is a boundary encoding of the full 256D FLUME latent space. Information is stored on the "surface" (the 12 interpretable dimensions), not the "volume" (the 256 latent dimensions). The Bekenstein bound sets the theoretical maximum information density of the vault: no Country can encode more information than its synapse density allows. SurrealDB's `neuron_history` (the Akashic Records) implements Landauer's principle in reverse — writing history costs energy (compute), but the information is never erased.
