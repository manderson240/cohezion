# Solution: P1_little_peak

## Challenge
Little Peak 🌱

## Answer
```
1001
```

## Method

### Circuit Analysis
- **Qubits:** 4
- **Gates:** 6 (X, RY rotations)
- **Type:** Peaked circuit with heavy output

### Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

# Load circuit
with open('P1_little_peak.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# Run on free tier
result = bq.run(qc, 
    device='mps.cpu',
    shots=10000,
    options={'mps_bond_dimension': 64}
)
counts = result.get_counts()
```

### Results
- **Total shots:** 10,000
- **Unique outcomes:** 15
- **Best bitstring:** 1001
- **Probability:** 66.5% (vs uniform 6.67%)
- **SNR:** 90.44 sigma

### Heavy Output Detection
```python
mean_prob = 1.0 / len(counts)  # 0.0667
heavy_outputs = [b for b, c in counts.items() 
                 if c/sum(counts.values()) > mean_prob]
# Found 5 heavy outputs

heavy_count = sum(counts[b] for b in heavy_outputs)
snr = (heavy_count/total - 0.5) / (0.5/total**0.5)
# SNR = 90.44 sigma
```

## Confidence Level
**VERY HIGH** - SNR > 10 sigma confirms clear heavy output

## Submission Text
Ran circuit on BlueQubit mps.cpu with 10k shots. Bitstring '1001' had highest probability (66.5% vs uniform 6.67%). SNR 90.44 sigma confirms clear heavy output. Peaked circuit successfully characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method.

## Key Insight
The circuit creates a peaked distribution where bitstring '1001' dominates with 66.5% probability - 10x higher than uniform distribution, indicating strong constructive interference at that output.

## Files Used
- Circuit: `../problems/P1_little_peak.qasm`
- Tutorial: `../../tutorials/tutorial_breaking_peaked_quantum_circuits_classically.ipynb`
- **Skill Used:** [`heavy-output-peaked-circuits`](../../../../.claude/skills/heavy-output-peaked-circuits/SKILL.md) - Reusable heavy output detection method

## Skill Application

This solution applies the [`heavy-output-peaked-circuits`](../../../../.claude/skills/heavy-output-peaked-circuits/SKILL.md) skill:
- High-shot sampling (10k shots)
- Heavy output identification (> mean probability)
- SNR validation (90.44 sigma)
- Confidence-based submission

## Verification
✅ Submitted and confirmed correct (2026-04-02)
