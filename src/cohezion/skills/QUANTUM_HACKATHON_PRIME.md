---
name: quantum-hackathon-prime
description: "Expertise in quantum hackathon execution, specifically targeting 'Peaked Circuit' challenges on cloud providers like BlueQubit. Specialized in bypassing simulator limits via statistical refinement, managing real quantum hardware execution (Rigetti/IonQ), and navigating the nuanced resource constraints of cloud-quantum tiers."
---

# SKILL: QUANTUM_HACKATHON_PRIME

## DOMAIN EXPERTISE
Expertise in quantum hackathon execution, specifically targeting 'Peaked Circuit' challenges on cloud providers like BlueQubit. Specialized in bypassing simulator limits via statistical refinement, managing real quantum hardware execution (Rigetti/IonQ), and navigating the nuanced resource constraints of cloud-quantum tiers.

## KEY TEXTS & CONCEPTS
- **Endianness Truth Anchor:** Using a 2-qubit Bell state to definitively verify LSB vs MSB before processing large datasets.
- **Transpilation Layout Inversion:** Tracking `initial_layout` from Qiskit transpilation and applying the inverse permutation to hardware counts to recover logical bitstrings.
- **Plan-Credit Distinction:** Distinguishing between 'Account Credits' (payment balance) and 'Plan Type' (resource limits like max bond dimension).
- **Bootstrap Majority Voting:** Statistical refinement to extract global maximums from noisy, low-fidelity samples.

## INSTRUCTION

### 1. Establish the Endianness Truth Anchor
Never trust documentation or assumptions about bitstring order (LSB/MSB). Run a trivial 2-qubit circuit first.
```python
import qiskit
qc = qiskit.QuantumCircuit(2)
qc.x(1) # Set q1 to 1
qc.measure_all()
# Result '10' == MSB (q1, q0)
# Result '01' == LSB (q0, q1)
```

### 2. Track and Invert Transpilation Layout
When transpiling for hardware (e.g., to stay under gate limits), logical qubits are re-mapped. You MUST capture this mapping.
```python
from qiskit import transpile
optimized = transpile(circuit, backend, optimization_level=3)
# Capture logical-to-physical mapping
layout = optimized.layout.initial_layout
# Post-processing: Apply inverse mapping to hardware bitstrings
# to translate physical measurements back to logical problem space.
```

### 3. Verify Resource Plan vs Balance
Check that the account PLAN allows the requested resources (e.g., GPU, high bond dimension) before submitting, even if credits are available.
```python
# Protocol: Run a 1-shot test on the target device/settings.
# If it fails with NOT_ENOUGH_FUNDS despite balance, the PLAN is restricted.
bq.run(circuit, device='mps.gpu', shots=1, options={'mps_bond_dimension': 512})
```

## VERSION
v1.0

## SEE ALSO
- BITSTRING_ENDIANNESS_PRIME
- QISKIT_TRANSPILATION_PRIME
- STATISTICAL_REFINEMENT_PRIME
