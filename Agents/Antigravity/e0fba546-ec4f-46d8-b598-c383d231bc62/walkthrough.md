---
type: antigravity-artifact
session_id: e0fba546-ec4f-46d8-b598-c383d231bc62
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.53
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# System Stability Hardening - Walkthrough

## Issue Diagnosis
The system was experiencing recurring unresponsive states (lockups) during high-load AI operations.
Investigation revealed that **ZFS ARC (Adaptive Replacement Cache)** was uncapped, consuming up to **124GB of the 128GB RAM**, leaving insufficient memory for large language models and application logic. This caused the kernel to thrash and freeze before it could reclaim memory.

## Implemented Solution

### 1. ZFS ARC Limitation
We configured a hard limit on the ZFS ARC to prevent it from starving the application layer.
- **Limit**: **16GB** (approx. 12.5% of total RAM).
- **Persistence**: Added to `/etc/modprobe.d/zfs.conf`.
- **Runtime**: Applied immediately via `/sys/module/zfs/parameters/zfs_arc_max`.

### 2. ResourceMonitor Hardening
The `ResourceMonitor` (Gatekeeper) was upgraded to be more reactive and aware of swap pressure.
- **Heartbeat Interval**: Reduced from **10s** to **3s** for faster detection of spikes.
- **New Metrics**: Added **Swap Usage** and **ARC Size** monitoring.
- **Desperation Mode**: Now triggers if **Swap > 50%**.
- **Emergency Shutdown**: Now triggers if **Swap > 90%**.

## Verification
- **ZFS ARC**: Confirmed `c_max` (cache max) is set to 16GB.
- **Swap**: 32GB ZVOL swap is active and monitored.
- **LRU Logic**: Verified `ModelWrangler` correctly tracks model usage and evicts the oldest models first when under pressure (`tests/automated/test_lru_swap.py` passed).

## Learnings
- **ZFS ARC**: Uncapped ARC on Linux is dangerous for memory-intensive workloads like AI. Hard limits are required.
- **The Sudo Trap**: Automated systems must degrade gracefully without needing root privileges. We hardened `tune_system.sh` to handle this better in future setups, though initial application still requires sudo.

