# BlueQubit Challenge Submission Tracker

**Challenge:** oEOtLSSrPSVH60Ah  
**Started:** 2026-04-02  
**Status:** 🟢 Active

---

## Submissions Summary

| Problem | Qubits | Status | Raw Answer | Reversed (Submit This) | SNR | Confidence |
|---------|--------|--------|------------|------------------------|-----|------------|
| P1_little_peak | 4 | ✅ **CORRECT** | 1001 | 1001 | 90.44 | VERY HIGH |
| P2_swift_rise | 28 | ✅ **CORRECT** | 0011100001101100011011010011 | **1100101101100011011000011100** | 152.84 | VERY HIGH |
| P3_sharp_peak | 44 | ⏳ Running | TBD | TBD | TBD | TBD |
| P4_golden_mountain | 48 | ⏳ Not started | TBD | TBD | TBD | TBD |
| P5_granite_summit | 44 | ⏳ Running | TBD | TBD | TBD | TBD |
| P6_titan_pinnacle | 62 | ⏳ Not started | TBD | TBD | TBD | TBD |
| P7_heavy_hex_1275 | 45 | ⏳ Running | TBD | TBD | TBD | TBD |
| P8_grid_888_iswap | 40 | ⏳ Running | TBD | TBD | TBD | TBD |
| P9_hqap_1917 | 56 | ⏳ Not started | TBD | TBD | TBD | TBD |
| P10_heavy_hex_4020 | 49 | ⏳ Not started | TBD | TBD | TBD | TBD |

---

## Running Jobs

| Job ID | Problem | Qubits | Bond Dim | Status | Est. Time |
|--------|---------|--------|----------|--------|-----------|
| 8hUMnXnkxmXOvlCD | P3_sharp_peak | 44 | 32 | RUNNING | ~55s |
| mWV6NbpVm5dSUMct | P5_granite_summit | 44 | 32 | RUNNING | ~512s |
| [TBD] | P7_heavy_hex_1275 | 45 | 32 | [Pending] | - |
| [TBD] | P8_grid_888_iswap | 40 | 64 | [Pending] | - |

---

## Critical Finding: Bitstring Reversal

**⚠️ ALWAYS reverse bitstrings before submitting!**

### Why:
- BlueQubit SDK returns: qubit 0 as LSB (rightmost)
- Challenge expects: qubit 0 as MSB (leftmost)
- **Solution:** `submission = raw_bitstring[::-1]`

### Evidence:
- **P1:** "1001" is a palindrome (works either way)
- **P2:** Raw "001110..." was wrong, reversed "110010..." was correct

### Formula:
```python
raw = max(counts, key=counts.get)  # From BlueQubit
answer = raw[::-1]                  # For submission
```

---

## Strategy

### Completed:
1. ✅ P1: Submitted and confirmed correct
2. ✅ P2: Corrected with reversal, now correct

### In Progress:
3. ⏳ P3: Running (44 qubits, bond_dim=32)
4. ⏳ P5: Running (44 qubits, bond_dim=32)
5. ⏳ P7: Pending (45 qubits, bond_dim=32)
6. ⏳ P8: Pending (40 qubits, bond_dim=64)

### Next Steps:
- Wait for P3, P5, P7, P8 results
- Submit P4, P6, P9, P10 (may need paid tier or lower bond_dim)

---

## Free Tier Limits

| Circuit Size | Bond Dim | Success? |
|--------------|----------|----------|
| ≤40 qubits | 64 | ✅ Yes |
| 44-45 qubits | 32 | ⚠️ Trying |
| 48+ qubits | 32 | ❌ Likely fails |
| 62 qubits | 32 | ❌ Too large |

---

## Files

- **Solutions:** `solutions/P1_little_peak.md`, `solutions/P2_swift_rise.md`, etc.
- **Skill:** `.claude/skills/heavy-output-peaked-circuits/SKILL.md`
- **Problems:** `problems/*.qasm`

---

## Commands

Check all jobs:
```bash
python3 << 'EOF'
import bluequbit
bq = bluequbit.init()
jobs = ['8hUMnXnkxmXOvlCD', 'mWV6NbpVm5dSUMct']
for jid in jobs:
    j = bq.get(jid)
    print(f"{j.job_name}: {j.run_status}")
EOF
```

---

**Last Updated:** 2026-04-02  
**Next Check:** In 2 minutes
