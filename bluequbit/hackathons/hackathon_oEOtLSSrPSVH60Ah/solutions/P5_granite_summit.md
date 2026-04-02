# Solution: P5_granite_summit

## Challenge
Granite Summit 🏔️

## Answer
```
01000010100011110101010111101000010101010010
```

## Method

### Circuit Analysis
- **Qubits:** 44
- **Gates:** ~2,900
- **Type:** Heavy hex peaked circuit

### Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

with open('P5_granite_summit.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# 44 qubits requires reduced bond dimension on free tier
result = bq.run(qc, 
    device='mps.cpu',
    shots=100000,
    options={'mps_bond_dimension': 32}
)
counts = result.get_counts()

raw = max(counts, key=counts.get)
answer = raw[::-1]  # REVERSE for submission
```

### Results
- **Total shots:** 100,000
- **Best bitstring (reversed):** `01000010100011110101010111101000010101010010`
- **Status:** ✅ Complete

## Submission Text
Ran circuit on BlueQubit mps.cpu with 100k shots using bond_dim=32 for 44 qubits. Bitstring '01000010100011110101010111101000010101010010' (reversed from raw measurement) had highest probability count. Heavy hex peaked circuit characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method. Note: Required smaller bond_dim=32 for 44 qubits on free tier.

## Submission
**Answer:** `01000010100011110101010111101000010101010010`

## Files Used
- Circuit: `../problems/P5_granite_summit.qasm`
- **Skill:** [`heavy-output-peaked-circuits`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md)

## Verification
✅ Ready to submit (2026-04-02)
