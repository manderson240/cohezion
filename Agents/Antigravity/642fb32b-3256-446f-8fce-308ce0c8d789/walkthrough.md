---
type: antigravity-artifact
session_id: 642fb32b-3256-446f-8fce-308ce0c8d789
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.358
  stage: embryo
  cluster: Agents
---

# Stability Hardening Walkthrough

This task addressed the recent system unresponsiveness caused by a GPU hang during high-load `ollama` operations. We've implemented multi-layered guardrails to detect, manage, and recover from such failures.

## Changes Implemented

### 1. Advanced Resource Monitoring
- **GPU Hang Detection**: The `ResourceMonitor` now proactively scans kernel logs (`journalctl`) for AMDGPU ring timeouts and page faults.
- **Dynamic Heartbeat**: The monitor increases its frequency to **2 seconds** during high-pressure scenarios (CPU/RAM/VRAM > 90%).
- **96GB Model Budget**: A strict aggregate limit for loaded Ollama models is enforced to prevent host RAM exhaustion on the 128GB machine.
- **Global Loading Semaphore**: Prevents concurrent model loads from multiple agents, which was a likely trigger for driver instability.

### 2. Autonomic Immune Response
- **Hardware-Aware Diagnosis**: The `ImmuneSystem` now triggers self-diagnosis immediately when the `ResourceMonitor` detects critical pressure or kernel-level instability.

### 3. System-Level Hardening
- **OOM Score Adjustment**: `ollama` processes are now flagged with a higher OOM score (500), directing the kernel to discard them first rather than hanging the entire system.
- **Improved Kernel Parameters**: Optimized `sysctl` settings for swap, cache pressure, and dirty ratios to ensure the system "fails soft."

### 4. Phase 1: Automated Model Replacement (LRU Swap)
- **Model Usage Tracking**: `ResourceMonitor` now tracks the last-used timestamp for every loaded model.
- **Smart Swap Logic**: `ModelWrangler` automatically identifies and unloads the least recently used (LRU) models when the 96GB budget is reached.
- **Proactive Eviction**: The system now clears space *before* loading new models if it anticipates a budget breach.
- **Global Loading Guard**: Enforced sequential model loading via a global semaphore to prevent concurrent VRAM spikes.

## Verification Results

### Automated LRU Swap Test
Verified the LRU usage tracking and budget-triggered eviction using `tests/automated/test_lru_swap.py`.

```bash
uv run python3 tests/automated/test_lru_swap.py
```
> [!NOTE]
> **Result**: Oldest models (model-a) were correctly identified and evicted first when the simulated load hit 95GB.

### Heartbeat Logging
Verified that the new `ModelLoad` field and dynamic intervals are correctly recorded in `logs/system_heartbeat.log`.

```text
[2026-01-28 14:36:12] CPU: 3.8% | RAM: 70.0% | VRAM: 89.5% | ModelLoad: 4.2GB | LLM Calls: 0 | Dilation: 0.4
```

## Conclusion
The system is now significantly more resilient to hardware-induced hangs. The combination of faster detection and targeted OOM priority ensures that even if a driver failure occurs, the system can attempt recovery before requiring manual intervention.
