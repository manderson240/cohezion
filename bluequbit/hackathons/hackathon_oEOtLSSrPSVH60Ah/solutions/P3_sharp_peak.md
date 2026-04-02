# Solution: P3_sharp_peak

## Challenge
Sharp Peak 🔺

## Answer
```
01011000100010110011111000001010101010110001
```

**Status:** ✅ CONFIRMED CORRECT (50 points)

## Method
Ran circuit on BlueQubit mps.cpu with 100k shots using bond_dim=32 for 44 qubits. Bitstring '01011000100010110011111000001010101010110001' (reversed from raw) had highest probability. SNR 51.77 sigma confirms clear heavy output.

## Submission Text
Ran circuit on BlueQubit mps.cpu with 100k shots using bond_dim=32. Bitstring '01011000100010110011111000001010101010110001' (reversed from raw measurement) had highest probability. SNR 51.77 sigma confirms clear heavy output. Peaked circuit characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method. Note: Required smaller bond_dim=32 for 44 qubits on free tier.

## Files Used
- Circuit: `../problems/P3_sharp_peak.qasm`
- **Skill:** [`quantum-heavy-output-detection`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md)

## Verification
✅ CONFIRMED CORRECT (2026-04-02)
