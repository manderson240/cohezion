---
description: "Hardware safety, FleetLock discipline, and memory bounds on AMD Strix Halo"
globs: ["scripts/preflight*.sh", "scripts/recover*.sh", "src/cohezion/inference/**"]
alwaysApply: true
---

# Rule: Hardware Safety & Fleet Discipline

## Triggers
- Local model execution, model loading via Lemonade/Ollama, or swarm spawning on Strix Halo APU.

## Enforced Behavior
1. **Fleet Preflight Mandatory**: Execute `bash scripts/preflight_fleet.sh` before spawning inference swarms. Exit non-zero = do not start.
2. **Thresholds**:
   - Available Memory: $\ge 25\text{ GiB}$
   - Swap: $\le 10\%$
   - GTT Allocation: $\le 50\text{ GiB}$
   - PSI Pressure: avg10 $\le 20.0$
3. **Single-Flight Lock**: Acquire `fleet_lock:modelload` before calling `lemonade load` or `ollama pull`. Never load models concurrently across UMA aperture.
4. **Autonomous Recovery**: If preflight fails due to stale cache/allocations, execute soft recovery: `sudo -n sh -c 'echo 3 > /proc/sys/vm/drop_caches'`.
