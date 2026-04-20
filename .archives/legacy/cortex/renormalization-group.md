---
title: "Renormalization Group"
date: 2026-03-09
tags: [concept, physics, mathematics, scaling, universality, critical-phenomena]
aspect: knower
neural:
  activation: 1.0
  stage: mature
  synapse_in: 20
  synapse_out: 19
---

# Renormalization Group

## Definition

The renormalization group (RG) is a mathematical framework for studying how physical systems change under changes of scale. Developed by Kenneth Wilson (Nobel Prize 1982), it explains the deepest mystery of phase transitions — universality: why completely different physical systems exhibit identical behavior near critical points. The RG shows that under successive coarse-graining (zooming out), the microscopic details wash away and only a few "relevant" parameters survive, determining the macroscopic behavior.

The central insight: physics at different scales is connected by a flow in parameter space. Starting from microscopic parameters, the RG flow carries the system toward fixed points — special parameter values where the system looks the same at all scales (scale invariance). Near a fixed point, the system's behavior is determined by the fixed point's properties, not by the original microscopic details. This is why universality works.

"As above, so below" — the ancient Hermetic maxim — is literally the statement that the system is at an RG fixed point.

## Key Properties

### Block-Spin Transformation (Kadanoff, 1966)

The conceptual foundation of the RG, illustrated with the 2D Ising model:

1. **Divide** the lattice into blocks of b×b spins
2. **Coarse-grain:** Replace each block with a single "block spin" (majority rule or average)
3. **Rescale:** Shrink the lattice by factor b to restore the original lattice spacing
4. **Renormalize:** Find the effective Hamiltonian H' for the block spins

The transformation defines a map in parameter space:
> K' = R_b(K)

where K = {K₁, K₂, ...} are the coupling constants. Iterating this map generates the **RG flow**.

### Fixed Points

A fixed point K* satisfies:
> K* = R_b(K*)

At K*, the system looks identical at all scales — it is **scale-invariant**. Fixed points classify the universality classes of phase transitions.

**Types of fixed points:**
- **Trivial (high-T):** K* = 0 — disordered, uncorrelated phase
- **Trivial (low-T):** K* = ∞ — fully ordered phase
- **Critical (Wilson-Fisher):** Non-trivial K* — the critical point itself. Unstable in some directions (relevant operators), stable in others (irrelevant operators)

### Relevant, Irrelevant, and Marginal Operators

Linearizing the RG transformation near K*:
> δK' = R'(K*) · δK = M · δK

The eigenvalues λ_i of the linearized RG matrix M determine operator relevance. Since the rescaling factor is b, we write λ_i = b^{y_i}:

| Eigenvalue | y_i | Name | Effect |
|-----------|-----|------|--------|
| λ > 1 | y_i > 0 | **Relevant** | Grows under RG flow — drives system away from fixed point |
| λ < 1 | y_i < 0 | **Irrelevant** | Shrinks under RG flow — washes out at large scales |
| λ = 1 | y_i = 0 | **Marginal** | Requires higher-order analysis |

**Universality explained:** Two systems flow to the same fixed point if they differ only in irrelevant operators. The relevant operators (temperature deviation, external field) determine the critical exponents — which are properties of the fixed point, not of the microscopic Hamiltonian.

### Scaling Relations

Near the critical fixed point, the correlation length scales as:
> ξ ~ |t|^{-ν}  where ν = 1/y_t

and the order parameter as:
> m ~ |t|^β

All critical exponents are determined by the RG eigenvalues y_t (thermal) and y_h (magnetic). The **scaling relations**:

> α + 2β + γ = 2  (Rushbrooke)
> γ = ν(2 - η)    (Fisher)
> dν = 2 - α       (Josephson/hyperscaling)

reduce the number of independent exponents to TWO (y_t, y_h), or equivalently (ν, η).

## Mathematical Framework

### Wilson's Momentum-Shell RG

In field theory, the RG integrates out high-momentum modes:

Starting from the partition function Z = ∫ Dφ e^{-S[φ]} where S is the action:

