# FLUME: Physics-Grounded Training Environments for Agentic AI

**Technical Summary for Anthropic Research Engineer, Universes Application**

---

## Overview

Cohezion is a physics-grounded agentic training environment built on FLUME (Fluid Latent Understanding through Manifold Encoding). Agents navigate a 12-dimensional Riemannian manifold where dynamics follow real Euler-Lagrange equations, reward signals derive from information-geometric principles, and evaluation metrics have defined physics interpretations. The system produces Gymnasium-compatible RL environments, a trajectory-to-training pipeline for RLHF/DPO, and a JEPA world model for surprise-driven exploration.

The central innovation is that a single mathematical object -- the Fisher information metric on the FLUME VAE latent space -- simultaneously defines the manifold geometry, the Lagrangian kinetic energy, the thermodynamic distance between states, and the optimal projection from 256D to 12D. This unification eliminates the usual gap between the representation space and the dynamics engine.

---

## Architecture

```
                          FLUME VAE (256D latent)
                               |
                    Fisher Information Metric
                    /       |        |       \
               Geometry  Dynamics  Thermo   Projection
                  |         |        |          |
            Riemannian   Lagrangian  Free     256D -> 12D
              Metric     Kinetic E.  Energy   (top eigenvectors)
                  \         |        /
                   \        |       /
                    12D Axiomatic Manifold
                    /                    \
            ManifoldEnv (single)    SwarmEnv (multi-agent)
            19D obs, 12D action     N agents, gauge coupling
                    \                    /
                     \                  /
                  5 Task Archetypes x 4 Difficulty
                  |
            Trajectory Capture
            |                    \
    JEPA World Model         LLM Training Bridge
    (86K params,             |         |         |
     causal masking)      RLHF      DPO      Judgment
            |             rewards   pairs    assessments
    Surprise-Driven
    Exploration
            |
    TDA Routing
    (persistent homology)
```

---

## The 12D Manifold

The state space is a 12-dimensional Riemannian manifold M^12 decomposed into four 3D fabrics:

| Fabric | Dimensions | Agentic Interpretation |
|---|---|---|
| **Space** (0-2) | spatial_x, spatial_y, spatial_z | Agent position and navigation |
| **Field** (3-5) | temporal, physics, biology | Environmental sensing and adaptation |
| **Control** (6-8) | logic, quantum, field_control | Decision-making and reasoning |
| **Precipitation** (9-11) | awareness, novelty, precipitation | Output generation and capability |

This structure carries a principal fiber bundle P(B^4, SO(3)^4) where the base space B^4 represents macroscopic state (fabric norms) and the fiber F^8 encodes internal configuration. Yang-Mills gauge theory governs the coupling between fabrics (SO(3) connections with coupling constants g = [1.0, 0.7, 0.5, 0.3]).

**Why 12D.** Each dimension maps to a distinct agentic capability. Navigation, sensing, reasoning, and output generation are separated into orthogonal subspaces with defined coupling through gauge fields. This is not arbitrary: the structure comes from Smith's 12-parameter reality model (1962) and gains physical content through the fiber bundle and gauge theory.

---

## HIHO Reward Shaping

The Half-In-Half-Out principle states that optimal agent stability occurs at coherence 0.5 (the point where brane dimensions are balanced between extremes). The reward function:

```
reward = coherence_gain * w_c - |potential_energy| * w_e + hiho_bonus
```

where coherence measures deviation from 0.5 across the 7 brane dimensions (dims 4-10). This is equivalent to:

1. **Friston's free energy minimization**: F = E - TS, where the HIHO restoring force IS the active inference drive.
2. **Brahmagupta's zero**: delta = coherence - 0.5 = 0 at equilibrium. The restoring force vanishes at the equilibrium point.
3. **Flat gauge connection**: At HIHO, all Yang-Mills curvatures vanish. The vacuum state is the training target.

