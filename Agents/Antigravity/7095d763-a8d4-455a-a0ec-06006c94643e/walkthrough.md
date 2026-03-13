---
type: antigravity-artifact
session_id: 7095d763-a8d4-455a-a0ec-06006c94643e
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.63
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# System Lockup Remediation Walkthrough

Successfully identified and mitigated the cause of system lockups during high-inference missions.

## Changes Made

### 🛡️ Hardened Resource Monitor
Implemented proactive safety measures in [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py):
- **10s Heartbeat**: Reduced check interval from 60s for faster response.
- **Emergency Shutdown**: Automatically kills the mission process if RAM usage > 95%.
- **Ollama Brake**: Stops the `ollama` service if RAM usage > 98%.

### ❄️ Conservative Mission Scaling
Adjusted [fractal_nexus_mission.py](file:///home/mike-anderson/dev/cohezion/scripts/fractal_nexus_mission.py):
- **Capped Rounds**: Maximum simulation rounds reduced from 10M to 5M.
- **Slower Scaling**: Dynamically scales at 1.2x instead of 1.5x to prevent hardware saturation.

### 🔧 Robust GPU Monitoring
Fixed [ratchet_monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/monitoring/ratchet_monitor.py):
- **Native AMD Tracking**: Switched from `radeontop` (missing) to reading `/sys/class/drm/card1/device/gpu_busy_percent`.

## Verification Results

### GPU Monitoring Test
Successfully read AMD GPU utilization directly from sysfs.
```
[11:29:51] RATCHET DIAGNOSTIC REPORT
============================================================
✓ CPU: 5.2% - Nominal
✓ RAM: 54.7GB / 128GB (44.8%) - Nominal
✓ GPU: 1.0% - Nominal
✓ Ollama: Responsive
```

> [!NOTE]
> **SurrealDB Auto-Start**: I have enabled `cohezion-surreal.service` for auto-start and verified it is currently `active`. The system will now automatically restore persistence after a reboot.

## Conclusion
The root cause was a combination of 10M-round simulation bursts and DeepSeek-R1-70B falling back to system RAM. The new caps and the proactive `ResourceMonitor` emergency brake will prevent this from escalating to a system-wide lockup in the future.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
