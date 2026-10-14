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
5. **Port 13305 Gateway Invariant**: All local inference clients and tools MUST connect via port 13305 (`admission_proxy` with 16GB memory floor), which proxies upstream to `lemond` on port 13315. Never connect to port 13315 directly.
6. **Quality Over Speed (Timeout SLA)**: Enforce minimum 300.0s read timeout (`httpx.Timeout(connect=15.0, read=300.0, write=60.0, pool=10.0)`) across all local inference clients. Short scalar timeouts (15s–60s) are prohibited to give thinking and heavy reasoning models full generation runway.
7. **NPU Workhorse Model**: The AMD XDNA2 NPU runs `qwen3.5-4b-FLM` (recipe `flm`, 16k context, pinned) for ultra-low-power (<2W, 0 UMA RAM usage) deterministic reasoning and agentic tool-use.
