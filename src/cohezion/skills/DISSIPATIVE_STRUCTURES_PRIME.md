# SKILL: DISSIPATIVE_STRUCTURES_PRIME

## DOMAIN EXPERTISE

You understand Ilya Prigogine's Nobel Prize-winning framework (1977) for non-equilibrium
thermodynamics and dissipative structures. You know how systems **far from equilibrium**
self-organize into ordered, stable patterns through constant energy/entropy flux — and how
this explains the HIHO attractor in Cohezion. The HIHO stability at 0.5 coherence is NOT
an equilibrium state — it is a **dissipative structure** that requires constant token flux
to maintain. Understanding this distinction prevents incorrect attempts to "freeze" HIHO
by cutting off input.

## KEY TEXTS & CONCEPTS

- **Ilya Prigogine**: *Order Out of Chaos* (1984); Nobel Prize lecture (1977)
- **Bénard convection (1901)**: Thermal flux creates hexagonal convection cells (order from chaos)
- **Belousov-Zhabotinsky (BZ) reaction (1959)**: Chemical oscillator — spontaneous
  spatiotemporal patterns in far-from-equilibrium chemistry
- **Brusselator model**: Simple two-reaction scheme showing limit cycle oscillation
- **Haken's synergetics**: Order parameters and slaving principle (1977)
- **Landau-Ginzburg theory**: Order parameter φ near second-order phase transitions
- **Wilbert B. Smith**: Precipitation at 0.5 coherence = Prigogine bifurcation point

---

## CORE FRAMEWORK: EQUILIBRIUM vs. DISSIPATIVE STRUCTURES

### Equilibrium thermodynamics (classical — Boltzmann, Gibbs)
- System evolves toward maximum entropy (S_max)
- Final state: **dead equilibrium** — no gradients, no structure, no function
- HIHO at equilibrium: coherence drifts to 0.5 and **stays there forever** with no dynamics

### Non-equilibrium thermodynamics (Prigogine)
- System is **coupled to environment** via constant flux (energy/matter/information in, entropy out)
- Far enough from equilibrium: the system undergoes a **bifurcation** — a sudden qualitative
  change in behavior from disordered to ordered
- Result: a **dissipative structure** — stable, functional, self-organized, but requiring
  continuous flux to persist

**Key distinction:** Equilibrium HIHO = boring fixed point. Dissipative HIHO = living attractor
that oscillates, adapts, processes information, and generates outputs — but disappears if you
cut the token flux.

---

## THE BÉNARD CONVECTION ANALOGY

Heated fluid between two plates:
- **Below critical Rayleigh number Ra_c**: uniform conduction (equilibrium → boring)
- **At Ra_c**: bifurcation! Spontaneous hexagonal convection cells form
- **Above Ra_c**: ordered cellular structure dissipates heat much more efficiently

**Cohezion analog:**
- Ra_c ↔ minimum token throughput (tokens/sec): below this, the agent runs cold, no HIHO structure
- Convection cells ↔ PRIME skills: stable dissipative structures for processing semantic flux
- Hexagonal packing ↔ the Expert Domain Lattice (EDL): optimal tiling of cognitive space
- Boundary heat flux ↔ compound engineering loop: constant injection of new tasks

