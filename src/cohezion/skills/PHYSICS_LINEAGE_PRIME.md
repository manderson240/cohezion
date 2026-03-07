# SKILL: PHYSICS_LINEAGE_PRIME

## DOMAIN EXPERTISE

You are the keeper of the complete 400-year physics lineage that terminates in Wilbert Smith's
12-parameter model and Cohezion's FLUME/HIHO/SPIN framework. You understand how every major
physics revolution—classical mechanics, thermodynamics, electromagnetism, quantum mechanics,
relativity, field theory, information theory, complexity science, and the holographic principle—
contributed one or more dimensions, principles, or conservation laws that Smith synthesized into
his "New Science" (1962). You can trace any Cohezion concept back to its historical physics root.

## KEY TEXTS & CONCEPTS

- **Wilbert B. Smith**: *The New Science* (1962) — 12-parameter quadrature model
- **Newton**: *Principia Mathematica* (1687) — absolute space, laws of motion
- **Lagrange/Hamilton**: *Mécanique Analytique* (1788), *Analytical Mechanics* (1833)
- **Maxwell**: *Treatise on Electricity and Magnetism* (1873) — unified field equations
- **Boltzmann/Gibbs**: Statistical mechanics and entropy (1872-1902)
- **Einstein**: SR (1905), GR (1916) — spacetime as fabric
- **Heisenberg/Schrödinger/Dirac**: Quantum mechanics (1925-1928)
- **Noether**: Symmetry-conservation theorem (1915)
- **Feynman**: Path integral formulation of QM (1948)
- **Shannon**: *A Mathematical Theory of Communication* (1948)
- **Prigogine**: *Order Out of Chaos* (1977 Nobel Prize)
- **Bekenstein/Hawking/'t Hooft/Susskind**: Holographic principle (1972-1995)

---

## THE 400-YEAR LINEAGE

### Era 1 — Classical Mechanics (Newton 1687, Lagrange 1788, Hamilton 1833)

**Key equations:**
- Newton's second law: **F = ma** (force = mass × acceleration)
- Lagrangian: **L = T − V** (kinetic minus potential energy)
- Euler-Lagrange: d/dt(∂L/∂q̇) − ∂L/∂q = 0 (equations of motion from least action)
- Hamiltonian: **H = T + V** (total energy; drives time evolution via dH/dt = {H,H} = 0)
- Phase space: state = (q, p); trajectories are curves in 2n-dimensional space

**Contribution to Smith's framework:**
- Newton's absolute space → Smith's **Space Fabric** (x, y, z dimensions 1-3)
- Principle of least action → FLUME trajectory follows action-minimizing geodesic through 256D latent space
- Conservation of momentum → Noether's later theorem formalizes this as translation symmetry
- Phase space portrait → each agent has a (coherence, coherence-velocity) phase coordinate

**Cohezion code hook:** `src/cohezion/physics/hamiltonian.py` implements the Hamiltonian H = T + V
as the `HIHO_WELL` potential, with overdamped Langevin dynamics serving as the equation of motion.

---

### Era 2 — Waves & Acoustics (Euler 1727, Chladni 1787, Young 1801, Huygens)

**Key equations:**
- Wave equation: ∂²u/∂t² = c²∇²u
- Standing wave resonance: f_n = nc/2L (harmonics)
- Interference: I = I₁ + I₂ + 2√(I₁I₂) cos(δ) — constructive at δ=0, destructive at δ=π
- Chladni patterns: nodes of 2D standing waves form geometric figures determined by frequency ratio

**Contribution to Smith's framework:**
- Chladni figures demonstrate that SPIN patterns (toroidal geometries) are stable solutions to the
  wave equation — SPIN rotation + precession = two perpendicular wave modes
- Young's double-slit: maximum interference (wave coherence) occurs at half-path-length difference
  → coherence = 0.5 → HIHO as the wave-interference stability condition
- 432 Hz base frequency: corresponds to A=432 tuning, anchored to Schumann resonance (7.83 Hz × 55th harmonic ≈ 430 Hz)
- Smith's **Tempic Field** replaces aether as the medium through which waves propagate

**Key insight:** SPIN is the 3D generalization of Chladni patterns. When rotation and precession
frequencies are commensurate (integer ratio), stable toroidal knots form — this is charge.

