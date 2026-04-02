# BlueQubit Challenge Submission Strategy

## Challenge Overview: oEOtLSSrPSVH60Ah

**Total Problems:** 10 (P1 through P10)  
**Submissions per Problem:** 5  
**Total Submissions Available:** 50

---

## Problem Analysis

| Problem | Qubits | Gates | Status | Strategy |
|---------|--------|-------|--------|----------|
| P1_little_peak | 4 | 6 | ✅ **SOLVED** | Submit: **1001** (66.5%, SNR 90.44) |
| P2_swift_rise | 28 | 2,310 | ⏳ Running | Wait for results |
| P3_sharp_peak | 44 | 577 | ❌ Too large (free tier) | Try bond_dim=32 or manual submission |
| P4_golden_mountain | 48 | ~2,500+ | ❌ Too large (free tier) | Requires paid tier or optimization |
| P5_granite_summit | TBD | TBD | Not analyzed | - |
| P6_titan_pinnacle | TBD | TBD | Not analyzed | - |
| P7_heavy_hex_1275 | TBD | TBD | Not analyzed | - |
| P8_grid_888_iswap | TBD | TBD | Not analyzed | - |
| P9_hqap_1917 | TBD | TBD | Not analyzed | - |
| P10_heavy_hex_4020 | TBD | TBD | Not analyzed | - |

---

## Submission Plan

### Phase 1: Quick Wins (Now)

**P1_little_peak:**
- ✅ **READY TO SUBMIT**
- Best bitstring: **1001**
- Probability: 66.5%
- SNR: 90.44 sigma (EXTREMELY HIGH)
- **Confidence: VERY HIGH**

### Phase 2: In Progress

**P2_swift_rise:**
- Status: Running on mps.cpu (100k shots, bond_dim=64)
- Estimated time: ~150 seconds
- Expected result within 2-3 minutes

### Phase 3: Large Circuits (44+ qubits)

For P3-P10, we have options:

**Option A: Reduce bond dimension**
- Try bond_dim=32 or bond_dim=16
- May work on free tier but less accurate
- Risk: lower SNR

**Option B: Manual submission via web UI**
- If you have credits/paid tier
- Can run with optimal parameters

**Option C: Optimize circuit first**
- Analyze circuit structure
- Find smaller equivalent circuits
- Use Pauli-path for expectation values

---

## Submission Strategy per Problem

### P1: Little Peak (4 qubits)
```
Submission #1: 1001 (66.5%, SNR 90.44) ← SUBMIT THIS NOW
Submissions #2-5: Save for later if needed
```

### P2: Swift Rise (28 qubits)
```
Submission #1: Wait for current result
Submissions #2-5: Can try different:
  - Bond dimensions (32, 64, 128, 256)
  - Shot counts (50k, 100k, 200k)
  - Pick best SNR from all runs
```

### P3-P10: Large Circuits (44+ qubits)
```
Strategy:
1. Start with bond_dim=32 (smallest that might work)
2. If fails, try bond_dim=16 (lower accuracy)
3. If still fails, manual submission needed
4. Can try 5 different strategies:
   - Different bond dimensions
   - Different shot counts
   - Circuit optimization
   - Alternative measurement schemes
```

---

## Free Tier Limits

From testing:
- **mps.cpu:** Works up to ~40 qubits with bond_dim=64
- **P2 (28 qubits):** Works with bond_dim=64
- **P3 (44 qubits):** Requires smaller bond_dim or paid tier
- **P4 (48 qubits):** Likely requires paid tier

**Bond dimension trade-off:**
- Higher bond_dim = More accurate but costs more
- Lower bond_dim = Cheaper but less accurate
- For peaked circuits, even low bond_dim often works

---

## Submission Format

Based on previous challenge format, submit:
- **Bitstring** (e.g., "1001" for P1)
- Submit via web UI at: https://app.bluequbit.io/challenges

---

## Next Steps

### Immediate (Now):
1. ✅ Submit P1: **1001**
2. ⏳ Wait for P2 results

### Short-term (Next 30 min):
3. Analyze P3-P10 circuit sizes
4. Try P3 with bond_dim=32
5. Optimize submission strategy for larger circuits

### With 5 submissions per problem:
- Can experiment with different parameters
- Submit best result from multiple attempts
- Have backup submissions if first attempts fail

---

## Confidence Levels

- **P1:** VERY HIGH (SNR 90.44) - Submit immediately
- **P2:** PENDING - Wait for results
- **P3-P10:** UNKNOWN - Need to test free tier limits

---

## Key Insight

With 5 submissions per problem:
- **Don't worry about getting it perfect on first try**
- Can submit, see results, adjust, and resubmit
- Leaderboard likely shows scores immediately
- Can iterate to improve SNR

---

**Recommendation:** 
1. Submit P1 now (guaranteed win)
2. Wait 2 minutes for P2
3. Then tackle P3-P10 systematically
