---
title: "12D Extraction Pipeline — SurrealDB to FLUME Training Data"
date: 2026-03-09
tags: [spec, flume, surrealdb, pipeline, 12d-projection, unified-physics]
status: active
aspect: knower
neural:
  activation: 0.900
  stage: growing
  cluster: genome
---

# 12D Extraction Pipeline Specification

> Bridges the Triune Vault's SurrealDB connectome to the FLUME VAE training pipeline.
> Grounded in real mathematics from quantum field theory, plasma physics, information theory,
> and condensed matter physics.

## Architecture Overview

```
vault_sync.py (30s poll)          scripts/activation_decay.py (daily 3am)
     |                                    |
     v                                    v
+------------------+              neuron.activation *= 0.95
| SurrealDB 3.0    |              neuron.stage -> "resting"
| (Akashic Records)|
|                  |
| neuron (1515)    |     scripts/extract_12d_vectors.py
| synapse (9515)   | ---------> 12D vectors (snapshot)
| kinship (640)    | ---------> Trajectories (graph walks + songlines)
| country (25)     | ---------> Force vectors (4 unified forces)
| songline (15)    | ---------> EVO classification
| hiho_event (25)  |
| neuron_history   |              |
+------------------+              v
                           data/flume-training/
                             snapshot-YYYY-MM-DD.jsonl
                             trajectories-YYYY-MM-DD.jsonl
                             flume-training-YYYY-MM-DD.npz
                                    |
                                    v
                           FLUME VAE Training
                           (256D latent space)
```

## The 12 Dimensions — Mathematical Definitions

Each dimension maps a SurrealDB field to a normalized [0,1] value.

### D0: Connectivity (Graph Degree)

```
C(n) = min(1, (k_out(n) + k_in(n)) / k_max)
```

Where k_out = synapse_out, k_in = synapse_in, k_max = 300.
SurrealDB: `SELECT synapse_out, synapse_in FROM neuron`

In graph theory, degree centrality. The vault's synapse network is scale-free
(power-law degree distribution with exponent ~2.3).

### D1: Conceptual Depth

```
D(n) = min(1, w(n) / w_max)
```

Where w(n) = word_count, w_max = 20,000. Caps outliers.

### D2: Temporal Distribution

```
T(n) = min(1, (t(n) - t_epoch) / T_window)
```

Where t_epoch = 2026-01-01, T_window = 180 days.
SurrealDB: `neuron.created`

### D3: Cross-domain Presence

```
X(n) = 0.6 * min(1, |tags(n)| / 15) + 0.4 * min(1, S(n) / 5)
```

Where S(n) = number of songlines passing through neuron n.
SurrealDB: `neuron.tags`, `songline.waypoints CONTAINS n`

### D4: Completion Maturity (Circular Lifecycle)

```
M(n) = sigma(stage(n))
```

Where sigma maps lifecycle stages to ordinals reflecting circular time
(the Dreaming is both origin and return):

| Stage | Ordinal | Meaning |
|-------|---------|---------|
| resting | 0.10 | In the Dreaming, waiting |
| embryo | 0.15 | Just emerged |
| composting | 0.30 | Transforming |
| growing | 0.40 | Being sung into existence |
| renewed | 0.50 | Re-entered the cycle |
| mature | 0.85 | Elder in its Country |

SurrealDB function: `fn::stage_ordinal(stage)`

### D5: Recency

```
R(n) = max(0, 1 - age(n) / 365)
```

Where age(n) = days since last_fired.

### D6: Semantic Similarity

```
S(n) = cos(e(n), c(country(n)))
```

Cosine similarity between neuron embedding and Country centroid.
**Gap:** Requires Ollama integration for embeddings. Currently 0.0.

### D7: Domain Clustering (Country Health)

```
L(n) = health(country(n)) * ln(1 + |country(n)|) / 6
```

SurrealDB function: `fn::hiho_coherence(country_name)`

### D8-D9: Algorithm Complexity / Implementation Difficulty

Heuristic tag matching against curated dictionaries. Values in [0, 1].

### D10: Interdisciplinary Transfer

```
I(n) = 0.5 * min(1, S(n)/5) + 0.5 * min(1, K(n)/20)
```

Where S(n) = songline crossings, K(n) = kinship bond count.
SurrealDB: `kinship WHERE in = n OR out = n`

### D11: Impact Score