**Formula for Cohezion Rayleigh analog:**
```
Ra_cohezion = (token_rate × context_richness) / (coherence_diffusivity × forgetting_rate)
```
For HIHO structure to form: Ra_cohezion > Ra_c ≈ 1707.8 (Bénard's critical value, dimensionless)

---

## THE BELOUSOV-ZHABOTINSKY REACTION ANALOGY

The BZ reaction oscillates between two chemical states (oxidized/reduced) spontaneously,
generating beautiful spiral waves. It demonstrates that **chemistry can have a clock** —
without biological machinery, purely through non-equilibrium thermodynamics.

**Cohezion analog (the compound loop as BZ reaction):**

```
State A: Agent is reasoning (oxidized — high cognitive energy)
    ↓ produces: tokens, decisions, actions
State B: Agent is reflecting (reduced — integrating results)
    ↓ produces: skill updates, learnings, coherence adjustments
    ↓ returns to State A (loop closes)
```

The compound engineering loop IS a BZ reaction: two states cycling spontaneously,
generating spatiotemporal patterns (PRIME skill updates) across the knowledge graph.

**Brusselator equations (simplified compound loop model):**
```
dA/dt = 1 - (B+1)A + A²B     [A = active reasoning state]
dB/dt = BA - A²B              [B = reflection state]
```
Limit cycle (oscillation) exists when B > 1 + A² — the system oscillates between reasoning
and reflection without settling. This is the **healthy compound loop condition**.

---

## ORDER PARAMETER THEORY (Landau-Ginzburg)

Near a phase transition (bifurcation), a single "slow variable" — the **order parameter φ** —
governs the system's behavior. All other ("fast") variables are slaved to φ.

**Landau-Ginzburg equation near HIHO bifurcation:**
```
∂φ/∂t = aφ − bφ³ + D∇²φ + noise
```
where:
- φ = coherence deviation from 0.5: φ = C − 0.5
- a = control parameter (distance from bifurcation; a > 0 = ordered, a < 0 = disordered)
- b > 0 = saturation (prevents φ → ∞)
- D = diffusion in latent space (FLUME momentum term)
- noise = Langevin thermal noise from `hamiltonian.py`

**Haken's slaving principle:** Near HIHO (a → 0), all 256 FLUME dimensions are slaved to
the single order parameter φ = C − 0.5. This is why **monitoring coherence is sufficient**
for full system diagnosis — all 256 dimensions "follow" the coherence.

---

## CRITICAL SLOWING DOWN

Near the HIHO bifurcation point, a universal phenomenon occurs: the system's relaxation
time τ diverges to infinity.

```
τ ∼ |a|^{−ν}   (ν = critical exponent, typically 0.5-1.0)
```

**In Cohezion:** As coherence approaches exactly 0.5, perturbations decay **very slowly**.
This is why multiple damping cycles are needed near HIHO — it's not sluggishness, it's
critical slowing down. The HIHO damping code should account for this:

```python
def hiho_damping_with_critical_slowing(coherence: float, stability_score: float,
                                        latent_vector, rng=None):
    """
    HIHO damping that accounts for Prigogine critical slowing down.
    Near coherence = 0.5, use stronger damping because τ is large.
    """
    import numpy as np

    if rng is None:
        rng = np.random.default_rng()

    deviation = abs(coherence - 0.5)

    # Critical slowing down: damping strength inversely proportional to deviation
    # Far from 0.5: strong restoring force (fast return)
    # Near 0.5: gentle noise injection (slow dynamics, don't over-correct)
    if deviation < 0.05:
        # In the critical zone: inject Langevin noise (thermal fluctuations)
        noise_strength = 0.15
        drift = (rng.random(len(latent_vector)) - 0.5) * noise_strength
        return latent_vector + drift
    elif deviation > 0.3:
        # Far from HIHO: strong damping (like underdamped oscillator)
        restoring = -(coherence - 0.5) * 0.8
        correction = np.full(len(latent_vector), restoring / len(latent_vector))
        return latent_vector + correction
    else:
        # Normal HIHO zone: standard damping
        return latent_vector
```

---

## DETECTING PRIGOGINE BIFURCATION IN COHEZION

Signs that the compound loop is approaching a Prigogine bifurcation (new structure forming):

```python
def detect_prigogine_bifurcation(coherence_history: list[float]) -> dict:
    """
    Detect onset of dissipative structure formation in coherence time series.

    Signatures of approaching bifurcation:
    1. Critical slowing down: autocorrelation time τ increasing
    2. Variance increasing: fluctuations grow near bifurcation
    3. Return-map eigenvalue approaching 1.0 (loss of exponential relaxation)
    """
    import numpy as np

    if len(coherence_history) < 20:
        return {"bifurcation_detected": False, "reason": "insufficient_history"}

    series = np.array(coherence_history)
    centered = series - 0.5

    # 1. Autocorrelation at lag-1 (should increase near bifurcation)
    if len(centered) > 1:
        autocorr = np.corrcoef(centered[:-1], centered[1:])[0, 1]
    else:
        autocorr = 0.0

    # 2. Variance (should increase near bifurcation)
    variance = np.var(centered)

    # 3. Trend in variance (variance should be increasing)
    half = len(centered) // 2
    var_early = np.var(centered[:half])
    var_late = np.var(centered[half:])
    variance_increasing = var_late > var_early

    bifurcating = (
        autocorr > 0.7 and          # Critical slowing down
        variance > 0.01 and          # Growing fluctuations
        variance_increasing          # Trend toward bifurcation
    )

    return {
        "bifurcation_detected": bifurcating,
        "autocorrelation_lag1": autocorr,
        "variance": variance,
        "variance_trend": "increasing" if variance_increasing else "stable",
        "interpretation": (
            "New PRIME skill may be self-organizing" if bifurcating
            else "Normal HIHO oscillation"
        ),
    }
```

---

## ENTROPY PRODUCTION IN THE COMPOUND LOOP

Prigogine showed that dissipative structures have **minimum entropy production** at their
stable operating point (Prigogine's theorem of minimum entropy production for stationary states).

```
σ_min = dS_total/dt|_{stationary}  ← minimum compatible with boundary conditions
```

**For Cohezion:** At HIHO (coherence ≈ 0.5), the entropy production rate is minimized
while keeping the system alive. This means:
- Too few tokens → system falls below Ra_c → no HIHO structure (dead)
- Too many tokens → entropy production exceeds σ_min → coherence destabilized → chaotic
- Optimal rate → σ = σ_min → HIHO maintained → maximum cognitive output per entropy cost

This is the thermodynamic justification for **throttled scouting** (THROTTLED_SCOUT_PRIME.md):
sequential, paced token generation minimizes σ while maintaining the dissipative HIHO structure.

---

## VERSION

v1.0 (2026-03-05)

## SEE ALSO

- `PHYSICS_LINEAGE_PRIME.md` — Era 14 (Dissipative Structures) in the 400-year lineage
- `HIHO_STABILITY_PRIME.md` — Derivation 4 (dynamical systems) and Derivation 6 (Smith empirical)
- `THROTTLED_SCOUT_PRIME.md` — token throttling as entropy-production minimization
- `COMPOUND_ENGINEERING_PRIME.md` — compound loop as BZ reaction
- `src/cohezion/physics/hamiltonian.py` — Langevin dynamics = thermal noise in dissipative system
- `src/cohezion/knowledge_graph/KEY_LEARNINGS.md` — Learning 63: C(t) convergence formula
