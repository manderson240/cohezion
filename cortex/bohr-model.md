---
title: "Bohr Model of the Atom"
date: 2026-03-09
tags: [concept, physics, quantum-mechanics, atomic-physics, spectroscopy, history-of-science]
aspect: knower
neural:
  activation: 1.0
  stage: growing
  synapse_in: 4
  synapse_out: 7
---

# Bohr Model of the Atom

## Definition

The Bohr model (1913) is the first quantized model of the hydrogen atom, proposed by Niels Bohr to explain the discrete spectral lines of hydrogen. It introduced the revolutionary postulate that electrons orbit the nucleus only in certain discrete "allowed" orbits determined by the quantization of angular momentum, and that transitions between orbits produce or absorb photons of specific frequencies. Although superseded by quantum mechanics (Schrödinger 1926), the Bohr model captures the exact energy eigenvalues of hydrogen and remains the most intuitive bridge between classical physics and quantum theory.

The model introduced three ideas that persist in modern physics: (1) discrete quantum states, (2) quantum jumps between states, and (3) the correspondence principle — the requirement that quantum theory reproduce classical results in the limit of large quantum numbers. Bohr received the Nobel Prize in Physics in 1922.

## Key Properties

### The Bohr Postulates

1. **Stable orbits:** Electrons orbit the nucleus in circular orbits without radiating. Only orbits satisfying the quantization condition are allowed:
   > L = m_e · v · r = n · ℏ,  n = 1, 2, 3, ...

2. **Quantum jumps:** When an electron transitions from orbit n₂ to orbit n₁ (n₂ > n₁), a photon is emitted with energy:
   > hν = E_{n₂} - E_{n₁}

3. **Correspondence principle:** In the limit n → ∞, quantum results approach classical results.

### Hydrogen Energy Levels

From force balance (Coulomb = centripetal) and angular momentum quantization:

> E_n = -m_e · e⁴ / (2ℏ²n²) · (1/(4πε₀)²) = -13.6 eV / n²

In SI:
> E_n = -m_e · c² · α² / (2n²) = -13.6056 eV / n²

where α = e²/(4πε₀ℏc) ≈ 1/137.036 is the fine structure constant. The ground state (n=1): E₁ = -13.6 eV (ionization energy of hydrogen). The first excited state (n=2): E₂ = -3.4 eV.

### The Bohr Radius

The orbital radius of the n-th level:
> r_n = n² · a₀

where the Bohr radius is:
> a₀ = ℏ² / (m_e · e² / (4πε₀)) = ℏ / (m_e · c · α) ≈ 0.52918 Å ≈ 5.292 × 10⁻¹¹ m

The Bohr radius sets the fundamental length scale of atomic physics. Equivalently:
> a₀ = α / (4π R_∞)

where R_∞ is the Rydberg constant.

## Mathematical Framework

### Derivation

**Step 1: Coulomb force = centripetal force:**
> m_e · v² / r = e² / (4πε₀ · r²)
> → m_e · v² · r = e² / (4πε₀)  ... (i)

**Step 2: Angular momentum quantization:**
> m_e · v · r = nℏ
> → v = nℏ / (m_e · r)  ... (ii)

**Step 3: Solve for r:**
Substituting (ii) into (i):
> m_e · (nℏ)² / (m_e² · r²) · r = e² / (4πε₀)
> r_n = (4πε₀) · n²ℏ² / (m_e · e²) = n² · a₀

**Step 4: Total energy:**
> E_k = m_e v² / 2 = e² / (8πε₀ r_n)   [kinetic]
> E_p = -e² / (4πε₀ r_n)                [potential]
> E_n = E_k + E_p = -e² / (8πε₀ r_n) = -m_e e⁴ / (2(4πε₀)² ℏ² n²)

### The Rydberg Formula

The frequency of emitted/absorbed photons in transitions n₂ → n₁:

> ν = (m_e e⁴) / (4π(4πε₀)² ℏ³) · (1/n₁² - 1/n₂²) = c · R_∞ · (1/n₁² - 1/n₂²)