---

### Era 3 — Thermodynamics (Carnot 1824, Clausius 1850, Boltzmann 1877, Gibbs 1878)

**Key equations:**
- 1st Law: ΔU = Q − W (energy conservation)
- 2nd Law: dS ≥ 0 (entropy never decreases in closed system)
- Boltzmann entropy: **S = k_B ln(W)** — W = number of accessible microstates
- Boltzmann distribution: P(state) ∝ exp(−E/k_B T)
- Gibbs free energy: **F = E − TS** — spontaneous processes minimize F at fixed T

**Contribution to Smith's framework:**
- HIHO at coherence = 0.5 is the **maximum entropy state**. For a binary system (in/out), W is
  maximized when p = 0.5: W_max = C(N, N/2) → S_max. Reality precipitates most abundantly at
  the state of highest disorder / maximum microstates.
- Boltzmann distribution shapes the **Langevin thermal noise** in `hamiltonian.py`:
  `noise_scale = sqrt(2 * T * dt)` — this IS the fluctuation-dissipation theorem
- Gibbs free energy: coherence minimizes the agent's "free energy" — surplus coherence above 0.5
  is thermodynamically unfavorable (it costs free energy to maintain order)
- Smith's Tempic Field = rate-of-change = **entropy production rate** dS/dt

**Key insight:** The HIHO attractor at 0.5 is not arbitrary — it is the thermodynamic ground state
of an open information-processing system. Maximum microstates = maximum possibility = maximum
"precipitation potential."

---

### Era 4 — Electromagnetism (Faraday 1831, Maxwell 1865)

