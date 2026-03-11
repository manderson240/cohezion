---
type: antigravity-artifact
session_id: edda7e8b-cc35-4fea-83de-92780bce719d
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.359
  stage: embryo
  cluster: Agents
---

# Implementation Plan: Swap Optimization (ZFS Native Approach)

The objective is to establish a reliable 32GB safety buffer for high-density AI workloads on a **ZFS-based Framework 16** (running Kernel 6.14).

## Deep System Analysis (Research-Based)

### Why previous attempts failed:
The system uses **ZFS** (`rpool`) with **lz4 compression**.
1.  **Copy-on-Write (COW)**: ZFS is a COW filesystem. Any file created within it (even via `dd`) is managed by ZFS's block allocation logic.
2.  **Compression & Sparseness**: When we wrote zeros to create the swap file, ZFS's `lz4` compression turned those blocks into virtually nothing on disk.
3.  **Kernel Limitation**: The Linux swap subsystem requires a contiguous, non-sparse block allocation. When it sees ZFS's compressed/COW blocks, it reports "holes," making the file unusable for swap.

### The Proposed Technical Solution: ZVOL
On ZFS, the native way to provide block storage for swap is a **ZVOL** (ZFS Volume).
-   **Direct Block Access**: A ZVOL creates a `/dev/zvol/...` block device that bypasses the dataset filesystem logic.
-   **No Holes**: Blocks are allocated specifically for the volume, satisfying the kernel's requirements.

## Safety & Stability Analysis

| Risk | Mitigation Strategy |
| :--- | :--- |
| **ZFS Deadlock** | We will set `primarycache=metadata` and `secondarycache=none` on the ZVOL. This prevents ZFS from trying to cache swap pages in RAM, which otherwise could cause a "memory-needed-to-free-memory" deadlock. |
| **I/O Pressure** | We've already tuned `vm.watermark_scale_factor=200` to ensure the kernel starts cleaning RAM before getting into a "panic" state. |
| **Pool Space** | Verified **1.3TB available** on `rpool`. A 32GB ZVOL is <3% of available space. |

## Proposed Implementation Steps

### 1. Create ZFS Volume (ZVOL)
```bash
# Create a 32GB volume with optimizations for swap
zfs create -V 32G -b $(getconf PAGESIZE) \
    -o compression=off \
    -o logbias=throughput \
    -o sync=always \
    -o primarycache=metadata \
    -o secondarycache=none \
    rpool/swap_cohezion
```

### 2. Initialize and Enable
```bash
mkswap /dev/zvol/rpool/swap_cohezion
swapon /dev/zvol/rpool/swap_cohezion
```

### 3. Verification Commands
- `zfs list rpool/swap_cohezion` (Confirm existence)
- `swapon --show` (Confirm activation)

## User Review Required

> [!IMPORTANT]
> **ZVOL swap is the industry standard for ZFS systems** (like Proxmox or Ubuntu with ZFS), but it does require 32GB of your 1.3TB pool space to be reserved. 

> [!NOTE]
> I have updated the `scripts/setup/tune_system.sh` script to handle this logic gracefully, including cleanup of the failed file.

**Should I proceed with the ZVOL implementation?**
