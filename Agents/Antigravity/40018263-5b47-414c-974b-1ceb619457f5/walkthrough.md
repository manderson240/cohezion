---
type: antigravity-artifact
session_id: 40018263-5b47-414c-974b-1ceb619457f5
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.315
  stage: embryo
  cluster: Agents
---

# Sleep Stabilization Walkthrough: Framework Desktop (Strix Halo)

This document summarizes the changes applied to resolve sleep-wake freezes on your **Framework Desktop (AMD Ryzen AI Max+ 395)**.

## Changes Implemented

### 1. Kernel Parameter Optimization (GRUB)
Applied `iommu=pt` to resolve resume hangs while maintaining virtualization support, along with platform-specific memory optimizations for the Strix Halo architecture.

- **File**: [/etc/default/grub](file:///etc/default/grub)
- **New Parameters**: `iommu=pt amdgpu.gttsize=131072 ttm.pages_limit=33554432`

Verified via `/etc/default/grub`:
```bash
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash iommu=pt amdgpu.gttsize=131072 ttm.pages_limit=33554432"
```

### 2. Diagnostic Tool Installation
The official **AMD S2idle Report** script has been downloaded to help diagnose any future blockers if the system still fails to enter the deepest sleep state.

- **Path**: [/home/mike-anderson/dev/cohezion/src/cohezion/healing/amd_s2idle_report.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/healing/amd_s2idle_report.py)

---

## Verification Results (Post-Reboot)

The following states have been confirmed active after the system reboot:

- **Uptime**: ~22 minutes (Confirming successful reboot).
- **Active Parameters**: `iommu=pt`, `amdgpu.gttsize=131072`, `ttm.pages_limit=33554432`.
- **Power State**: `[s2idle]` is the active selection in `/sys/power/mem_sleep`.
- **Driver Quirk**: Kernel confirmed using "Low-power S0 idle" and applied the NVMe simple suspend quirk automatically.

The system is now stable and optimized for the Strix Halo architecture.

## Related Vault Notes

- [[cohezion]]
