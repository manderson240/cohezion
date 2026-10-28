---
name: ventral-hippocampus-circuits-prime
description: "Expert in ventral hippocampus (vHPC) affective-motivational mapping, projection routing across BLA, mPFC, NAc, and Hypothalamus, approach-avoidance conflict arbitration, and latent state inference based on Biane et al. (2026)."
---

# SKILL: VENTRAL_HIPPOCAMPUS_CIRCUITS_PRIME

## DOMAIN EXPERTISE
Expert in biological and computational ventral hippocampal circuitry based on Biane, Wagner-Carena & Kheirbek (Nature Reviews Neuroscience, 2026). Contrasts dorsal hippocampal (dHPC) high-resolution Euclidean spatial mapping with ventral hippocampal (vHPC) low-dimensional affective-motivational manifold representations. Specializes in multi-channel projection gating across the basolateral amygdala (BLA), medial prefrontal cortex (mPFC), nucleus accumbens (NAc), and hypothalamus (LH/PVN) to arbitrate approach-avoidance conflicts, compute latent state inferences, modulate agentic exploration vigor, and enforce formal verification safety gates with zero latency.

## KEY TEXTS & CONCEPTS
* **Foundational Reference**: Biane, J.S., Wagner-Carena, J. & Kheirbek, M.A. (2026). "The ventral hippocampus: computations, circuits and functions." *Nature Reviews Neuroscience*, doi:10.1038/s41583-026-01078-6.
* **Longitudinal Gradient**: dHPC maps spatial metric coordinates $\mathbf{v}_{dHPC} = W_{grid} \mathbf{s}_{spatial}$, while vHPC compresses external contexts with interoceptive signals into an affective-motivational manifold $\mathbf{v}_{vHPC} = \tanh(W_{aff} [\mathbf{s}_{spatial}; \mathbf{h}_{intero}])$.
* **Parallel Projection Channels**:
  - **BLA (Basolateral Amygdala)**: Valence assignment, associative plasticity, signed error propagation ($|c|$), fear conditioning.
  - **mPFC (Medial Prefrontal Cortex)**: Contextual cognitive control, conflict arbitration ($\sigma(2|c|)$), task rule switching, policy priors.
  - **NAc (Nucleus Accumbens)**: Incentive salience, reward expectation, exploratory dispatch vigor ($g \cdot (1 - 0.4 U_t)$).
  - **Hypothalamus (LH/PVN)**: Autonomic arousal, metabolic homeostasis, resource throttling ($(1 - g) + 0.4 U_t$).
* **Approach-Avoidance Conflict**: Signal $c = V_{app} - V_{avoid}$ passed through logistic sigmoid $g = \sigma(\kappa c)$ where $\kappa$ governs conflict sensitivity.
* **Latent State Inference**: Maintains hierarchical Bayesian belief distribution $b_t(z)$ over hidden task contexts $z$, computing Shannon entropy uncertainty $U_t = \mathbb{H}[b_t]$ to dynamically steer agentic execution.

## INSTRUCTION

### 1. Fusing Spatial State and Interoceptive State into Manifold
Combine external task/spatial features with internal resource pressure and error frequency:

```python
from cohezion.neuro.ventral_hippocampus import VentralHippocampusCircuit

circuit = VentralHippocampusCircuit(spatial_dim=12, conflict_sensitivity=2.0)
affective_vec = circuit.compute_affective_vector(
    spatial_coordinates=[0.5] * 12,
    interoceptive_energy=0.85,
    interoceptive_stress=0.15,
)
```

### 2. Inferring Latent Context via Bayesian Update
Update beliefs over hidden task environments (`SAFE_EXPLOIT`, `AMBIGUOUS_CONFLICT`, `HIGH_THREAT_RISK`) and compute uncertainty entropy:

```python
observation_evidence = {
    "SAFE_EXPLOIT": 0.1,
    "AMBIGUOUS_CONFLICT": 0.8,
    "HIGH_THREAT_RISK": 0.1,
}
posterior, entropy = circuit.infer_latent_context(observation_evidence)
```

### 3. Arbitrating Approach-Avoidance and Gating Downstream Targets
Determine the agent behavioral regime and output pathway weights:

```python
mode, targets, conflict = circuit.arbitrate_approach_avoidance(
    reward_expectation=0.8,
    threat_risk=0.2,
    uncertainty_entropy=entropy,
)

# Modes: MOTIVATED_EXPLORATION, DEFENSIVE_CONSOLIDATION, MPFC_ARBITRATION, SAFE_AVOIDANCE
if mode == "defensive_consolidation":
    # Enforce AutoHarness ZKFV formal verification & rollback guardrails
    pass
elif mode == "motivated_exploration":
    # Dispatch proactive Tier-1/Tier-2 autonomous exploration
    pass
```

### 4. Persisting Circuit State to SurrealDB
Record the vHPC hub node and projection synapses into the knowledge mesh:

```python
state = circuit.process_step(
    spatial_coordinates=[0.2] * 12,
    reward_expectation=0.7,
    threat_risk=0.3,
)
counts = await circuit.persist_circuit_state(state, step_id="cycle_431")
```

## VERSION
v0.1

## SEE ALSO
- `FASTFLOWLM_PRIME.md` (FastFlowLM NPU execution on AMD XDNA2)
- `DROSOPHILA_CNS_CONNECTOME_PRIME.md` (Sensorimotor reflex arcs and connectome topologies)
- `JOURNEY_TRACKING_PRIME.md` (12D state vector manifold navigation)
