# Challenge oEOtLSSrPSVH60Ah Solutions

**Status:** 🟢 In Progress  
**Submissions Used:** 2/50 (1 per solved problem)  
**Last Updated:** 2026-04-02

---

## Solved Problems

| Problem | Status | Bitstring | SNR | Confidence |
|---------|--------|-----------|-----|------------|
| [P1_little_peak](P1_little_peak.md) | ✅ **CORRECT** | `1001` | 90.44 | VERY HIGH |
| [P2_swift_rise](P2_swift_rise.md) | ✅ Ready | `0011100001101100011011010011` | 152.84 | VERY HIGH |
| P3_sharp_peak | ⏳ Not started | TBD | TBD | TBD |
| P4_golden_mountain | ⏳ Not started | TBD | TBD | TBD |
| P5_granite_summit | ⏳ Not started | TBD | TBD | TBD |
| P6_titan_pinnacle | ⏳ Not started | TBD | TBD | TBD |
| P7_heavy_hex_1275 | ⏳ Not started | TBD | TBD | TBD |
| P8_grid_888_iswap | ⏳ Not started | TBD | TBD | TBD |
| P9_hqap_1917 | ⏳ Not started | TBD | TBD | TBD |
| P10_heavy_hex_4020 | ⏳ Not started | TBD | TBD | TBD |

---

## Method: Heavy Output Detection

All solutions use the **Heavy Output Detection** method from Tutorial 2:

1. **Run circuit** on mps.cpu with high shots (10k-100k)
2. **Find heavy outputs** (bitstrings with probability > mean)
3. **Calculate SNR** to validate clear peak
4. **Submit bitstring** with maximum probability

### Confidence Levels

| SNR | Confidence | Action |
|-----|------------|--------|
| > 10 | VERY HIGH | ✅ Submit immediately |
| 5-10 | HIGH | Safe to submit |
| 2-5 | MEDIUM | Verify with more shots |
| < 2 | LOW | Circuit may not be peaked |

---

## Quick Reference

### Submitting Answers

1. Go to: https://app.bluequbit.io/challenges
2. Find challenge: **oEOtLSSrPSVH60Ah**
3. Select problem (P1, P2, etc.)
4. Enter bitstring from solution file
5. Add explanation (copy from `.md` file)

### Running New Circuits

```python
import bluequbit
import qiskit

bq = bluequbit.init()

# Load and run
with open('../problems/PX_name.qasm') as f:
    qc = qiskit.QuantumCircuit.from_qasm_str(f.read())

result = bq.run(qc, 
    device='mps.cpu',
    shots=100000,
    options={'mps_bond_dimension': 64}
)

counts = result.get_counts()
best = max(counts, key=counts.get)
print(f"Submit: {best}")
```

---

## Files

- **Solutions:** `P1_little_peak.md`, `P2_swift_rise.md`, etc.
- **Circuits:** `../problems/*.qasm`
- **Tutorials:** `../../tutorials/*.ipynb`
- **Skill:** `../../../../.claude/skills/heavy-output-peaked-circuits/SKILL.md`

---

## Notes

- **Free tier limit:** Works up to ~40 qubits with bond_dim=64
- **P3-P10 (44+ qubits):** May require smaller bond_dim or paid tier
- **5 submissions per problem:** Can iterate and improve SNR
- **Strategy:** Solve easiest first (P1, P2), then tackle larger circuits

---

## Success Metrics

- ✅ P1: SNR 90.44 (4 qubits, 6 gates)
- ✅ P2: SNR 152.84 (28 qubits, 2,310 gates)
- ⏳ P3-P10: Pending (44+ qubits)

**Next:** Analyze P3 (44 qubits) with smaller bond_dim
