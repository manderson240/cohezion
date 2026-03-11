---
type: antigravity-artifact
session_id: 40018263-5b47-414c-974b-1ceb619457f5
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.351
  stage: embryo
  cluster: Agents
---

# Stabilizing Framework Desktop Sleep (Ryzen AI Max 300 Series)

The system is a high-performance **Framework Desktop** featuring the **AMD Ryzen AI Max+ 395** (Strix Halo) platform. Sleep-wake freezes on this cutting-edge architecture (Zen 5 + RDNA 3.5) under Linux 6.14 are typically related to early-stage power management (S2idle) or IOMMU/Display Core transitions.

## User Review Required

> [!IMPORTANT]
> **Kernel Parameters to AVOID**:
> - `nvme.noacpi=1`: Generally discouraged for Zen 5; Kernel 6.14 includes native fixes for NVMe power transitions.
> - `amdgpu.dc=0`: **DO NOT USE**. Strix Halo requires the Display Core (DC) for 3D/VGA functionality. Disabling it will likely result in a broken display.

> [!TIP]
> **Virtualization & Docker Compatibility**:
> Based on your concern about Docker and hypervisors, I've switched the recommendation from `amd_iommu=off` to `iommu=pt` (Pass-Through mode).
> - **iommu=pt** keeps the IOMMU enabled for your hypervisor (KVM/Virtualization) but tells the kernel to skip the extra translation layer for host devices. This resolves the resume-from-sleep freezes without breaking virtualization or Docker.
> - **Docker Note**: Native Docker on Linux uses namespaces, not a hypervisor, so it is unaffected by this setting.

## Proposed Changes

### Power Management Configuration

#### [/etc/default/grub](file:///etc/default/grub)

- Add `iommu=pt` to resolve potential resume-from-S2idle hangs while maintaining virtualization support.
- Add `amdgpu.gttsize=131072` and `ttm.pages_limit=33554432` to optimize unified memory allocation for the AI Max+ 395 (optional but recommended by Framework for this platform).

```bash
# Target: GRUB_CMDLINE_LINUX_DEFAULT
GRUB_CMDLINE_LINUX_DEFAULT="quiet splash iommu=pt amdgpu.gttsize=131072 ttm.pages_limit=33554432"
```

---

### Diagnostic Setup

#### [NEW] [amd_s2idle_report.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/healing/amd_s2idle_report.py)

- Install the official AMD S2idle diagnostic script to verify if any specific hardware component (NVMe, USB4, GPU) is blocking the transition to the deepest sleep state.

---

## Verification Plan

### Automated Diagnostics
1. **Run S2idle Test**: 
   ```bash
   sudo python3 /home/mike-anderson/dev/cohezion/src/cohezion/healing/amd_s2idle_report.py
   ```
   This will perform a short suspend cycle and generate a detailed report on any blockers.

### Manual Verification
1. **Suspend/Resume Cycles**: 
   - Test suspend via UI (GNOME/KDE).
   - Test suspend via terminal: `systemctl suspend`.
2. **Log Inspection**:
   - Check `journalctl -b 0 | grep -i "s2idle"` for power state entry/exit.
   - Check `dmesg | grep -i amdgpu` for any "ring gfx timeout" or resume errors.
