# Solution: P2_swift_rise

## Challenge
Swift Rise 📈

## Answer
```
1100101101100011011000011100
```

**Status:** ✅ CONFIRMED CORRECT (20 points)

## Method
Ran circuit on BlueQubit mps.cpu with 100k shots. Bitstring '1100101101100011011000011100' (reversed from raw) had highest probability (35.531% vs uniform 0.0043%). SNR 152.84 sigma confirms extremely clear heavy output.

## Submission Text
Ran circuit on BlueQubit mps.cpu with 100k shots. Bitstring '1100101101100011011000011100' (reversed from raw measurement '0011100001101100011011010011') had highest probability (35.531% vs uniform 0.0043%). SNR 152.84 sigma confirms extremely clear heavy output. Peaked circuit characterized using tutorial_breaking_peaked_quantum_circuits_classically.ipynb heavy output detection method. Note: Bitstring reversed due to qubit ordering convention.

## Files Used
- Circuit: `../problems/P2_swift_rise.qasm`
- **Skill:** [`quantum-heavy-output-detection`](../../../../.claude/skills/quantum-heavy-output-detection/SKILL.md)

## Verification
✅ CONFIRMED CORRECT (2026-04-02)
