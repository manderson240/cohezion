---
type: antigravity-artifact
session_id: 0c888e0d-6061-443c-a927-3d908cbf0d85
date: 2026-03-04
title: "Walkthrough: Guardrail Enhancement"
tags: [agent-output, antigravity, guardrails]
aspect: doer
neural:
  activation: 0.424
  stage: growing
  cluster: Agents
---

# Walkthrough: Guardrail Enhancement & VRAM Recovery

Following a system-wide unresponsiveness event that required a `REISUB` command, I conducted a root cause analysis and implemented enhanced hardware-aware guardrails.

## Root Cause Analysis

The system became unresponsive due to **Integrated GPU (iGPU) VRAM exhaustion**. 
- **Telemetry**: Logs showed VRAM pressure reaching **99.98%**.
- **Failure Chain**: 
    1. High VRAM pressure triggered the `ResourceMonitor`'s emergency shutdown.
    2. The shutdown failed because it attempted to run `sudo systemctl stop ollama`.
    3. Without a `sudo` password in the automated loop, the command stalled, and the system locked up under pressure.

## Improvements Made

### 🛡️ Tiered Guardrail System
Restored and codified a 3-tier response system in `cohezion.reliability.monitor`:
1. **Tier 1 (80% Load)**: Warning logs and checkpoint preparation.
2. **Tier 2 (90% Load)**: Active throttling (blocks Slot Acquisition).
3. **Tier 3 (95% Load)**: Emergency Shutdown.

### 📼 AMD VRAM Tracking
Implemented direct telemetry for the Framework 16's AMD GPU using `/sys` paths:
- Monitors `/sys/class/drm/card1/device/mem_info_vram_*`.
- Integrated VRAM pressure into the global backpressure signal.

### 🚑 Non-Privileged Emergency Shutdown
Fixed the "Sudo Trap" by switching to the Ollama HTTP API:
- **Automatic Unload**: The monitor now queries `http://localhost:11434/api/ps` to find running models.
- **Graceful Release**: It sends a `keep_alive: 0` request for each model, freeing VRAM instantly without requiring elevated privileges.

## Verification Results

### Automated Stress Test
Ran `python3 tests/automated/test_monitor_stress.py` with mocked vitals:

```bash
--- 🛡️ Testing ResourceMonitor Tiers ---
INFO:cohezion.reliability.monitor:🛡️ ResourceMonitor initialized with max_concurrency=2
✅ Tier 1: Logic processed.
Testing Tier 2 Throttling...
✅ Tier 2: Throttled correctly.
Testing Tier 3 Emergency...
ERROR:cohezion.reliability.monitor:🚨 EMERGENCY SHUTDOWN TRIGGERED: {'cpu_percent': 96, 'memory_percent': 50, 'vram_percent': 50, ...}
✅ Tier 3: Emergency shutdown triggered and Ollama model unload commanded.
```

### Manual Verification
- Verified `/sys` paths on live hardware.
- Confirmed `ollama ps` and the unload API work as expected in the local environment.
### 🔄 Dynamic Model Swapping & Priority Slots
Implemented hierarchical resource management to prevent high-priority reasoning tasks from being blocked by secondary agents:
- **Priority Slots**: Defined in `ModelWrangler` (1=Critical, 4=Low).
- **Proactive Eviction**: High-priority agents (Priority <= 2) now trigger a "Resource Preparation" phase that evicts lower-priority models from VRAM if pressure is >75%.
- **Router Protection**: The core `phi4:mini` routing model is protected from eviction to maintain system orchestrations.

### 👁️ Pulse HUD Overhaul (Quadrature Integration)
Transformed the `AutonomicDisplay` into a dense, high-fidelity command center:
- **Scaling Fixes**: Corrected CPU/RAM/VRAM rendering bugs (0.5 -> 50%).
- **12D Telemetry**: Integrated all 12 dimensions of the Ouroboros state vector, including RAM load and "Hidden Dynamics" (Momentum, Density, etc.).
- **Autonomic Survival**: Updated the `OuroborosGanglion` to include VRAM in its survival reflexes.
- **Visual Density**: Enhanced the HUD with glassmorphism, pulse animations, and grid-based logical dimensions for a "Minority Report" aesthetic.

### 🚒 Desperation Mode (Tiered Throttling)
Implemented a mid-tier safety net that prevents hard lockups by damping down non-essential computational activity:
- **Tier 1 (92%)**: Automatically sets non-essential processes (Fractal Universe, Research Scouts) to maximum niceness (19).
- **Tier 2 (94%)**: Sends `SIGSTOP` to pause these processes until resource pressure drops below 85%.
- **Autonomic Damping**: Updated the `OuroborosGanglion` to scale back agent activity (e.g., fewer concurrent tests) when "Damping" is active.
- **Verification**: Confirmed successful throttling and recovery cycles with `test_desperation_mode.py`.

---
> [!IMPORTANT]
> Cohezion is now "Hardened." Its resource stewardship allows for deep, autonomous exploration while maintaining system responsiveness even under extreme conditions.

## Related Vault Notes

- [[ai-safety]]
- [[cohezion]]
- [[fractal-universe]]
