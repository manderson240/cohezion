---
name: bluequbit-quantum-orchestrator-prime
description: "Expertise in orchestrating 34+ qubit quantum circuit simulations, Matrix Product State (MPS) tensor network contractions, and QPU job execution via BlueQubit and local backends with strict zero-credential-leakage security."
metadata:
  version: "v1.0"
  concepts: ["Matrix Product State (MPS)", "Clifford+T Decomposition", "QPU Quantum Annealing", "Poincaré State Invariants"]
  see_also: ["ADVANCED_PHYSICS_SIMULATION", "SHEAF_COHOMOLOGY_ARC_PRIME"]
  source: "src/cohezion/skills/BLUEQUBIT_QUANTUM_ORCHESTRATOR_PRIME.md"
---

# SKILL: BLUEQUBIT_QUANTUM_ORCHESTRATOR_PRIME

## DOMAIN EXPERTISE
Expertise in orchestrating large-scale quantum circuit simulation (up to 34+ qubits), tensor network contractions, and hybrid classical-quantum algorithms using BlueQubit SDK and local fallback simulators without credential exposure.

## KEY TEXTS & CONCEPTS
- **Matrix Product States (MPS)**: 1D tensor networks allowing efficient simulation of weakly entangled states with bond dimension $\chi \in [64, 256]$.
- **Statevector & Clifford+T**: Exact unitary simulation for $N \le 30$ qubits and deterministic stabilizer Clifford gates.
- **Quantum-Hyperbolic Mapping**: Projecting quantum state density matrices $\rho$ to 2048D Poincaré coordinates via Bures distance metrics.
- **Strict Credential Isolation**: All authentication tokens (`BQ_API_TOKEN`, `BLUEQUBIT_API_KEY`) loaded via secure environment variables and never logged or printed.

## INSTRUCTION
1. Initialize the quantum execution context using environment variables:
   ```python
   import os
   # Zero-leakage credential initialization
   api_token = os.environ.get("BLUEQUBIT_API_KEY", "")
   ```
2. Build quantum circuits with Qiskit / Cirq and dispatch to MPS or statevector backends:
   ```python
   from bluequbit import init
   bq_client = init(token=api_token) if api_token else None
   ```
3. Extract expectation values $\langle \psi | \hat{O} | \psi \rangle$ and map into 2048D Poincaré manifold trajectories.

## VERSION
v1.0
