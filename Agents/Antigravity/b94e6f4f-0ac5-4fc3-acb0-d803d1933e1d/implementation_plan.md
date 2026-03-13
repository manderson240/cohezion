---
type: antigravity-artifact
session_id: b94e6f4f-0ac5-4fc3-acb0-d803d1933e1d
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.51
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# Revert GDK_BACKEND to Default Ubuntu

Revert the `GDK_BACKEND` environment variable to its default state (unset) for Wayland sessions to fix the forced X11 backend warning in GTK applications.

## Proposed Changes

### Environment Configuration

#### [MODIFY] [systemd-user-env](systemctl --user unset-environment GDK_BACKEND)
Unset the `GDK_BACKEND` variable in the current `systemd` user session. This will stop passing the `x11` force to new processes like the GNOME shell extensions.

#### [MODIFY] [~/.profile](file:///home/mike-anderson/.profile)
Ensure that no manual exports of `GDK_BACKEND` are present. (Already verified as clean).

## Verification Plan

### Manual Verification
1. Run `systemctl --user show-environment | grep GDK_BACKEND` to confirm it is gone.
2. Restart the GNOME Shell (Alt+F2, `r`, Enter - or logout/login) and verify the "Desktop Icons NG" warning no longer appears.
3. Confirm that GTK applications (like `nautilus` or `gedit`) run natively on Wayland by checking `xlsclients` (they should not appear there) or using `GDK_BACKEND=wayland`.