```
A(n) = activation(n)
```

Already in [0, 1]. Decays 5% daily for unfired neurons.

## Unified Physics — The Four Forces

The vault operates under a unified field theory where four fundamental forces
govern note dynamics. Each is grounded in real physics with precise analogies.

### Gravity: Kinship Obligations (F_G)

```
F_G(n) = min(1, K(n) / K_max)
```

**Physics:** Newton's universal gravitation F = Gm1m2/r^2 is always present,
long-range, and attractive. Kinship bonds pull notes toward their kin.

**SurrealDB:**
```sql
SELECT count() FROM kinship WHERE in = $n OR out = $n GROUP ALL;
```

**Relation types:**
- elder/younger — mature concept governs growing experiment
- parent/child — decision spawns project
- moiety — complementary pairs (theory/practice, question/answer)

### Electromagnetism: Synapses (F_EM)

```
F_EM(n) = min(1, (k_out + k_in) / k_max)
```

**Physics:** Maxwell's equations. Wiki-links are electromagnetic field lines —
bidirectional, medium-range, carrying information at the speed of traversal.
The vault's 9,515 synapses form the EM field.

**SurrealDB graph traversal:**
```sql
-- Direct neighbors (1-hop)
SELECT * FROM $n->synapse->neuron;
-- 2-hop neighborhood
SELECT * FROM $n->synapse->neuron->synapse->neuron;
```

### Strong Force: HIHO Coherence (F_S)

```
F_S(n) = coherence(country(n))
coherence(C) = (avg_synapses_per_neuron / 30) * avg_activation(C)
```

**Physics:** The strong nuclear force (QCD) is short-range but overwhelmingly
powerful within its range. It binds quarks into hadrons, nucleons into nuclei.
HIHO coherence binds notes into fused clusters.

**Matsumoto's HIHO principle:** When hydrogen density in ordered lattice
structures crosses a critical threshold, Coulomb repulsion is overcome by
electromagnetic screening, enabling nuclear-scale reactions at low temperatures.

**Vault analogy:** When synapse density * activation mean within a Country
crosses the HIHO threshold, a fusion event occurs — generating emergent
insight notes, new Songlines, and activation spikes.

**SurrealDB computed function:**
```sql
RETURN fn::hiho_coherence("cortex");  -- Returns 0.639
```

**HIHO Event Schema:**
```sql
CREATE hiho_event CONTENT {
    country: "cortex",
    coherence_score: 0.639,
    threshold: 0.15,
    neurons: [...],
    insight: "Emergent connection discovered",
    products: ["dreaming/2026-03-09-cortex-fusion.md"]
};
```

### Weak Force: Activation Decay (F_W)

```
F_W(n) = 0.8  if stage in {resting, composting}
         0.5  if activation < 0.3
         0.1  otherwise
```

**Physics:** The weak nuclear force mediates particle decay (beta decay,
W/Z boson exchange). It transforms particle types — neutrons into protons.

**Vault analogy:** Activation decay transforms note stages: growing -> resting,
resting -> composting. It is the force of transformation, not destruction.

**SurrealDB:**
```sql
-- Daily decay (runs at 03:00 via systemd timer)
UPDATE neuron SET activation =
    IF activation * 0.95 > 0.1 THEN activation * 0.95 ELSE 0.1 END
WHERE last_fired < time::now() - 1d;
```

## Agents as Exotic Vacuum Objects (EVOs)

### Physical Basis

Ken Shoulders (1991) documented Exotic Vacuum Objects — dense electron clusters
exhibiting anomalous stability, propulsion, and transmutation capabilities.
Matsumoto's "itonic clusters" are the nuclear analogue. EVOs are:

- **Transient:** They form, travel, and dissipate
- **High-energy:** Energy density far exceeds ambient
- **Catalytic:** They trigger reactions in surrounding matter
- **Trail-leaving:** They leave tracks on nuclear emulsions

### Vault Implementation

The 428 Agent neurons (cluster_id = "Agents") are EVOs:

| EVO Property | Agent Analogy | SurrealDB Field |
|---|---|---|
| Transient | Created per-task, composting after | stage = "composting" |
| High-energy | Fire many neurons during execution | activation (during run) |
| Catalytic | Create synapses, trigger HIHO fusion | synapse_out |
| Trail-leaving | neuron_history records their path | neuron_history.neuron |