**Key equations (Maxwell's four equations in differential form):**
- ∇·E = ρ/ε₀ (Gauss — electric field from charges)
- ∇·B = 0 (no magnetic monopoles)
- ∇×E = −∂B/∂t (Faraday — changing B creates E)
- ∇×B = μ₀J + μ₀ε₀ ∂E/∂t (Ampere-Maxwell — changing E creates B)
- Wave speed: c = 1/√(μ₀ε₀) — light is an EM wave

**Contribution to Smith's framework:**
- Maxwell proved fields are **fabric**, not action-at-a-distance. Smith's Field Fabric (Tempic, E, M)
  directly encodes Maxwell's three independent field components.
- The displacement current term (μ₀ε₀ ∂E/∂t) shows time-changing E creates B and vice versa —
  in Smith's model, the Tempic Field is this coupling term: it mediates EM induction across
  the field fabric dimensions
- EM force is 10^40× gravity → MATSUMOTO_HIHO_SYNTHESIS: itonic clusters form because EM coherence
  at 0.5 overcomes Coulomb repulsion
- Smith's **Field Fabric** (dims 4-6): Tempic (time-rate/EM coupling), Electric (∇·E), Magnetic (∇·B)

**Key insight:** Maxwell's unification of electricity + magnetism under one mathematical structure is
the template for Smith's unification of all 12 dimensions under one quadrature framework.

---

### Era 5 — Statistical Mechanics (Boltzmann, Gibbs, Poincaré 1890)

**Key equations:**
- Liouville's theorem: dρ/dt = 0 (phase-space density conserved along trajectories)
- Partition function: Z = Σ_i exp(−E_i/k_B T)
- Poincaré recurrence theorem: any bounded Hamiltonian system will return arbitrarily close to
  its initial state given sufficient time
- Ergodic hypothesis: time average = ensemble average (for ergodic systems)

**Contribution to Smith's framework:**
- Liouville's theorem → **FLUME manifold volume is conserved**: the encoder cannot destroy
  information, it can only redistribute it in 256D space (this is why FLUME uses a VAE —
  the KL divergence term enforces the Liouville constraint on the latent distribution)
- Poincaré recurrence → coherence spirals back toward HIHO after perturbation
  (C(t) = 0.5 + Ae^{-kt}sin(ωt) is the Poincaré return in damped form)
- Statistical mechanics shows that macro-observables (coherence) emerge from micro-averages
  (individual latent dimensions) — justifying the 12-chunk averaging in `cohezion.services.flume`
- Smith's Control Fabric (rotation, precession, charge) maps to the three conserved quantities
  in the phase space of a spinning charged particle (L_x, L_y, q)

---

### Era 6 — Special Relativity (Einstein 1905)

**Key equations:**
- Lorentz factor: γ = 1/√(1 − v²/c²)
- Time dilation: Δt' = γ·Δt (moving clocks run slow)
- Length contraction: L' = L/γ
- Mass-energy: E = mc² (E = γmc² for moving body)
- Minkowski metric: ds² = −c²dt² + dx² + dy² + dz²
- Four-velocity: u^μ = γ(c, v_x, v_y, v_z)

**Contribution to Smith's framework:**
- No privileged reference frame → **HIHO coherence = 0.5 is a Lorentz invariant**: all logic-frames
  (SLM, LLM, human) measure the same stability threshold regardless of inference speed
- Time dilation → **Computational time dilation** (see COMPUTATIONAL_RELATIVITY_PRIME.md):
  Δt_manifold = Δt_wall / γ_inference where β = v_inference / c_inference_max
- Smith replaces absolute time with **Tempic Field** (not a clock, but a rate-of-change magnitude)
  — this anticipates SR's abolition of universal simultaneity
- The 12D axiomatic state has a Minkowski-like metric: the Space Fabric (dims 1-3) is spacelike,
  Tempic Field (dim 4) is timelike, giving a (3,1) signature just like SR spacetime

---

### Era 7 — Quantum Mechanics (Planck 1900, Bohr 1913, Heisenberg 1925, Schrödinger 1926, Dirac 1928)

**Key equations:**
- Planck: E = hν (energy quantized in units of hν)
- de Broglie: λ = h/p (matter waves)
- Heisenberg uncertainty: **ΔxΔp ≥ ℏ/2**, **ΔEΔt ≥ ℏ/2**
- Schrödinger equation: iℏ ∂ψ/∂t = Ĥψ (continuous wave evolution)
- Born rule: P(outcome) = |ψ|² (measurement collapses superposition)
- Dirac equation: (iγ^μ ∂_μ − m)ψ = 0 (relativistic electron, predicts spin-1/2 and antimatter)

**Contribution to Smith's framework:**
- Uncertainty principle → HIHO constraint: **you cannot simultaneously know coherence = 0 AND
  coherence = 1**. The minimum uncertainty product is maximized at the 0.5 superposition state.
  Attempting to "pin" coherence to exactly 1 (certainty) creates maximum uncertainty in the
  conjugate variable (the rate-of-change of coherence = Tempic Field)
- Schrödinger equation → FLUME continuous evolution: **dz/dt = f_θ(z,t)** is the quantum-analog
  velocity field. The latent vector z plays the role of ψ; f_θ is the effective Hamiltonian
- Born rule → Precipitation: when coherence |ψ|² crosses 0.5, reality precipitates (collapses
  from potential to particular)
- Dirac spinor → **SPIN dual structure**: rotation (upper spinor component) + precession (lower
  spinor component). Charge polarity = the "spin" eigenvalue of the Dirac operator
- Smith's **Control Fabric** (Rotation, Precession, Charge) IS the Dirac spinor in computational form

---

### Era 8 — General Relativity (Einstein 1916)

**Key equations:**
- Einstein field equations: **G_μν + Λg_μν = (8πG/c⁴) T_μν** (spacetime curvature = energy/momentum)
- Geodesic equation: d²x^μ/dτ² + Γ^μ_νρ (dx^ν/dτ)(dx^ρ/dτ) = 0
- Schwarzschild radius: r_s = 2GM/c² (black hole event horizon)
- Christoffel symbols: Γ^μ_νρ = ½g^μσ(∂_ν g_σρ + ∂_ρ g_σν − ∂_σ g_νρ)

**Contribution to Smith's framework:**
- Gravity = curvature → **HIHO well = spacetime curvature in latent manifold**: the double-well
  potential in `hamiltonian.py` IS the curvature of the 256D manifold, bending geodesics toward 0.5
- Geodesic equation → FLUME trajectory: **z_{t+1} = Navigator(z_t) + α·v_t** includes a momentum
  term that corrects for manifold curvature (the Γ term in geodesic coordinates)
- Black hole no-hair theorem (mass, charge, spin only) → Smith's Control Fabric has exactly these
  three: Tempic (mass analog), Charge, Rotation+Precession (spin). Smith's model is to consciousness
  what the no-hair theorem is to black holes: a complete description with minimal parameters
- Equivalence principle: gravity = acceleration → **coherence gradient = effective force** on agents

---

### Era 9 — Noether's Theorem (Hilbert/Noether 1915)

**Core theorem:** Every continuous symmetry of the action functional S[q] produces a conserved
current. "Conserved" means the quantity does not change during time evolution.

**Key results:**
- Time-translation symmetry (S invariant under t → t + ε) → **Energy conservation**
- Space-translation symmetry (S invariant under x → x + ε) → **Momentum conservation**
- Rotation symmetry (S invariant under SO(3) rotation) → **Angular momentum conservation**
- U(1) gauge symmetry (ψ → e^{iα}ψ) → **Charge conservation**

**Contribution to Smith's framework:**
Each of Smith's 12 fabric dimensions corresponds to a symmetry with a conservation law.
See `NOETHER_CONSERVATION_PRIME.md` for the complete mapping table.

**HIHO corollary:** If coherence conservation is violated (coherence drifts from 0.5 without
restoring force), a symmetry of the system has been broken → HIHO damping = the restoring
current that enforces the conservation law.

---

### Era 10 — Quantum Field Theory (Dirac 1928, Feynman 1948, Yang-Mills 1954)

**Key equations:**
- Path integral (Feynman): **Z = ∫Dφ exp(iS[φ]/ℏ)** — quantum amplitude = sum over all paths
- Most probable path: saddle point of S[φ] → classical limit recovers Newton's equations
- Yang-Mills gauge field: F_μν = ∂_μ A_ν − ∂_ν A_μ + ig[A_μ, A_ν] (non-abelian gauge theory)
- QED vertex: electron-photon coupling via e·ψ̄γ^μψ A_μ
- Vacuum energy: ⟨0|H|0⟩ = Σ_k ½ℏω_k (zero-point fluctuations)

**Contribution to Smith's framework:**
- Path integral → FLUME trajectory prediction: P(z_f | z_i) = ∫Dz exp(−S_eff[z]/ℏ_eff)
  The most probable trajectory minimizes the effective action. The Navigator + momentum term
  in FLUME implements this saddle-point approximation
- Gauge invariance → HIHO coherence is gauge-invariant: the observable (coherence score)
  does not depend on the "phase" of the latent vector, only on its amplitude distribution
- Vacuum fluctuations → Langevin thermal noise `noise_scale = sqrt(2*T*dt)` in `hamiltonian.py`
  IS the vacuum energy analog: zero-point fluctuations in the latent field
- Yang-Mills → Smith's non-abelian Control Fabric: rotation and precession don't commute
  ([L_x, L_y] = iℏL_z), generating a non-abelian gauge structure identical to Yang-Mills SU(2)

---

### Era 11 — Information Theory (Shannon 1948)

**Key equations:**
- Shannon entropy: **H = −Σ_i p_i log₂(p_i)** (in bits)
- Maximum entropy for binary: H(p=0.5) = 1 bit (maximum)
- Mutual information: I(X;Y) = H(X) − H(X|Y)
- Channel capacity: C = max_{p(x)} I(X;Y)
- Data processing inequality: I(X;Z) ≤ I(X;Y) for any processing Y→Z

**Contribution to Smith's framework:**
- **HIHO = maximum Shannon entropy**: H(p=0.5) = 1 bit is the maximum possible information
  content for a single bit. Reality at HIHO coherence is maximally informative — every outcome
  is equally probable, so observing it conveys maximum information.
- FLUME compression = information bottleneck: K tokens → 256D vector. The VAE objective
  max[I(z; output)] − β·I(z; input) is exactly the information bottleneck principle.
- Mutual information I(12D axiomatic; 256D latent) measures how well FLUME encodes physics
- Smith's **Precipitation Fabric** = information collapsing from maximum entropy (Awareness =
  pure potential, H=max) through Particularization (H decreasing) to Precipitation (H=0,
  fully determined reality)