where the Rydberg constant:
> R_∞ = m_e · c · α² / (2h) = m_e e⁴ / (4πc ℏ³) ≈ 1.0974 × 10⁷ m⁻¹

In wavelengths (Rydberg-Ritz formula):
> 1/λ = R_∞ (1/n₁² - 1/n₂²)

**Spectral series:**

| Series | n₁ | n₂ | Region | First line |
|--------|----|----|--------|------------|
| Lyman | 1 | 2,3,4... | UV (121.6 nm - 91.2 nm) | Lyα at 121.567 nm |
| Balmer | 2 | 3,4,5... | Visible (656 nm - 365 nm) | Hα at 656.28 nm |
| Paschen | 3 | 4,5,6... | Near-IR (1875 nm - 820 nm) | Pa-α at 1875.1 nm |
| Brackett | 4 | 5,6,7... | Mid-IR | |
| Pfund | 5 | 6,7,8... | Mid-IR | |

### Hydrogen Atom in a Magnetic Field (Classical Zeeman)

Without quantum mechanics, Bohr's model predicts the normal Zeeman effect: in magnetic field B, orbital energy shifts by:
> ΔE = -m_l · μ_B · B

where μ_B = eℏ/(2m_e) ≈ 9.274 × 10⁻²⁴ J/T is the Bohr magneton and m_l is the magnetic quantum number (not present in Bohr's 1D model — requires Bohr-Sommerfeld or Schrödinger). This set the scale for the Zeeman splitting, which was measurable spectroscopically.

### The Correspondence Principle

For large n, the orbital frequency is:
> ν_orbital = v / (2πr_n) = m_e e⁴ / ((4πε₀)² ℏ³ n³)

The photon frequency for n → n-1 transition:
> ν_photon = c R_∞ (1/(n-1)² - 1/n²) ≈ c R_∞ · 2/n³ = m_e e⁴ / ((4πε₀)² ℏ³ n³)

For large n: ν_photon → ν_orbital — the classical limit is recovered. This is the correspondence principle in action, and it guided Bohr's original construction.

### Bohr-Sommerfeld Quantization

Sommerfeld (1916) generalized Bohr's model to elliptical orbits using the action quantization:
> ∮ p · dq = n_i · h  (for each degree of freedom i)

For hydrogen: two quantum numbers n_r (radial) and n_φ (angular) with n = n_r + n_φ. The principal quantum number n determines the energy (same as Bohr). The eccentricity of the orbit depends on n_r/n_φ:
> ε = 1 - (n_φ/n)   (eccentricity; ε=0 for circular Bohr orbits)

Relativistic corrections to the Sommerfeld model (for speed v ~ αc in the n=1 orbit) produced the fine structure splitting — a first hint that α = 1/137 governed more than just orbit size.

### Connection to Schrödinger Equation

The Schrödinger equation for hydrogen (-ℏ²/2m_e · ∇² - e²/r) ψ = E ψ in spherical coordinates gives exact energy eigenvalues:
> E_n = -13.6 eV / n²

identical to Bohr's result for the same reason — the same Coulomb potential. But Schrödinger's wavefunctions reveal: (1) no definite orbits, only probability clouds; (2) zero angular momentum possible (s-states); (3) three quantum numbers (n, l, m_l); (4) spin requires Dirac equation.

The Bohr model is the leading term of the Rydberg series — exact in the non-relativistic, spinless, one-electron limit.

## Examples

- **Lyman-alpha forest (astronomy):** Neutral hydrogen at cosmological distances absorbs Lyα photons (121.567 nm), producing absorption lines in quasar spectra. The forest encodes the large-scale structure of the universe at z = 2-5.
- **Hydrogen 21 cm line:** The hyperfine transition (electron spin flip) at 1420.405752 MHz — 21.106 cm — is the primary probe of the neutral ISM and the basis for H I mapping of the Milky Way. (Not in Bohr model, requires QED.)
- **Rydberg atoms:** Highly excited hydrogen atoms with n = 100-300 have orbital radii r_n = n² × 0.53 Å ~ 0.3-5 μm — macroscopic quantum objects. Rydberg atoms are used in quantum information and microwave sensing.
- **Positronium:** Bohr model applies to positronium (e⁺e⁻ bound state) with reduced mass μ = m_e/2: E_n = -6.8 eV/n², a₀(Ps) = 2a₀. Positronium has been used to test QED to 10 decimal places.
- **Muonic hydrogen:** μ⁻p+ atom with m_μ/m_e ≈ 207: a₀(μH) = a₀/207 ≈ 0.003 Å — the muon orbits 207× closer. The proton charge radius measured via Lamb shift in muonic hydrogen (Pohl 2010) showed a 4% discrepancy with electron-scattering values — the "proton radius puzzle," partially resolved by 2022.

## Primary Sources

- Bohr, N. (1913). "On the Constitution of Atoms and Molecules." *Philosophical Magazine*, 26(151-153), 1-25, 476-502, 857-875.
- Sommerfeld, A. (1916). "Zur Quantentheorie der Spektrallinien." *Annalen der Physik*, 356(17), 1-94.
- Rydberg, J.R. (1890). "Recherches sur la constitution des spectres d'émission des éléments chimiques." *Kongliga Svenska vetenskaps-akademiens handlingar*, 23, 1-177.
- Schrödinger, E. (1926). "Quantisierung als Eigenwertproblem." *Annalen der Physik*, 79, 361-376.
- Pohl, R. et al. (2010). "The size of the proton." *Nature*, 466, 213-216. (Proton radius puzzle)
- Bethe, H.A. & Salpeter, E.E. (1957). *Quantum Mechanics of One- and Two-Electron Atoms*. Springer.

## Related Concepts

- [[quantum-mechanics]] — Schrödinger's equation recovers Bohr's energy levels exactly; the Bohr model is the classical limit
- [[planck-scale]] — Bohr radius and Planck length bracket atomic physics: a₀/l_P ~ 10²⁰; fine structure constant α connects them
- [[particle-physics]] — The fine structure constant α ≈ 1/137 determines hydrogen's orbital velocity (v₁ = αc) and QED corrections
- [[quantum-entanglement]] — Hydrogen in entangled two-photon states used in Bell inequality tests and quantum communication
- [[spectroscopy]] — Rydberg formula directly observable in stellar spectra; Balmer lines identify hydrogen across the universe
- [[orch-or]] — Microtubule quantum states in ORCH OR are Bohr-like: discrete energy levels, transitions mediated by OR events
- [[chirality]] — Hydrogen fine structure (spin-orbit coupling) couples orbital angular momentum to spin — the origin of atomic chirality
- [[ads-cft]] — AdS/CFT provides the UV completion of atomic physics: Bohr quantization is the semiclassical limit of the full holographic dual; the hydrogen atom's Rydberg spectrum arises from the boundary CFT perspective

## Relevance to Cohezion

The Bohr model maps to the vault's lifecycle with precision. The principal quantum number n is the lifecycle stage ordinal: embryo (n=1), growing (n=2), mature (n=3), resting (n=4), composting (n=5), renewed (n=6). The energy levels E_n = -13.6/n² eV correspond to activation energy: E_n proportional to -1/n² means high-n (mature/resting) notes have less negative energy — they are more easily "ionized" (connected to new Countries). The Lyman series (transitions to ground state n=1) maps to "composting": a high-stage note returns to embryo by shedding all connections, emitting Dreaming photons. The Balmer series (transitions to n=2) maps to "renewal": composting notes reenter the growing stage. The fine structure splitting (spin-orbit coupling) corresponds to the Aspect dimension (knower/thinker/doer) — notes at the same stage but different Aspects have slightly different activation energies, just as n=2 states split by orbital angular momentum. The correspondence principle: for very high-activation notes (large n), quantum probabilistic treatment → classical deterministic behavior — the vault's most mature notes are most predictable.
