# Solution: P4_golden_mountain

## Challenge
Golden Mountain 🏔️

## Answer
```
110001000000111101101011011000000110110001111010
```

## Method

### Circuit Analysis
- **Qubits:** 48
- **Gates:** ~15,300
- **Type:** Large peaked circuit

### Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

with open('P4_golden_mountain.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# 48 qubits requires small bond dimension on free tier
result = bq.run(qc, 
    device='mps.cpu',
    shots=100000,
    options={'mps_bond_dimension': 16}
)
counts = result.get_counts()

raw = max(counts, key=counts.get)
answer = raw[::-1]  # REVERSE for submission
```

### Results
- **Total shots:** 100,000
- **Best bitstring (reversed):** `110001000000111101101011011000000110110001111010`

## Submission Text
Ran circuit on BlueQubit mps.cpu with 100k shots using bond_dim=16 for 48 qubits. Bitstring '110001000000111101101011011000000110110001111010' (reversed from raw measurement) had highest probability. Large peaked circuit characterized using heavy output detection method. Note: Required small bond_dim=16 for 48 qubits on free tier.

## Files Used
- Circuit: `../problems/P4_golden_mountain.qasm`
- **Skill:** [`quantum-heavy-output-detection`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md)

## Verification
✅ COMPLETE (2026-04-02)
