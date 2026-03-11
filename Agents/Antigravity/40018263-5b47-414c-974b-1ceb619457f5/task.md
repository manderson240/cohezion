---
type: antigravity-artifact
session_id: 40018263-5b47-414c-974b-1ceb619457f5
date: 2026-03-04
title: "Task"
aspect: doer
neural:
  activation: 0.314
  stage: embryo
  cluster: Agents
---

# Task: Resolve Sleep-Wake Freeze on Framework Desktop (Refocused)

## Research and Diagnosis
- [x] Gather detailed system specifications (Hardware: Strix Halo AI Max+ 395) <!-- id: 0 -->
- [x] Research latest BIOS and kernel parameters for Strix Halo (Browser) <!-- id: 1 -->
- [x] Draft Implementation Plan (implementation_plan.md) <!-- id: 3 -->

## Implementation and Execution
- [x] Seek user approval and execute changes <!-- id: 4 -->
- [x] Update BIOS/Firmware (User confirmed latest: 3.04) <!-- id: 5 -->
- [x] Update GRUB (iommu=pt and memory limits) <!-- id: 6 -->
- [x] Clean up redundant lid settings for desktop <!-- id: 11 -->

## Desktop Configuration
- [ ] Resolve GTK X11/Wayland mismatch (Desktop Icons NG) <!-- id: 12 -->
	- [ ] Verify XDG_SESSION_TYPE and GDK_BACKEND <!-- id: 13 -->
	- [ ] Locate and remove "force X11" configuration in /etc/environment or dotfiles <!-- id: 14 -->
	- [ ] Verify fix by launching GTK apps natively on Wayland <!-- id: 15 -->