1. **Separate:** Split φ into slow modes (k < Λ/b) and fast modes (Λ/b < k < Λ)
2. **Integrate out fast modes:** Z = ∫ Dφ_slow e^{-S_eff[φ_slow]} where S_eff = -ln ∫ Dφ_fast e^{-S[φ_slow + φ_fast]}
3. **Rescale:** k → bk, φ → b^{(d-2+η)/2}φ to restore the UV cutoff to Λ

This generates a flow in the space of all possible actions S. The β-function:
> β(g) = Λ ∂g/∂Λ

describes how coupling constants g run with scale.

### The ε-Expansion (Wilson-Fisher, 1972)

Near d = 4 (upper critical dimension), expand in ε = 4 - d:

For scalar φ⁴ theory: S = ∫ d^dx [(∇φ)²/2 + rφ² + u(φ²)²]:

The Wilson-Fisher fixed point (to one loop):
> u* = ε/[8π²(N+8)/6] + O(ε²)

where N is the number of field components. Critical exponents:
> η = (N+2)ε²/[2(N+8)²] + O(ε³)
> ν = 1/2 + (N+2)ε/[4(N+8)] + O(ε²)

For the 3D Ising model (N=1, ε=1): ν ≈ 0.630, β ≈ 0.326 — in excellent agreement with exact results.

### RG in Quantum Field Theory

In QFT, the RG relates physics at different energy scales. The running coupling constant g(μ) satisfies:

> μ dg/dμ = β(g)

**QED:** β(e) = e³/(12π²) > 0 — coupling increases at high energy (Landau pole at ~10^{286} GeV).

**QCD:** β(g_s) = -(11N_c - 2N_f)g_s³/(48π²) < 0 for N_f < 33/2 — **asymptotic freedom** (Gross, Wilczek, Politzer, Nobel 2004). The strong coupling decreases at high energy: quarks are free at short distances, confined at long distances.

### Conformal Field Theory at Fixed Points

At an RG fixed point, the system has not just scale invariance but (in most physical cases) full conformal invariance. In 2D, the conformal group is infinite-dimensional (Virasoro algebra), leading to exact solutions:

> <φ(z₁)φ(z₂)> = 1/|z₁-z₂|^{2Δ}

where Δ is the scaling dimension. The central charge c classifies 2D conformal field theories:
- c = 1/2: 2D Ising model
- c = 1: free boson (Gaussian model)
- c = 26: critical dimension of bosonic string theory

### Functional RG (Wetteringia Equation)

The exact functional RG equation (Wetteringia, 1993):

> ∂Γ_k/∂k = (1/2) Tr[(Γ_k^{(2)} + R_k)^{-1} · ∂R_k/∂k]

where Γ_k is the effective average action at scale k, Γ_k^{(2)} is its second functional derivative, and R_k is a regulator function. This is an exact equation — all approximations enter through truncation of Γ_k.

## Examples

- **3D Ising universality class:** Water critical point (647 K, 22 MPa), uniaxial ferromagnet (iron, 1043 K), binary fluid demixing — all share ν = 0.630, β = 0.326, γ = 1.237, predicted by ε-expansion and confirmed experimentally.
- **Asymptotic freedom in QCD:** At CERN's LHC (√s = 13 TeV), the strong coupling α_s ≈ 0.12, compared to α_s ≈ 0.35 at 1 GeV. This running is the RG in action — measurements at different energies agree with the β-function prediction.
- **Kosterlitz-Thouless transition (2D):** The 2D XY model has a topological phase transition (vortex unbinding) with NO symmetry breaking and NO divergent order parameter — discovered via RG analysis. Nobel Prize 2016 (Kosterlitz, Thouless, Haldane).
- **Turbulence (Kolmogorov cascade):** Energy injected at large scales cascades to small scales through a self-similar inertial range. The energy spectrum E(k) ~ k^{-5/3} is an RG fixed point of the Navier-Stokes equations.

## Primary Sources

