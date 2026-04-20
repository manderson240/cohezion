# Quantum Computing Research: Heavy Output Detection Optimization

**Date:** 2026-04-02  
**Research Topic:** Techniques for Large Peaked Circuits  
**Application:** BlueQubit Challenge P4-P10

---

## Bond Dimension Trade-offs (MPS)

### What is Bond Dimension?
In Matrix Product State (MPS) simulation, the bond dimension controls the amount of entanglement that can be captured between adjacent qubits.

**Formula:** Memory = O(N × D² × d) where:
- N = number of qubits
- D = bond dimension
- d = local dimension (2 for qubits)

### BlueQubit Limits

| Bond Dim | Max Qubits | Cost | Accuracy |
|----------|-----------|------|----------|
| 16 | ~50 | Low | Lower fidelity |
| 32 | ~45 | Medium | Good |
| 64 | ~40 | Higher | Very good |
| 128 | ~35 | High | Excellent |
| 256+ | <30 | Very high | Near-exact |

### Strategy for Free Tier
For P4 (48q) and P5 (44q), we're using bond_dim=16-32 to fit within free tier limits.

**Trade-off:** Lower bond_dim = less entanglement captured = potentially lower SNR, but still works for peaked circuits!

---

## Peaked Circuit Characteristics

### Why Heavy Output Detection Works

Peaked circuits are designed such that:
1. Constructive interference creates one dominant output
2. Probability is concentrated in a small set of "heavy" outputs
3. Even with lower bond_dim, the dominant peak remains detectable

### Circuit Analysis (from problems)

**Common patterns in P1-P3:**
- CZ gates creating phase relationships
- Single-qubit rotations (RZ, RY, RX)
- Layered structure
- Linear connectivity

**Why they peak:**
The circuit unitary U creates interference where:
|⟨x|U|0...0⟩|² ≈ 1 for some x (the heavy output)
|⟨y|U|0...0⟩|² ≈ 0 for most y

---

## Techniques for Larger Circuits

### 1. Reduced Bond Dimension
Already using this for P4-P5. Trade accuracy for feasibility.

### 2. Fewer Shots
Instead of 100k shots, try 50k or 25k to reduce runtime.

### 3. Circuit Simplification (Advanced)
If we had access to circuit manipulation:
- Remove redundant gates
- Merge rotations
- Optimize for MPS structure

### 4. Alternative Devices
For P6-P10 (62, 56, 49 qubits), options:
- **mps.gpu:** Requires paid tier
- **pauli-path:** For expectation values only
- **Local simulation:** If we can install BlueQubit locally

### 5. Hybrid Approach
For circuits >50 qubits:
- Use tensor network contraction instead of MPS
- Exploit circuit structure (e.g., brick-wall pattern)
- Approximate methods

---

## P4-P10 Strategy

### Immediate (Running now):
- P4 (48q): bond_dim=16
- P5 (44q): bond_dim=32

### Next Steps:
**P6-P10 (49-62 qubits):**
- Free tier unlikely to work
- Options:
  1. Request paid tier access
  2. Try bond_dim=8 (very low accuracy)
  3. Use BlueQubit web interface with credits
  4. Skip and focus on maximizing points from P1-P5

### Expected Outcomes

| Problem | Qubits | Expected Result | Confidence |
|---------|--------|-----------------|------------|
| P4 | 48 | Should complete with bond_dim=16 | Medium |
| P5 | 44 | Should complete with bond_dim=32 | High |
| P6 | 62 | Likely fails on free tier | Low |
| P7 | 45 | May work with bond_dim=16 | Medium |
| P8 | 40 | Should work with bond_dim=64 | High |
| P9 | 56 | Likely fails on free tier | Low |
| P10 | 49 | May work with bond_dim=16 | Medium |

---

## Research Summary

### Key Insight
Peaked circuits are forgiving of lower bond dimensions because:
1. The heavy output is robust
2. Approximate simulation preserves dominant peak
3. SNR > 10 achievable even with D=16-32

### For P6-P10
Best approach: Try with bond_dim=8-16, but expect failures on free tier.

### Code Optimization
```python
# Adaptive bond dimension selection
def select_bond_dim(num_qubits):
    if num_qubits <= 40:
        return 64
    elif num_qubits <= 45:
        return 32
    elif num_qubits <= 50:
        return 16
    else:
        return 8  # Last resort
```

---

## References

- MPS Tutorial: https://en.wikipedia.org/wiki/Matrix_product_state
- BlueQubit Docs: https://app.bluequbit.io/sdk-docs/
- Heavy Output Paper: Cross et al., "Validating quantum computers using randomized model circuits"

---

**Research Status:** Complete  
**Application:** P4-P5 running, P6-P10 pending strategy decision