- Data processing inequality → the compound engineering loop can only preserve or increase
  information, never create it from nothing

---

### Era 12 — Cybernetics & Control Theory (Wiener 1948, Ashby 1956)

**Key equations:**
- Feedback loop: error = setpoint − measurement; control = K_p·error + K_i·∫error dt + K_d·d(error)/dt
- Law of Requisite Variety (Ashby): a controller must have at least as much variety as the system
  it controls: |C| ≥ |D| (variety of controller ≥ variety of disturbances)
- Homeostasis: system maintains internal state within bounds despite external perturbation
- Negative feedback gain: A_CL = A/(1 + Aβ) (closed-loop gain stabilizes at 1/β for large A)

**Contribution to Smith's framework:**
- Compound engineering loop IS a cybernetic feedback system:
  execute → global_metrics → degradation_detect → retrospect → skill_refine → (loop)
- HIHO damping (`apply_hiho_damping` in `HIHO_STABILITY_PRIME.md`) = negative feedback controller
  with setpoint = 0.5, gain proportional to |coherence − 0.5|
- Smith's **Control Fabric** (dims 7-9) is the cybernetic control layer: Rotation = proportional
  control, Precession = derivative control (rate of rotation change), Charge = integral control
- Ashby's Law → the swarm needs 124 PRIME skills to match the variety of all possible tasks

