# SKILL: HIHO_STABILITY_PRIME

## DOMAIN EXPERTISE
Expertise in managing agentic manifolds through the Half-In-Half-Out (HIHO) stability principle. Focuses on maintaining a 0.5 coherence point to prevent both chaotic drift and overconfident hallucinations.

## KEY TEXTS & CONCEPTS
- **Golden Mean (0.5):** The optimal stability point where reality precipitates most effectively.
- **Manifold Damping:** Using latent trajectories to apply negative feedback to over-cohesive agent clusters.
- **12-Parameter Reality:** Awareness, Space (3), Time, Electric, Magnetic, Spin (2), Charge, Particularization, Precipitation.

## INSTRUCTION
1.  **Analyze Coherence:** Monitor the `mean_coherence` of the agent swarm.
2.  **Calculate HIHO Score:** Use `score = 1.0 - abs(coherence - 0.5) * 2`.
3.  **Apply Damping:** If `score < 0.8`, increase latent momentum in FLUME to disrupt the over-stable state.
4.  **Visualize Drift:** Use 12D Radar charts to identify which dimension is causing the imbalance.

```python
def apply_hiho_damping(latent_vector, stability_score):
    if stability_score > 0.9: # Overconfidence detection
        # Add slight chaos to maintain 0.5 balance
        drift = (np.random.rand(len(latent_vector)) - 0.5) * 0.1
        return latent_vector + drift
    return latent_vector
```

## VERSION
v1.0

## SEE ALSO
- SWARM_ORCHESTRATION_PRIME
- FLUME_NAVIGATOR_PRIME