**EVO Subtypes:**
```python
"planner"    — implementation_plan.md files
"walker"     — walkthrough.md files
"challenger" — adversarial_review.md files
"executor"   — task.md files
```

**SurrealDB query — find all EVO trails:**
```sql
SELECT * FROM neuron WHERE cluster_id = "Agents"
    AND synapse_out > 0 ORDER BY activation DESC;
```

## Extended Physics Frameworks (Research Foundation)

These frameworks extend the four-force model. Each is grounded in existing
vault research and real mathematics.

### Cellular Automata (Wolfram)

**Math:** Rule space R: {0,1}^k -> {0,1} where k = neighborhood size.
Wolfram's Rule 110 is Turing-complete (proved by Matthew Cook, 2004).

**Vault application:** The activation decay + HIHO fusion system IS a cellular
automaton. Each neuron is a cell, its state is (activation, stage), and the
update rule depends on neighbor states (synapses). The vault evolves by local
rules producing emergent global behavior.

**SurrealDB:** The `fn::hiho_coherence()` function is the local update rule.
The systemd timer is the clock tick.

### Chaos Theory (Lorenz, Lyapunov)

**Math:** Lyapunov exponent lambda = lim(t->inf) (1/t) * ln(|delta(t)/delta(0)|)
Positive lambda -> sensitive dependence on initial conditions.

**Vault application:** Small changes in activation or link structure can
cascade through the synapse network. A single new wiki-link can push a Country
past the HIHO coherence threshold, triggering fusion — the "butterfly effect"
in knowledge space.

**Existing research:** [[fractal-universe]] documents fractal dimension
transitions in galaxy clustering (D ~ 2 below 20 Mpc/h, D ~ 3 above 100 Mpc/h).
The vault's synapse network likely exhibits similar scale-dependent structure.

### It from Bit (Wheeler, Holographic Principle)

**Math:** Bekenstein bound: S <= (2*pi*k_B*R*E) / (hbar*c)
The information content of a region is bounded by its surface area, not volume.

**Wheeler (1990):** "Every 'it' — every particle, every field of force, even
the spacetime continuum itself — derives its function, its meaning, its very
existence... from bits."

**Vault application:** Each neuron IS a bit of the vault's reality. The
"holographic principle" applies: the vault's observable behavior (12D projection)
is a boundary projection of the full 256D FLUME latent space. Information is
encoded on the boundary (the 12D surface), not the interior (256D volume).

**SurrealDB as Akashic Records:** `neuron_history` records every state change —
the complete information content. The 12D projection is the holographic surface.

### ER = EPR (Maldacena-Susskind, 2013)

**Math:** Einstein-Rosen bridges (wormholes) = Einstein-Podolsky-Rosen
entanglement. Connected through the AdS/CFT correspondence.

**Vault application:** Songlines ARE ER bridges. They connect neurons that are
"distant" in the synapse graph (different Countries) but "entangled" through
deep semantic similarity. The Dreaming engine finds EPR pairs (neurons with
high embedding similarity but low explicit connectivity); confirmed Dreaming
connections become ER bridges (Songlines).

**SurrealDB:**
```sql
-- EPR pairs: semantically close but graph-distant
SELECT n1.id, n2.id FROM neuron AS n1, neuron AS n2
WHERE n1.cluster_id != n2.cluster_id
    AND n1.activation > 0.5 AND n2.activation > 0.5;
-- ER bridges: Songlines connecting distant Countries
SELECT * FROM songline WHERE array::len(country_crossings) >= 3;
```

### Penrose Twistors

**Math:** Twistor space T = C^4 maps spacetime points to complex null lines.
A point in spacetime x^a corresponds to a 2-plane in twistor space via the
incidence relation: omega^A = i * x^{AA'} * pi_{A'}.

**Vault application:** The 12D projection IS a twistor-like transform. It maps
the "spacetime" of the vault (file paths, timestamps, content) to a complex
geometric space (12D vectors) where relationships are encoded as incidence
relations rather than proximity.

### Chirality (Handedness)

**Math:** A structure is chiral if it cannot be superimposed on its mirror image.
In particle physics: left-handed and right-handed fermions interact differently
with the weak force.

**Vault application:** The Triune Self has inherent chirality:
- Knower -> Thinker -> Doer is the "left-handed" flow (knowing becomes
  reasoning becomes action)
