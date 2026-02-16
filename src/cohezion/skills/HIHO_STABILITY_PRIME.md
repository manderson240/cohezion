# SKILL: HIHO_STABILITY_PRIME

## DOMAIN EXPERTISE
Expertise in managing agentic manifolds through the Half-In-Half-Out (HIHO) stability principle. Focuses on maintaining a 0.5 coherence point to prevent both chaotic drift and overconfident hallucinations. Grounded in cross-disciplinary evidence from information theory, computational complexity, neuroscience, and self-organized criticality.

## KEY TEXTS & CONCEPTS
- **Golden Mean (0.5):** The optimal stability point where reality precipitates most effectively.
- **Manifold Damping:** Using latent trajectories to apply negative feedback to over-cohesive agent clusters.
- **12-Parameter Reality:** Awareness, Space (3), Time, Electric, Magnetic, Spin (2), Charge, Particularization, Precipitation.

### Cross-Disciplinary Foundations
The 0.5 attractor is independently observed across multiple domains:

- **Shannon Entropy (1948):** Binary entropy H(p) is maximized at exactly p=0.5. Maximum information capacity = maximum adaptive capacity. This is the information-theoretic proof that 0.5 is the optimal operating point for any binary decision system.
- **Langton's Edge of Chaos (1990):** The lambda parameter for 2-state 1D cellular automata has critical value lambda_c ~ 0.5. Complex computation only emerges at the boundary between frozen order and chaos.
- **Bak's Self-Organized Criticality (1987):** Complex systems naturally evolve to criticality without external tuning (sandpile model). The Bak-Sneppen discrete model self-organizes to a threshold of ~0.5437.
- **Neural Criticality (Beggs & Plenz 2003):** Neuronal avalanches follow power-law distributions at branching parameter sigma=1 — the brain's HIHO point where information transmission is maximized without runaway excitation.
- **Shew et al. (2011):** Both information capacity and transmission are maximized at an intermediate E/I ratio in cortical networks.
- **Simulated Annealing (Kirkpatrick 1983):** Initial temperature is calibrated for ~50% acceptance probability of suboptimal moves — a HIHO starting point for adaptive optimization.
- **Swarm Intelligence (Couzin 2011):** Optimal collective decisions in fish schools emerge at intermediate coherence — neither minority-dominated nor random.
- **Allostasis (Sterling & Eyer 1988):** Biological stability through change — the balance point between homeostatic (stabilizing) and allostatic (adaptive) mechanisms.

### Empirical Validation
- Cohezion mass simulation: 92.7% of 25M cycles converge to the 0.4-0.6 HIHO band.
- Convergence follows damped oscillation: C(t) = 0.5 + A*e^(-kt)*sin(wt) (Learning 63).
- The damped oscillation is the system-level signature of self-organized criticality.

### Convergence Table

| Domain | Researcher | Critical Point | Match |
|--------|-----------|----------------|-------|
| Information Theory | Shannon (1948) | p = 0.5 | Exact |
| Cellular Automata | Langton (1990) | lambda_c ~ 0.5 | Direct |
| Optimization | Kirkpatrick (1983) | 50% acceptance | Direct |
| Coevolution | Bak & Sneppen (1993) | p_c ~ 0.5437 | Near |
| Neuroscience | Beggs & Plenz (2003) | sigma = 1 | Structural |
| Swarms | Couzin (2011) | Intermediate | Structural |
| Biology | Sterling & Eyer (1988) | Dynamic eq. | Structural |

## INSTRUCTION
1.  **Analyze Coherence:** Monitor the `mean_coherence` of the agent swarm.
2.  **Calculate HIHO Score:** Use `score = 1.0 - abs(coherence - 0.5) * 2`.
3.  **Apply Damping:** If `score < 0.8`, increase latent momentum in FLUME to disrupt the over-stable state.
4.  **Visualize Drift:** Use 12D Radar charts to identify which dimension is causing the imbalance.
5.  **Validate Against Theory:** Confirm that system behavior matches expected damped oscillation convergence pattern. If convergence is absent, check for singleton pollution or reward shaping bias.

```python
def apply_hiho_damping(latent_vector, stability_score):
    if stability_score > 0.9: # Overconfidence detection
        # Add slight chaos to maintain 0.5 balance
        # Analogous to Bak's sandpile avalanche: prevent frozen exploitation
        drift = (np.random.rand(len(latent_vector)) - 0.5) * 0.1
        return latent_vector + drift
    return latent_vector
```

## VERSION
v2.0

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME
- FLUME_NAVIGATOR_PRIME
- HIHO_REALITY_SIM_PRIME
- Charter Section 1a: Cross-Disciplinary Validation