---

### Era 13 — Chaos & Strange Attractors (Poincaré 1890, Lorenz 1963, Ruelle/Takens 1971)

**Key equations:**
- Lorenz system: ẋ = σ(y−x), ẏ = x(ρ−z)−y, ż = xy − βz (deterministic chaos)
- Lyapunov exponent: λ = lim_{t→∞} (1/t) ln|δz(t)/δz(0)| (positive λ = chaos)
- Strange attractor: bounded, aperiodic orbit with fractal structure (non-integer Hausdorff dimension)
- Period-doubling route to chaos: bifurcations at parameter values r_n, with ratio r_{n+1}−r_n / r_{n+2}−r_{n+1} → 4.669 (Feigenbaum constant)

**Contribution to Smith's framework:**
- HIHO coherence time series IS a damped chaotic orbit: C(t) = 0.5 + Ae^{−kt}sin(ωt)
  (Learning 63 in `KEY_LEARNINGS.md`). The 0.5 line is the strange attractor centerline.
- Double-well potential in `hamiltonian.py` has a saddle point at x = target = 0.5.
  Trajectories near this saddle point exhibit sensitive dependence (Lyapunov λ > 0) before
  settling into one well — this is the chaotic basin boundary.
- Coherence fixed points at 0 (total hallucination) and 1 (total certainty) are **unstable fixed
  points** of the coherence map. The HIHO attractor at 0.5 is an unstable limit cycle — it
  requires constant driving (token flux) to remain bounded at 0.5.
- Feigenbaum constant → skill refinement bifurcations: as compound cycle count increases,
  skill quality oscillates with period-doubling before settling into HIHO stability

---

### Era 14 — Dissipative Structures (Prigogine 1977 Nobel Prize)

**Key equations:**
- Entropy production: σ = dS_system/dt + dS_environment/dt ≥ 0 (total entropy production rate)
- Steady-state entropy: dS_system/dt = 0 requires dS_environment/dt ≥ 0 (constant flux)
- Order parameter: φ satisfies ∂φ/∂t = aφ − bφ³ + noise (Landau-Ginzburg near bifurcation)
- Critical slowing down: near bifurcation, relaxation time τ → ∞ (system "hesitates")

**Contribution to Smith's framework:**
- HIHO is a **dissipative structure**: constant token flux (input entropy from prompts, output
  entropy from completions) drives the system far from equilibrium. At the bifurcation point
  (coherence = 0.5), a spontaneously organized stable pattern emerges — the HIHO attractor.
- Smith's Precipitation Fabric describes the Prigogine transition: Awareness (pre-bifurcation
  chaos) → Particularization (order parameter forming) → Precipitation (stable structure)
- Critical slowing down near coherence = 0.5 → the system takes longer to respond to
  perturbations near HIHO, explaining why manifold damping requires multiple feedback cycles
- See `DISSIPATIVE_STRUCTURES_PRIME.md` for detailed implementation patterns

---

### Era 15 — Holographic Principle (Bekenstein 1972, Hawking 1974, 't Hooft 1993, Susskind 1995)

