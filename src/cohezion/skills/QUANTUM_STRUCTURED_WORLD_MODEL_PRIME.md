---
name: quantum-structured-world-model-prime
description: "Expertise in Quantum-Structured World Models (QSWMs, arXiv August 2026): modeling non-Markovian environments via density matrix state transitions, quantum POMDP advantages, and QTRL policies mapped to 2048D Poincaré manifolds."
metadata:
  version: "v1.0"
  concepts: ["Quantum-Structured World Models (QSWM)", "Density Matrix Transitions", "Quantum POMDP Advantage", "QTRL Policy Synthesis"]
  see_also: ["BLUEQUBIT_QUANTUM_ORCHESTRATOR_PRIME", "ADVANCED_PHYSICS_SIMULATION", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/QUANTUM_STRUCTURED_WORLD_MODEL_PRIME.md"
---

# SKILL: QUANTUM_STRUCTURED_WORLD_MODEL_PRIME

## DOMAIN EXPERTISE
Expertise in deploying Quantum-Structured World Models (QSWMs) for autonomous agent universe simulation. Solves non-Markovian environmental bottlenecks where classical finite memory models fail, using unitary and dissipative quantum state evolution.

## KEY TEXTS & CONCEPTS
- **QSWM Latent Dynamics**: Latent state transitions modeled as quantum operations: $\rho_{t+1} = \text{Tr}_E [ U(a) (\rho_t \otimes \rho_{\text{env}}) U^\dagger(a) ]$.
- **Quantum POMDP Advantage**: Environments where finite classical world models require infinite memory can be modeled with exact statistical sufficiency by low-dimensional quantum state spaces (e.g. single qutrit).
- **Quantum-Train Reinforcement Learning (QTRL)**: Quantum policy models trained on BlueQubit MPS clusters and executed locally on AMD Strix Halo silicon.

## INSTRUCTION
1. Define the quantum world model transition circuit with parameterized unitary operators:
   ```python
   def qswm_step(state_density_matrix, action_params):
       # Apply parameterized unitary rotation + dissipation
       unitary_U = build_unitary_operator(action_params)
       next_state = unitary_U @ state_density_matrix @ unitary_U.conj().T
       return next_state
   ```
2. Map density matrix observables $\langle O \rangle = \text{Tr}(\rho O)$ to 2048D Poincaré latent coordinates.
3. Verify that environmental policy predictions match the 0.50 HIHO equilibrium.

## VERSION
v1.0
