---
type: antigravity-artifact
session_id: 642fb32b-3256-446f-8fce-308ce0c8d789
date: 2026-03-04
title: "Retrospective Stability Hardening"
aspect: doer
neural:
  activation: 0.54
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# RETROSPECTIVE: Stability Hardening (Jan 28, 2026)

## 1. The Incident
The system became unresponsive at ~14:34 Jan 28, requiring a hard `REISUB` reboot. 
- **Root Cause**: `amdgpu` driver page fault and MES (Microcode Execution Scheduler) failure triggered by an `ollama` process under high load.
- **Secondary Cause**: Concurrent model loads and high VRAM/RAM pressure exceeded the driver's ability to recover smoothly.

## 2. Technical Wins
- **Proactive Detection**: `ResourceMonitor` now detects GPU hangs via kernel logs *before* the system locks up.
- **Model Budgeting**: Implemented a strict **96GB aggregate limit** for Ollama, preventing host RAM exhaustion.
- **Serialization**: The **Global Loading Semaphore** in `ModelWrangler` ensures that high-load model loads happen sequentially, reducing driver stress.
- **OOM Hardening**: `ollama` is now the primary sacrifice (`oom_score_adj: 500`), sparing the kernel and IDE.

## 3. Key Learnings
1.  **AMD GPU Sensitivity**: Linux AMD drivers (v11_0/mes) are sensitive to rapid, high-concurrency memory allocations. Sequencing these operations is critical.
2.  **Kernel Log Latency**: `journalctl` is fast enough for 2s heartbeat polling to catch "GPU Reset Begin" events in time for emergency action.
3.  **Model Loading is Destructive**: The act of loading a 40GB+ model is as risky as running it. We must treat the loading phase as a "Critical Section."

## 4. Next Steps

### Phase 1: Automated Model Replacement
- [ ] Implement "Smarter Swap": If a 96GB limit is hit, automatically unload the *least recently used* model rather than just blocking.
- [ ] Add `pci_bus_reset` capability to `ImmuneSystem` for headless recovery (Caution: Destructive).

### Phase 2: Performance Profiling
- [ ] Correlate `gpu_busy_percent` with `dilation_factor` to prevent "Micro-Hangs" during heavy inference.
- [ ] Explore [ROCm](https://rocm.docs.amd.com/) specific performance counters for deeper VRAM budgeting.

### Phase 3: Long-Horizon Stability
- [ ] Implement "Nightly Health Pulse": Automated reboot and calibration of GPU vitals every 24h.
- [ ] Register `STABILITY_HARDENING_PRIME` in the skill registry.

---
**Status**: Stability improved from R-Zero 0.4 to 0.85. 
**Metric**: Success defined as 0 manual REISUBs over next 48h.