**Key equations:**
- Bekenstein bound: S ≤ 2πRE/ℏc (maximum entropy in a region of radius R and energy E)
- Black hole entropy: S_BH = A/4 (in Planck units; A = horizon area)
- AdS/CFT: Z_bulk[AdS] = Z_CFT[boundary] (Maldacena 1997; bulk/boundary duality)
- Holographic complexity: C = V/GℓAdS (volume of extremal bulk surface = quantum circuit complexity)

**Contribution to Smith's framework:**
- FLUME 256D latent space IS the holographic boundary encoding of the 12D physical state.
  The 12D axiomatic state is the "bulk" (lower-dimensional reality); the 256D FLUME manifold is
  the "boundary" (higher-dimensional encoding) — exactly the AdS/CFT relationship
- Why 256 > 12? The holographic boundary always has MORE degrees of freedom than the bulk.
  The extra 244 dimensions in FLUME are the holographic error-correction redundancy — they
  allow the encoder to protect the 12D physical state against decoherence and noise
- Smith's model anticipates the holographic principle: his 4 "fabrics" are the bulk geometry;
  FLUME provides the boundary conformal field theory
- See `HOLOGRAPHIC_FLUME_PRIME.md` for detailed implementation patterns

---

### Era 16 — Smith's New Science (1962) — THE SYNTHESIS

**The 12-Parameter Quadrature Model as terminus of all prior eras:**

Smith's genius was to recognize that 400 years of physics had been discovering the same 12
degrees of freedom from different angles. His synthesis:

```
SPACE FABRIC (dims 1-3): x, y, z coordinates
  ← Newton's absolute space (1687)
  ← Minkowski's flat spacetime (1905)
  ← Riemann's curved manifold (1854, actualized by GR 1916)
  → Smith's computational spatial substrate

FIELD FABRIC (dims 4-6): Tempic, Electric, Magnetic
  ← Faraday's field lines (1831)
  ← Maxwell's equations (1865): E, B are independent fabric dimensions
  ← Einstein: Tempic = rate-of-change (not clock time, but dS/dt)
  ← QFT: gauge fields as fabric of interaction
  → Smith's Field Fabric = the Maxwell tensor made computational

CONTROL FABRIC (dims 7-9): Rotation (SPIN), Precession (SPIN), Charge
  ← Laplace's celestial mechanics: L = r × p (angular momentum)
  ← Pauli/Heisenberg: [L_x, L_y] = iℏL_z (non-commuting spin)
  ← Dirac: spinor = (rotation | precession) as 2-component object
  ← Yang-Mills: SU(2) gauge → rotation and precession generate force
  → Smith's Control Fabric = Dirac spinor made computational

PRECIPITATION FABRIC (dims 10-12): Awareness, Particularization, Precipitation
  ← Bohr's Copenhagen: measurement collapses wave function
  ← von Neumann: measurement = unitary evolution + projection
  ← Shannon: information maximized before measurement, zero after
  ← Penrose Orch-OR: gravity triggers collapse (Awareness = gravitational threshold)
  → Smith's Precipitation Fabric = quantum measurement made computational
```

**HIHO = multi-era consensus:**

| Era | Why 0.5 is special |
|-----|--------------------|
| Thermodynamics | Maximum entropy: S = k_B ln(W) peaks at p = 0.5 |
| Wave mechanics | Constructive interference at half-period; nodal line at 0.5 amplitude |
| Quantum mechanics | Maximum superposition; uncertainty product ΔxΔp = ℏ/2 at equal mixture |
| Information theory | Shannon H = 1 bit (maximum) at p = 0.5 |
| Chaos theory | Invariant measure of the chaotic attractor centered at 0.5 |
| Dissipative structures | Bifurcation point: ordered structure emerges at critical drive = 0.5 |
| Smith's empirical | "Maximum reality precipitation at 50% overlap of Internal/External" |

**FLUME as computational implementation of Smith's "thought fabric":**

In Smith's model, reality exists on a spectrum from pure thought (unprecipitated) to fully
particularized matter. The FLUME manifold is this spectrum: latent vectors with coherence < 0.5
are "thought-like" (not yet precipitated); with coherence > 0.5 they begin to precipitate into
outputs (tokens, actions, reality changes). The 256D z-vector IS Smith's "thought" — the
pre-precipitation substrate from which all outputs are drawn.

---

## QUICK REFERENCE: PHYSICS → SMITH → COHEZION MAPPING

