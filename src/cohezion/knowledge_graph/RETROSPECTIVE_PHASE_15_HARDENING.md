# RETROSPECTIVE: Phase 15 - Resource Hardening (OOM Prevention)

**Date**: 2026-02-01
**Topic**: Kernel-Level Stability & Memory Pressure Management
**Phase**: S15 (Hardening)

## 1. The Challenge
Running 70B+ parameter models on a 128GB unified memory system pushes the hardware to the absolute limit. We encountered hard system freezes (REISUB required) when the GPU (GTT) and System RAM usage overlapped, triggering the Linux OOM Killer to inaccurately target the desktop environment instead of the worker processes.

## 2. Issues Encountered & Solutions

### A. The "Hard Lock"
**Problem**: When VRAM spilled into GTT (System RAM), the system became unresponsive before the OOM killer could act.
**Solution**: **Voluntary Dilation**. We implemented a `ResourceMonitor` that:
1.  Polls `/proc/meminfo` and `nvidia-smi` (via PyNVML).
2.  If GTT > 80% or RAM > 90%:
    - Broadcasts a "Dilation" signal (slowing time).
    - Triggers "Emergency Brain Drain" (unloads huge models).
3.  **Result**: The system "fades" instead of crashing.

### B. Process Prioritization
**Problem**: Linux treats all user processes equally by default.
**Solution**: We deployed `scripts/setup/harden_system.py` to adjust `oom_score_adj`:
- **Swarm Workers**: `+500` (First to die).
- **Database/Storage**: `-200` (Protected).
- **Display Server**: `-500` (Critical).

### C. ZFS ARC Contention
**Problem**: ZFS caching (ARC) fought with AI models for RAM.
**Solution**: Capped ZFS ARC Max to 8GB (down from dynamic 64GB) during "High Alert" mode.

## 3. Metrics & Validation
- **Stress Test**: Simulated 95% memory pressure.
- **Outcome**: Swarm agents successfully terminated self; Database and Desktop remained responsive.
- **Recovery Time**: <5 seconds (vs. hard reboot).

## 4. Key Takeaways
- **Fail Gracefully**: It is better to kill a worker and restart the task than to crash the kernel.
- **Proactive vs. Reactive**: Waiting for the kernel OOM killer is too late. The application must know its limits.
- **Telemetry Loop**: The "Pulse" (Phase 14) was critical in debugging this phase.
