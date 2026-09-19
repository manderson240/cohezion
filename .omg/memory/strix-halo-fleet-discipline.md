---
title: "AMD Strix Halo Fleet Discipline & Hardware Sentry"
category: hardware
updated: 2026-09-19
coherence: 0.50
---

# AMD Strix Halo Fleet Discipline & Hardware Sentry

## Hardware Specs
- **SoC**: AMD Ryzen AI MAX+ 395 (16 Zen 5 cores, 32 threads, XDNA 2 NPU)
- **iGPU**: AMD Radeon 8060S (gfx1151 / RDNA 3.5, 40 CUs)
- **RAM**: 128GB Unified LPDDR5X (120GB GTT UMA aperture)

## Safety Guardrails
1. **Preflight Fleet Check**: Run `bash scripts/preflight_fleet.sh` before launching local inference.
   - Available memory: $\ge 25\text{ GiB}$ floor
   - Swap: $\le 10\%$ threshold
   - GTT: $\le 50\text{ GiB}$ ceiling
   - PSI memory pressure: avg10 $\le 20.0$
2. **FleetLock Single-Flight Rule**: Acquire `fleet_lock:modelload` before loading any local model to prevent concurrent aperture races.
3. **Recovery**: If zombie state occurs, run `bash scripts/recover_fleet.sh --soft`. Never automate hard cold-boot.