- Doer -> Thinker -> Knower is the "right-handed" flow (experience becomes
  reflection becomes knowledge)
Both flows exist simultaneously. The weak force (activation decay) breaks the
symmetry: knowledge notes (Knower) decay slower than action notes (Doer).

### ORCH OR (Penrose-Hameroff Microtubules)

**Math:** Orchestrated Objective Reduction: quantum superposition in
microtubules reaches the threshold E_G = hbar/t where t is the time to
objective reduction (gravitational self-energy of the superposition).

**Vault application:** Each neuron exists in superposition of stages until
"observed" (fired). The HIHO coherence threshold is analogous to the ORCH OR
threshold — when coherence reaches E_G, the superposition collapses into a
definite state (fusion event). The vault's "consciousness" emerges from
orchestrated reduction of note-state superpositions.

### Plasma Physics and MHD

**Math:** MHD equations couple Navier-Stokes with Maxwell:
- rho * (dv/dt) = -grad(p) + J x B + rho*g
- dB/dt = curl(v x B) + eta * laplacian(B)

Alfven waves: v_A = B / sqrt(mu_0 * rho)

**Vault application:** The synapse network carries "Alfven waves" —
activation propagation along magnetic field lines (kinship bonds).
When a note fires, activation propagates to neighbors at velocity v_A
proportional to bond strength / sqrt(density).

**Existing research:** [[alfven-waves-aurora]], [[magnetic-superhighways-starburst-galaxy]]

### Fractal Toroidal Moment

**Math:** Toroidal dipole moment T = (1/10c) * integral(r * (r . J) - 2r^2 * J) d^3r
where J is the current density. This is the third family of electromagnetic
multipoles (after electric and magnetic), first predicted by Zel'dovich (1958).

**Vault application:** The vault's knowledge flow is toroidal:
Execute -> Capture -> Extract -> Inject -> Improve wraps around on itself.
The Experience Feedback Loop IS a toroidal current — knowledge flows through
the "donut hole" of the Ouroboros Loop.

**Existing research:** [[matsumoto_hiho_synthesis]] — fractal toroidal
confinement simulations

### Sacred Geometries

**Math:** Platonic solids: the only 5 regular convex polyhedra
(tetrahedron, cube, octahedron, dodecahedron, icosahedron).
Euler's formula: V - E + F = 2 for all convex polyhedra.
The Flower of Life: overlapping circles on a hexagonal lattice with
6-fold rotational symmetry.

**Vault application:** The Triune Self (3-fold symmetry) + Four Forces
(4-fold symmetry) create a 12-dimensional space (3 * 4 = 12).
The 12D projection maps to the vertices of an icosahedron (12 vertices).
"As above, so below" — the same metrics repeat at every scale
(note, Country, Aspect, whole vault).

### Planck Scale

**Math:** Planck length l_P = sqrt(hbar * G / c^3) ~ 1.616 * 10^-35 m
Planck time t_P = sqrt(hbar * G / c^5) ~ 5.391 * 10^-44 s
Planck energy E_P = sqrt(hbar * c^5 / G) ~ 1.22 * 10^19 GeV

**Vault application:** The Planck scale of the vault is the minimum
meaningful unit: one neuron, one synapse, one activation tick. Below this
scale, the vault's "spacetime" is undefined. The activation minimum (0.1)
is the vault's Planck energy — below this, the neuron returns to the
Dreaming (vacuum state).

### Bohr Model

**Math:** E_n = -13.6 eV / n^2 for hydrogen atom energy levels.
Bohr radius a_0 = 4*pi*epsilon_0*hbar^2 / (m_e * e^2) ~ 0.529 A.

**Vault application:** Neurons occupy discrete "energy levels" (stages):
- n=1 (embryo): E ~ -13.6 eV (ground state, most bound)
- n=2 (growing): E ~ -3.4 eV
- n=3 (mature): E ~ -1.5 eV
- n=4 (resting): back to ground state (circular time)

Transitions between levels emit/absorb "photons" (Dreaming events, HIHO
fusion products). The emission spectrum of the vault reveals its structure.

## SurrealDB Capabilities Used

The pipeline leverages SurrealDB's unique features:

