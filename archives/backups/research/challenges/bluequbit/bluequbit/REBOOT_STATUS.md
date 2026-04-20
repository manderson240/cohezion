# BlueQubit Challenge Status - Pre-Reboot

**Date:** 2026-04-02
**Challenge:** oEOtLSSrPSVH60Ah

## Current Score: 80 points (P1-P3 solved)

## Running Jobs

### P7 Heavy Hex Retry (Job: tUfVijYQZZ8KkVxA)
- **Status:** COMPLETED but no clear peak
- **Result:** Uniform distribution (no heavy output)
- **Issue:** bond_dim=16 too low for 45 qubit heavy hex
- **Tried:** bond_dim=32 (completed but uniform results)

### P8 Grid iSWAP (Job: xg1wuFcwg3xJzceI) 
- **Status:** RUNNING (40 qubits, should complete on free tier)
- **Submitted:** 2026-04-02 15:25:30 UTC
- **Expected runtime:** ~13 minutes
- **Device:** mps.cpu with bond_dim=64

## Solution Status

| Problem | Qubits | Status | Answer | Points |
|-----------|--------|--------|--------|--------|
| P1_little_peak | 4 | ✅ SOLVED | `1001` | 10 |
| P2_swift_rise | 28 | ✅ SOLVED | `1100101101100011011000011100` | 20 |
| P3_sharp_peak | 44 | ✅ SOLVED | `01011000100010110011111000001010101010110001` | 50 |
| P4_golden_mountain | 48 | ⚠️ Low accuracy (28/48) | - | - |
| P5_granite_summit | 44 | ⚠️ Low accuracy (25/44) | - | - |
| P6_titan_pinnacle | 62 | ❌ NEEDS PAID TIER | - | - |
| P7_heavy_hex_1275 | 45 | ⚠️ RETRYING | - | - |
| P8_grid_888_iswap | 40 | ⏳ RUNNING | - | - |
| P9_hqap_1917 | 56 | ❌ NEEDS PAID TIER | - | - |
| P10_heavy_hex_4020 | 49 | ❌ NEEDS PAID TIER | - | - |

## Files Created/Modified

### Retry Scripts
- `retry_p7_system.py` - P7 retry with higher bond_dim
- `solve_p8.py` - P8 solver
- `check_p7_final.py`, `check_p8.py` - Status checkers

### Key Learnings
1. **P7 failed** because bond_dim=16 insufficient for 45-qubit heavy hex
2. **Free tier limit:** ~44 qubits reliably
3. **Heavy hex circuits** need higher bond_dim than brick wall at same qubit count
4. **P6, P9, P10** require paid tier (56-62 qubits)

## Next Steps After Reboot

1. **Check P8 result:** Run `check_p8.py` to see if completed
2. **Retry P7:** Try bond_dim=64 or pauli-path method
3. **Submit funding request:** ~$0.50 for P4, P5, P6, P9, P10
4. **Focus on solvable:** P8 (40 qubits) should work on free tier

## Critical Commands

```bash
# Check P8 status
cd /home/mike-anderson/dev/cohezion/bluequbit
/home/linuxbrew/.linuxbrew/bin/python3 check_p8.py

# Check all running jobs
cd /home/mike-anderson/dev/cohezion/bluequbit
/home/linuxbrew/.linuxbrew/bin/python3 -c "
import bluequbit
import os
# ... (see check scripts for full code)
"
```

## API Token
Located in: `/home/mike-anderson/dev/cohezion/.env`
- BLUEQUBIT_API_TOKEN=Wq0MRh8lQbTVSeFzbKZc8V6wqvnWZPWM
