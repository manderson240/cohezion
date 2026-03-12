---
type: antigravity-artifact
session_id: 7fb808c0-81bf-4a4e-872d-7b712e508ad1
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.331
  stage: embryo
  cluster: Agents
---

# Walkthrough: System Hardening & Multi-Tier Resource Safeguards

To prevent future system lockups (REISUB), I have implemented a proactive, multi-tiered resource defense system.

## Changes Made

### 1. Multi-Tier Resource Protection
Updated `ResourceMonitor` in [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py) to a 3-tier response system:
- **Tier 1 (85% Warning)**: Logs elevated usage and prepares for proactive checkpointing.
- **Tier 2 (90% Throttling)**: Blocks new LLM slots and enforces a 15-second cooling period.
- **Tier 3 (95% Emergency)**: Aggressively kills runaway mission processes (`fractal_nexus`, `shadow_scripter`, etc.) and attempts to halt the `ollama` service.

### 2. Hardware-Aware Immune System
Integrated hardware vitals into [immune_system.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/healing/immune_system.py). The `VelocityMonitor` now triggers a `SelfDiagnostic` if CPU, RAM, or VRAM exceeds 90%, allowing the system to diagnose hardware pressure before a lockup occurs.

### 3. Kernel Optimizations
Refined [tune_system.sh](file:///home/mike-anderson/dev/cohezion/scripts/setup/tune_system.sh) with:
- `vm.swappiness=5`: Prevents disk thrashing.
- `vm.vfs_cache_pressure=150`: Reclaims VFS cache more aggressively.
- `vm.dirty_ratio=10`: Avoids I/O blocking during high memory pressure.

## Verification Results

### Stress Test
Ran `tests/automated/test_monitor_stress.py` to verify the logic.
```bash
--- 🛡️ Testing ResourceMonitor Tiers ---
INFO:cohezion.reliability.monitor:Adjusted oom_score_adj for PID 29976 to 500
INFO:__main__:Tier 1 detected
Testing Tier 2 Throttling (Wait for capacity)...
WARNING:cohezion.reliability.monitor:⚠️ Throttling active (Tier 2): {'cpu_percent': 91...}. Waiting 15.0s...
✅ Tier 2: Throttled correctly.
Testing Tier 3 Emergency...
✅ Tier 3: Emergency shutdown triggered.
```

## User Action Required

> [!IMPORTANT]
> Please run the refined hardening script with sudo to apply the new kernel tweaks:
> ```bash
> sudo ./scripts/setup/tune_system.sh
> ```

This ensures the system "fails soft" by sacrificing processes instead of locking the entire OS.

## Related Vault Notes

- [[cohezion]]
