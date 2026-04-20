# Skill: Heavy Output Detection for Peaked Circuits

## Description

Extract the heavy output bitstring from a peaked quantum circuit using high-shot sampling and SNR (Signal-to-Noise Ratio) calculation. Proven winner on BlueQubit hackathon challenges.

## When to Use

- Challenge type: Peaked circuit (find dominant bitstring)
- Circuit has >2 qubits with CZ/CNOT gates creating interference patterns
- Goal: Identify bitstring with probability significantly above uniform
- Device: mps.cpu (free tier, up to ~40 qubits)

## Parameters

| Parameter | Value | Notes |
|-----------|-------|-------|
| Device | `mps.cpu` | Free tier, general simulation |
| Shots | 10,000 - 100,000 | More shots = better SNR accuracy |
| Bond Dimension | 64-512 | Higher for larger circuits |
| Confidence Threshold | SNR > 10 | Very High confidence |

## Method

### Step 1: Run Circuit
```python
import bluequbit
import qiskit

bq = bluequbit.init()

# Load circuit
with open('circuit.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

# Run with high shots
result = bq.run(qc, 
    device='mps.cpu',
    shots=100000,
    options={'mps_bond_dimension': 128}
)
counts = result.get_counts()
```

### Step 2: Find Heavy Outputs
```python
# Calculate mean probability
mean_prob = 1.0 / len(counts)

# Identify heavy outputs (> mean probability)
heavy_outputs = [
    bitstring for bitstring, count in counts.items()
    if count / sum(counts.values()) > mean_prob
]
```

### Step 3: Calculate SNR
```python
total_shots = sum(counts.values())
heavy_count = sum(counts[b] for b in heavy_outputs)

# SNR formula: (p_heavy - 0.5) / (0.5 / sqrt(N))
snr = (heavy_count / total_shots - 0.5) / (0.5 / total_shots ** 0.5)
```

### Step 4: Select Best Bitstring
```python
# Bitstring with maximum count
best_bitstring = max(counts, key=counts.get)
best_probability = counts[best_bitstring] / total_shots
```

## Validation

| SNR | Confidence | Action |
|-----|------------|--------|
| > 10 | VERY HIGH | Submit immediately |
| 5-10 | HIGH | Safe to submit |
| 2-5 | MEDIUM | Verify with more shots |
| < 2 | LOW | Circuit may not be peaked |

## Example Output

```
Bitstring: 1001
Probability: 66.5% (vs uniform 6.67%)
SNR: 90.44 sigma
Confidence: VERY HIGH
```

## Code Template

```python
"""
Heavy Output Detection Solver
Based on BlueQubit Tutorial 2: Breaking Peaked Circuits
"""

import bluequbit
import qiskit
from collections import Counter

def solve_peaked_circuit(circuit_path, shots=100000, bond_dim=128):
    """
    Find heavy output from peaked circuit.
    
    Args:
        circuit_path: Path to .qasm file
        shots: Number of shots (default 100k)
        bond_dim: MPS bond dimension (default 128)
    
    Returns:
        dict: {'bitstring': str, 'probability': float, 'snr': float}
    """
    # Initialize
    bq = bluequbit.init()
    
    # Load circuit
    with open(circuit_path) as f:
        qc = qiskit.QuantumCircuit.from_qasm_str(f.read())
    
    # Run
    result = bq.run(
        qc,
        device='mps.cpu',
        shots=shots,
        options={'mps_bond_dimension': bond_dim}
    )
    counts = result.get_counts()
    
    # Find heavy outputs
    total = sum(counts.values())
    mean_prob = 1.0 / len(counts)
    
    heavy_outputs = [
        b for b, c in counts.items()
        if c / total > mean_prob
    ]
    
    # Calculate SNR
    heavy_count = sum(counts[b] for b in heavy_outputs)
    snr = (heavy_count / total - 0.5) / (0.5 / total ** 0.5)
    
    # Best bitstring
    best = max(counts, key=counts.get)
    prob = counts[best] / total
    
    return {
        'bitstring': best,
        'probability': prob,
        'snr': snr,
        'heavy_outputs': len(heavy_outputs)
    }

# Usage
if __name__ == "__main__":
    result = solve_peaked_circuit(
        'P1_little_peak.qasm',
        shots=10000,
        bond_dim=64
    )
    print(f"Submit: {result['bitstring']}")
    print(f"SNR: {result['snr']:.2f} sigma")
```

## Key Insights

1. **High shots critical:** 10k+ shots needed for accurate SNR
2. **Bond dimension:** Higher = more accurate, but costs more
3. **Heavy output definition:** Any bitstring > mean probability
4. **SNR threshold:** > 10 sigma = submission-worthy
5. **Free tier limit:** Works up to ~40 qubits with bond_dim=64

## Success History

- **P1_little_peak (4q):** SNR 90.44, Bitstring 1001 ✅  
  *Note: Palindrome - works raw or reversed*
- **P2_swift_rise (28q):** SNR 152.84, Bitstring 1100101101100011011000011100 ✅  
  *Note: Must reverse from raw BlueQubit output*
- **Little Dimple challenge:** SNR 9,947 (proven winner)
- **Method:** Tutorial 2 from BlueQubit documentation

## ⚠️ CRITICAL: Bitstring Reversal Required

**BlueQubit SDK returns bitstrings with qubit 0 as LSB (rightmost).**
**Challenge platform expects qubit 0 as MSB (leftmost).**

**ALWAYS reverse before submitting:**

```python
raw = max(counts, key=counts.get)  # e.g., "0011"
submission = raw[::-1]              # Submit "1100"
```

**Why this matters:**
- P1 "1001" worked because it's a palindrome (same forward/backward)
- P2 revealed the issue - raw "001110..." was wrong, reversed "110010..." was correct
- **For P3-P10: ALWAYS reverse the bitstring!**

## Solutions

Complete solutions with submission text:
- [P1_little_peak](../../../bluequbit/hackathons/hackathon_oEOtLSSrPSVH60Ah/solutions/P1_little_peak.md)
- [P2_swift_rise](../../../bluequbit/hackathons/hackathon_oEOtLSSrPSVH60Ah/solutions/P2_swift_rise.md)
- [All Solutions](../../../bluequbit/hackathons/hackathon_oEOtLSSrPSVH60Ah/solutions/)

## References

- Tutorial: `tutorial_breaking_peaked_quantum_circuits_classically.ipynb`
- SDK: https://app.bluequbit.io/sdk-docs/
- Original paper: Heavy Output Generation (HOG) test

## Version

- Created: 2026-04-02
- Tested on: BlueQubit SDK 0.18.5b1
- Challenge: oEOtLSSrPSVH60Ah
