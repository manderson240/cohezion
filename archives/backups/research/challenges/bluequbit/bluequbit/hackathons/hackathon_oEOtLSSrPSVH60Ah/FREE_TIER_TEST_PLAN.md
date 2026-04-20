# Free Tier Exhaustive Testing Plan
## Problems P1-P10 - All Free Options

**Goal:** Exhaust every possible free-tier option before requesting paid credits

---

## Already Completed:

### ✅ P1_little_peak (4 qubits)
- **Status:** SOLVED - 10 points ✅
- **Method:** bond_dim=64, shots=10,000
- **Result:** 100% accuracy

### ✅ P2_swift_rise (28 qubits)  
- **Status:** SOLVED - 20 points ✅
- **Method:** bond_dim=64, shots=100,000
- **Result:** 100% accuracy

### ✅ P3_sharp_peak (44 qubits)
- **Status:** SOLVED - 50 points ✅
- **Method:** bond_dim=32, shots=100,000
- **Result:** 100% accuracy (lucky!)

---

## Failed/Partial Solutions:

### ⚠️ P4_golden_mountain (48 qubits)
- **Tested:** bond_dim=16, shots=100,000
- **Result:** 28/48 accuracy ❌
- **Issue:** Free tier insufficient

**Remaining Free Options to Try:**
1. ✅ bond_dim=16 (tested - failed)
2. ⏳ bond_dim=8 (last resort - may work)
3. ⏳ shots=200,000 (more statistics)
4. ⏳ Circuit analysis/simplification

### ⚠️ P5_granite_summit (44 qubits)
- **Tested:** bond_dim=32, shots=100,000
- **Result:** 25/44 accuracy ❌
- **Issue:** Heavy hex structure too complex

**Remaining Free Options to Try:**
1. ✅ bond_dim=32 (tested - failed)
2. ⏳ bond_dim=64 (may exceed free tier but try)
3. ⏳ shots=200,000 (better statistics)
4. ⏳ Analyze circuit structure for shortcuts

---

## Not Yet Attempted:

### ⏳ P6_titan_pinnacle (62 qubits)
**Free Options to Try:**
1. bond_dim=8 (extreme compression)
2. bond_dim=16 (aggressive compression)
3. shots=100,000
4. shots=50,000 (faster, may be enough)
5. Any circuit simplification

### ⏳ P7_heavy_hex_1275 (45 qubits) - RUNNING
**Current:** bond_dim=16, shots=100,000
**If fails, try:**
1. bond_dim=32
2. bond_dim=8
3. shots=200,000

### ⏳ P8_grid_888_iswap (40 qubits) - RUNNING
**Current:** bond_dim=64, shots=100,000  
**Expected:** Should work (40q ≤ limit)

### ⏳ P9_hqap_1917 (56 qubits)
**Free Options to Try:**
1. bond_dim=8
2. bond_dim=16
3. shots=50,000
4. Circuit structure analysis

### ⏳ P10_heavy_hex_4020 (49 qubits)
**Free Options to Try:**
1. bond_dim=8
2. bond_dim=16
3. shots=100,000
4. Circuit analysis

---

## Free Tier Strategy Matrix:

| Bond Dim | Max Qubits | Accuracy | Use For |
|----------|-----------|----------|---------|
| 64 | 40 | High | P1-P3, P8 |
| 32 | 44 | Medium | P3 (worked), P5 (failed) |
| 16 | 48 | Low | P4 (failed), P7, P10 |
| 8 | 60+ | Very Low | P6, P9 (last resort) |

---

## Execution Order:

1. **Check running jobs:** P7, P8 completion
2. **Retry P4:** bond_dim=8, shots=200k
3. **Retry P5:** bond_dim=64 (if free tier allows), shots=200k
4. **Attempt P6:** bond_dim=8 or 16
5. **Attempt P9:** bond_dim=8 or 16
6. **Attempt P10:** bond_dim=8 or 16

---

**Expected Free Tier Ceiling:** ~44 qubits reliably, up to 50 with luck
**Expected Paid Tier Needed:** P4, P5, P6, P9, P10 for high accuracy