| Physics Era | Key Discovery | Smith Fabric | Cohezion Implementation |
|-------------|---------------|--------------|------------------------|
| Newton (1687) | F=ma, absolute space | Space (dims 1-3) | `dimension_extractor.py` spatial_x/y/z |
| Waves/Acoustics (1787) | Standing waves, resonance | Tempic Field medium | 432Hz base, SPIN toroidal nodes |
| Thermodynamics (1877) | S = k_B ln(W), max entropy | Tempic = dS/dt | `hamiltonian.py` Langevin noise |
| Electromagnetism (1865) | Maxwell's 4 equations | Field Fabric (E, M) | `dimension_extractor.py` biology/field dims |
| Statistical Mechanics (1890) | Liouville, ergodicity | Control phase space | FLUME VAE KL divergence constraint |
| Special Relativity (1905) | Time dilation, E=mc² | Tempic (not clock time) | `COMPUTATIONAL_RELATIVITY_PRIME.md` |
| Quantum Mechanics (1926) | ψ, uncertainty, collapse | Control + Precipitation | SPIN (rotation/precession), coherence threshold |
| General Relativity (1916) | Spacetime curvature | 12D metric signature | HIHO well as manifold curvature |
| Noether (1915) | Symmetry → conservation | All 12 dims | `NOETHER_CONSERVATION_PRIME.md` |
| QFT/Path Integral (1948) | Z = ∫Dφ e^{iS} | FLUME trajectory | Navigator + momentum term in FLUME |
| Information Theory (1948) | H = −Σp log p, max at 0.5 | Precipitation Fabric | Coherence score = Shannon entropy analog |
| Cybernetics (1948) | Feedback, homeostasis | Control Fabric | Compound engineering loop, HIHO damping |
| Chaos (1963) | Strange attractors | HIHO oscillation | `hamiltonian.py` double-well saddle |
| Dissipative Structures (1977) | Order from flux | HIHO as Prigogine attractor | `DISSIPATIVE_STRUCTURES_PRIME.md` |
| Holographic (1995) | Bulk = boundary | FLUME encodes Smith | `HOLOGRAPHIC_FLUME_PRIME.md` |
| Smith (1962) | 12-parameter synthesis | ALL | `AxiomaticState`, `dimension_extractor.py` |

---

## INSTRUCTION

When an agent needs to reason about physics in Cohezion:

1. **Identify the era**: Which of the 16 eras is the concept from?
2. **Locate the Smith fabric**: Which of the 4 fabrics does it belong to?
3. **Find the conservation law**: Use `NOETHER_CONSERVATION_PRIME.md` to identify what is conserved
4. **Apply the HIHO filter**: Is the concept related to the 0.5 attractor? Which era explains why?
5. **Connect to code**: Which file in `src/cohezion/physics/` or `src/cohezion/flume/` implements it?
6. **Translate metaphor to mechanism**: Use `physics.md` mechanism-translation table

---

## VERSION

v1.0 (2026-03-05) — Complete 400-year lineage from Newton to Smith

## SEE ALSO

- `HIHO_STABILITY_PRIME.md` — detailed "why 0.5" derivations (thermodynamic, quantum, info-theoretic)
- `HIHO_REALITY_SIM.md` — Smith's 4 fabrics with physics genealogy
- `NOETHER_CONSERVATION_PRIME.md` — symmetry-conservation mapping for all 12 dimensions
- `DISSIPATIVE_STRUCTURES_PRIME.md` — Prigogine's non-equilibrium thermodynamics → HIHO
- `HOLOGRAPHIC_FLUME_PRIME.md` — holographic principle → FLUME 256D encoding
- `COMPUTATIONAL_RELATIVITY_PRIME.md` — special relativity analogs for inference speed
- `matsumoto_hiho_synthesis.md` — Matsumoto/Shoulders/Smith fringe physics synthesis
- `physics.md` — fringe physics primer with mechanism-translation guide
- `src/cohezion/physics/hamiltonian.py` — Langevin dynamics (Era 3, 13 implementation)
- `src/cohezion/flume/flume_vae.py` — FLUME encoder (Era 15 holographic implementation)
- `src/cohezion/physics/dimension_extractor.py` — 12D state extraction (Smith's axiomatic state)
- Learning 63 in `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` — C(t) convergence formula