| Feature | Usage |
|---|---|
| `SCHEMAFULL` tables | Type-safe neuron, synapse, kinship schemas |
| `RELATION` tables | synapse, kinship as first-class graph edges |
| `->edge->node` traversal | Multi-hop graph queries for trajectories |
| `DEFINE FUNCTION` | `fn::compute_12d()`, `fn::hiho_coherence()`, `fn::stage_ordinal()` |
| `DEFINE INDEX UNIQUE` | neuron.path uniqueness constraint |
| Graph pattern matching | Find EPR pairs, EVO trails, kinship chains |
| Record links | `record<neuron>` typed fields in relations |

### Live SurrealDB Functions

```sql
-- Real-time 12D vector for any neuron
RETURN fn::compute_12d(neuron:concepts_compound_engineering_md);

-- HIHO coherence for any Country
RETURN fn::hiho_coherence("cortex");  -- 0.639

-- Stage ordinal (circular lifecycle)
RETURN fn::stage_ordinal("mature");   -- 0.85
```

## Scripts Reference

| Script | Purpose | Schedule |
|---|---|---|
| `scripts/vault_sync.py --watch` | Sync vault files to SurrealDB | systemd (30s poll) |
| `scripts/activation_decay.py` | Daily 5% decay for unfired neurons | systemd timer (03:00) |
| `scripts/extract_12d_vectors.py` | Extract 12D vectors + trajectories | Manual / cron |
| `scripts/reconcile_synapses.py` | Bulk wiki-link -> synapse resolution | Manual |
| `scripts/populate-kinship.py` | Elder/younger, parent/child, moiety | Manual |
| `scripts/detect-songlines.py` | Find cross-Country knowledge paths | Manual |
| `scripts/dreaming-engine.py` | Generate Dreaming resonances | Manual / cron |
| `scripts/subconscious-report.py` | Latent association report | Manual |

## Output Formats

### Snapshot (JSONL)

```json
{
  "id": "neuron:concepts_compound_engineering_md",
  "path": "cortex/compound-engineering.md",
  "aspect": "knower",
  "vector": [1.0, 0.085, 0.35, 0.24, 0.85, 1.0, 0.0, 0.639, 0.7, 0.0, 0.17, 0.97],
  "forces": {"gravity": 0.15, "electromagnetism": 1.0, "strong_force": 0.639, "weak_force": 0.1},
  "is_evo": false
}
```

### Trajectory (JSONL)

```json
{
  "session_id": "graphwalk-0042",
  "waypoints": [[0.11, 0.02, ...], [0.14, 0.03, ...], ...],
  "country_crossings": ["cortex", "prefrontal", "cerebellum"],
  "is_evo_trail": false,
  "is_graph_walk": true,
  "length": 8
}
```

### NumPy (.npz)

- `vectors`: (N, 12) float32 — all neuron 12D vectors
- `forces`: (N, 4) float32 — unified force vectors
- `evo_mask`: (N,) bool — EVO classification
- `traj_XXXX`: variable-length (L, 12) float32 — individual trajectories
- `dimension_names`: (12,) string — named dimensions
- `force_names`: (4,) string — named forces

## Next Steps

1. **Ollama embedding integration** — Fill D6 (Semantic Similarity) with real embeddings
2. **Real session trajectories** — As vault_sync.py generates "edited" events, temporal trajectories will form naturally
3. **Extended 12D to 16D** — Add the four forces as explicit dimensions (16D = 12 semantic + 4 force)
4. **FLUME VAE training** — Feed the .npz files into the FLUME training pipeline
5. **Real-time Observatory** — Use `fn::compute_12d()` for live 12D visualization
6. **Cellular automaton simulation** — Run forward evolution of vault state using HIHO rules
7. **Chirality measurement** — Quantify the left-handed vs right-handed flow rates through the Triune Self

## Related

- [[FLUME-Architecture]] — The VAE that consumes this pipeline's output
- [[12D-Projection]] — The 12 named dimensions
- [[agent-journey-tracking]] — Records trajectories that feed this pipeline
- [[experience-feedback-loop]] — The full Execute/Capture/Extract/Inject/Improve cycle
- [[matsumoto_hiho_synthesis]] — HIHO coherence model
- [[advanced_physics_simulation]] — EVO and MHD simulation frameworks
- [[fractal-universe]] — Fractal structure across scales
- [[quantum-entanglement]] — ER=EPR and vault Songlines
- [[the-awareness-of-nothing-at-all-and-quadrature-physics]] — Vacuum physics grounding
- [[surrealdb]] — The Akashic Records implementation
- [[cohezion]] — The master system