- Wilson, K.G. (1971). "Renormalization Group and Critical Phenomena. I. Renormalization Group and the Kadanoff Scaling Picture." *Physical Review B*, 4(9), 3174-3183.
- Wilson, K.G. & Fisher, M.E. (1972). "Critical Exponents in 3.99 Dimensions." *Physical Review Letters*, 28(4), 240-243.
- Kadanoff, L.P. (1966). "Scaling Laws for Ising Models Near T_c." *Physics*, 2(6), 263-272.
- Goldenfeld, N. (1992). *Lectures on Phase Transitions and the Renormalization Group*. Westview Press.
- Zinn-Justin, J. (2002). *Quantum Field Theory and Critical Phenomena*. 4th ed. Oxford University Press.
- Cardy, J. (1996). *Scaling and Renormalization in Statistical Physics*. Cambridge University Press.

## Related Concepts

- [[thermodynamics]] — Phase transitions are the physical phenomena the RG explains; critical exponents are RG eigenvalues
- [[noether-theorem]] — Conformal invariance at RG fixed points gives conserved dilatation current
- [[symmetry-breaking]] — The RG flow away from the critical fixed point is symmetry breaking in parameter space
- [[quantum-mechanics]] — QFT renormalization cures UV divergences; the RG makes this systematic
- [[chaos-theory]] — The RG transformation itself can exhibit chaotic behavior; strange attractors in coupling space
- [[cellular-automata]] — Block-spin transformation IS a cellular automaton rule: coarse-grain each block by majority vote
- [[information-theory-it-from-bit]] — RG = information compression: irrelevant operators are the information discarded at each scale
- [[sacred-geometry]] — Scale invariance at fixed points produces self-similar (fractal) structure
- [[planck-scale]] — The RG connects Planck-scale physics to low-energy observables; running couplings extrapolate to Planck scale
- [[quantum-field-theory]] — RG is central to QFT; running couplings, beta functions, asymptotic freedom
- [[statistical-mechanics]] — RG explains universality of critical exponents near phase transitions
- [[emergence-and-self-organized-criticality]] — SOC systems are at RG fixed points without fine-tuning
- [[holographic-principle]] — the bulk radial direction in AdS/CFT IS the RG scale
- [[topology-in-physics]] — Kosterlitz-Thouless transition is a topological RG flow
- [[fluid-dynamics]] — Kolmogorov cascade E(k) ~ k^{-5/3} is an RG fixed point of Navier-Stokes
- [[exotic-vacuum-objects]] — morning glory morphology is scale-invariant across 9 orders of magnitude: an RG fixed point
- [[agents-as-exotic-vacuum-objects]] — agent identity stability across context lengths = scale invariance = RG
- [[the-new-science-framework]] — the 12 parameters as relevant operators; HIHO threshold as critical point
- [[theory-of-everything-synthesis]] — RG connects all scales of the TOE: nuclear → mesoscale → computational

## Relevance to Cohezion

"As Above, So Below" IS the RG. The vault computes the same metrics at every scale:

| Scale | Parameters | RG Step |
|-------|-----------|---------|
| Single neuron | activation, stage, synapses | Microscopic |
| Country | health, elder count, Songlines | Block-spin: average over constituent neurons |
| Aspect (K/T/D) | aggregate health, dominant Countries | Coarse-grain Countries into Aspects |
| Whole vault | total coherence, lifecycle distribution | Final macroscopic observable |

The **relevant operators** — the features that survive coarse-graining and determine vault-scale behavior — are: (1) average activation (the "temperature"), (2) link density (the "coupling strength"). These are the only two numbers that matter at the vault scale. All other features (word count, recency, individual tags) are **irrelevant operators** — they wash out under RG flow. This is why the 12D projection works despite seeming over-determined: at the vault scale, most dimensions are irrelevant. The RG predicts which of the 12 dimensions dominate at each scale — and this is exactly what PCA on the 12D vectors reveals: the first 2-3 principal components capture 80%+ of the variance. Those principal components ARE the relevant operators of the vault's RG flow.
