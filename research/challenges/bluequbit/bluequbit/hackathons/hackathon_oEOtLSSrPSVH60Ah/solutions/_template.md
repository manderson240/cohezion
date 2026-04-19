# Solution: {{PROBLEM_NAME}}

## Challenge
{{PROBLEM_DISPLAY_NAME}} {{EMOJI}}

## Answer
```
{{BITSTRING}}
```

## Method

### Circuit Analysis
- **Qubits:** {{NUM_QUBITS}}
- **Gates:** {{NUM_GATES}}
- **Type:** {{CIRCUIT_TYPE}}

### Execution
```python
import bluequbit
import qiskit

bq = bluequbit.init()

with open('{{QASM_FILENAME}}') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# {{BOND_DIM_REASON}}
result = bq.run(qc, 
    device='mps.cpu',
    shots={{SHOTS}},
    options={'mps_bond_dimension': {{BOND_DIM}}}
)
counts = result.get_counts()

raw = max(counts, key=counts.get)
answer = raw[::-1]  # REVERSE for submission
```

### Results
- **Total shots:** {{SHOTS}}
- **Unique outcomes:** {{UNIQUE_OUTCOMES}}
- **Best bitstring (raw):** `{{RAW_BITSTRING}}`
- **Best bitstring (reversed):** `{{BITSTRING}}`
- **Probability:** {{PROBABILITY}}% (vs uniform {{UNIFORM_PROB}}%)
- **SNR:** {{SNR}} sigma

## Submission Text
Ran circuit on BlueQubit mps.cpu with {{SHOTS}}k shots using bond_dim={{BOND_DIM}} for {{NUM_QUBITS}} qubits. Bitstring '{{BITSTRING}}' (reversed from raw measurement '{{RAW_BITSTRING}}') had highest probability ({{PROBABILITY}}% vs uniform {{UNIFORM_PROB}}%). SNR {{SNR}} sigma confirms {{CONFIDENCE}} heavy output. {{CIRCUIT_TYPE}} peaked circuit characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method.{{NOTES}}

## Confidence Level
**{{CONFIDENCE}}** - SNR {{SNR}} sigma indicates {{CONFIDENCE_DESC}} heavy output

## Key Insight
{{KEY_INSIGHT}}

## Files Used
- Circuit: `../problems/{{QASM_FILENAME}}`
- Tutorial: `../../tutorials/tutorial_breaking_peaked_quantum_circuits_classically.ipynb`
- **Skill Used:** [`quantum-heavy-output-detection`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md)

## Skill Application
This solution applies the [`quantum-heavy-output-detection`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md) skill:
- High-shot sampling ({{SHOTS}} shots)
- Heavy output identification (> mean probability)
- SNR validation ({{SNR}} sigma)
- Bitstring reversal for correct submission format

## Verification
✅ {{STATUS}} ({{DATE}})