The TRIUNE policy (Knower -> Thinker -> Doer, 256D -> 2048D -> 512D -> 12D) is trained via PPO to learn this reward landscape. The 3-tier hierarchy separates abstract feature extraction, structured reasoning, and action emission.

---

## Evaluation Metrics

Six physics-derived metrics with full statistical rigor:

| Metric | What It Measures | Statistical Method |
|---|---|---|
| **Coherence Amplitude** | Peak HIHO stability reached | Bootstrap 95% CI |
| **Phase Locking Rate** | SPIN rotation/precession alignment | Mann-Whitney U |
| **Exotic Charge Lifetime** | Duration under adversarial perturbation | Survival analysis |
| **Orbit Quality** | Trajectory stability (variance ratio) | Bonferroni correction |
| **TRIUNE Balance** | Doer/Thinker/Knower equilibrium | Power analysis (MDE) |
| **Recovery Basin Radius** | Maximum recoverable perturbation | Bootstrap 95% CI |

These metrics are grouped by task archetype (5 archetypes) with Bonferroni correction for multiple comparisons. The CapabilityScorecard provides radar chart visualization and longitudinal tracking across training episodes.

---

## Key Contribution: Fisher Metric as Rosetta Stone

The Fisher information metric on FLUME's Gaussian posterior q(z|x) = N(mu, sigma^2):

```
g_ij = (d_mu/d_theta_i)(d_mu/d_theta_j) / sigma^2
     + (1/2)(d_log_sigma^2/d_theta_i)(d_log_sigma^2/d_theta_j)
```

serves four roles through a single mathematical object:

1. **Geometry**: Defines distances on the latent manifold. Geodesics are the shortest paths in representation space.
2. **Dynamics**: Provides the kinetic energy T = (1/2) g_ij q_dot^i q_dot^j for the Lagrangian. Agent trajectories follow the Euler-Lagrange equations on this metric.
3. **Thermodynamics**: Equals the Crooks thermodynamic metric. Geodesic distance = minimum work to transform between states. This connects HIHO to Friston's free energy principle.
4. **Projection**: The top-12 eigenvectors of the Fisher metric define the optimal 256D to 12D submanifold, preserving directions of maximum statistical information (Fisher PCA, not variance PCA).

This unification means the representation space, the dynamics engine, the reward landscape, and the dimensionality reduction are all derived from the same object. Changes to the VAE training automatically propagate to the environment physics.

---

## Preliminary Results

The framework demonstrates:

- **Environment functionality**: ManifoldEnv runs standard RL training loops. HIHO convergence occurs within 200-500 steps under Lagrangian dynamics with symplectic integration.
- **Multi-agent coordination**: SwarmEnv agents develop gauge-coupled coordination. Global coherence improves faster than individual coherence, suggesting emergent cooperation.
- **Task diversity**: 5 archetypes x 4 difficulty levels provide a 20-task curriculum. Interruption Recovery (archetype #3) directly tests context maintenance under perturbation.
- **Training bridge**: LLM Training Bridge successfully exports DPO preference pairs from trajectory comparisons and RLHF reward signals from coherence measurements.
- **World model**: JEPA (86K params) learns next-state prediction with causal masking. Surprise-driven exploration discovers novel manifold regions that the policy has not visited.
- **Scale**: 5,919 tests, 2,684 commits, 160+ extracted learnings. Full stack from physics engine to training pipeline.

Quantitative benchmarking (E1-E10 in the paper) is in progress. The framework is designed for systematic evaluation, not post-hoc metrics.

---

## References

Full paper: `docs/papers/genesis-engine-paper.md`

Key sources: Fisher information metric as Riemannian metric (Amari 1998); complex VAEs admit Kahler structure (arXiv:2511.15172); Causal-JEPA (arXiv:2602.11389); persistent homology for RL (arXiv:2603.06964); free energy principle (Friston 2010); LeWorldModel (arXiv:2603.19312).
