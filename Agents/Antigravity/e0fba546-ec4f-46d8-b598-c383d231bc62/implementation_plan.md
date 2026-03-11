---
type: antigravity-artifact
session_id: e0fba546-ec4f-46d8-b598-c383d231bc62
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.328
  stage: embryo
  cluster: Agents
---

# Implementation Plan - System Stability Hardening

## Problem
The system experiences recurring unresponsive states.
Investigation reveals **ZFS ARC (Adaptive Replacement Cache)** is configured with a maximum of **~124GB** on a **125GB** system.
This causes memory contention between filesystem caching and large AI models, leading to lockups when the kernel struggles to reclaim memory fast enough.
Additionally, the `ResourceMonitor` has a **10s heartbeat**, which is too slow to catch rapid resource spikes.

## Proposed Changes

### 1. Kernel & ZFS Tuning (`scripts/setup/tune_system.sh`)
- **[MODIFY]** Add logic to set `zfs_arc_max` to **17,179,869,184 bytes (16GB)**.
- **[MODIFY]** Ensure this setting is persisted in `/etc/modprobe.d/zfs.conf`.
- **[MODIFY]** Apply the change immediately if the ZFS module is loaded.

### 2. Resource Monitor Hardening (`src/cohezion/reliability/monitor.py`)
- **[MODIFY]** Reduce `heartbeat_interval` default from `10.0s` to **`3.0s`**.
- **[MODIFY]** Add **Swap Usage** and **ARC Size** to `get_vitals()`.
- **[MODIFY]** Update `_heartbeat_loop` logic:
    - Trigger **Desperation Mode** if `Swap > 50%`.
    - Trigger **Emergency Shutdown** if `Swap > 90%`.
    - Monitor `ARC` usage as part of the total memory pressure picture.

## Verification Plan

### Automated Verification
1.  **Run Tuning Script**: Execute `sudo ./scripts/setup/tune_system.sh`.
2.  **Verify ARC Limit**: Run `grep c_max /proc/spl/kstat/zfs/arcstats` and confirm it is ~16GB.
3.  **Stress Test**: Run `tests/automated/test_monitor_stress.py` (if it exists) or create a new `tests/automated/test_resource_monitor_v2.py` that mocks high swap usage to ensure `ResourceMonitor` reacts correctly.

### Manual Verification
1.  **Monitor Logs**: Check `logs/system_heartbeat.log` to see the new interval (3s) and new metrics (Swap/ARC).
