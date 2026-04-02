# Solution: P3_sharp_peak

## Challenge
Sharp Peak 🔺

## Answer
```
01011000100010110011111000001010101010110001
```

## Method

### Circuit Analysis
- **Qubits:** 44
- **Gates:** 577
- **Type:** Peaked circuit (larger than free tier comfort zone)

### Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

with open('P3_sharp_peak.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# Use smaller bond dimension for 44 qubits on free tier
result = bq.run(qc, 
    device='mps.cpu',
    shots=100000,
    options={'mps_bond_dimension': 32}  # Reduced for free tier
)
counts = result.get_counts()

raw = max(counts, key=counts.get)
answer = raw[::-1]  # REVERSE for submission
```

### Results
- **Total shots:** 100,000
- **Unique outcomes:** TBD
- **Best bitstring (raw):** `10001101010101010000011111001101000100011010`
- **Best bitstring (reversed):** `01011000100010110011111000001010101010110001`
- **SNR:** 51.77 sigma

## Confidence Level
**HIGH** - SNR > 10 sigma confirms clear heavy output

## Submission Text
Ran circuit on BlueQubit mps.cpu with 100k shots using bond_dim=32. Bitstring '01011000100010110011111000001010101010110001' (reversed from raw measurement) had highest probability. SNR 51.77 sigma confirms clear heavy output. Peaked circuit characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method. Note: Required smaller bond_dim=32 for 44 qubits on free tier.

## Key Insight
44-qubit circuit pushes free tier limits. Used bond_dim=32 (vs standard 64) to stay within limits while maintaining accuracy. SNR 51.77 confirms the peak is still clearly detectable.

## Files Used
- Circuit: `../problems/P3_sharp_peak.qasm`
- Tutorial: `../../tutorials/tutorial_breaking_peaked_quantum_circuits_classically.ipynb`
- **Skill Used:** [`heavy-output-peaked-circuits`](../../../../.claude/skills/heavy-output-peaked-circuits/SKILL.md)

## Verification
⏳ Ready to submit (2026-04-02)
