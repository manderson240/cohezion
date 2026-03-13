---
type: antigravity-artifact
session_id: 2b962fe5-88c8-47ec-b20b-4c4911b5cae3
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.5
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# Walkthrough - GTK Backend Fix

## Goal
Resolve the "Desktop Icons NG is running under X11Wayland" warning by ensuring `GDK_BACKEND` is set to `wayland`.

## Changes
Renamed the existing environment configuration file to increase its priority, ensuring it overrides any system defaults.

- **Renamed**: `~/.config/environment.d/90-gdk-wayland.conf` -> `~/.config/environment.d/99-gdk-wayland.conf`

## Verification
1.  **File Content**: Confirmed that `99-gdk-wayland.conf` contains `GDK_BACKEND=wayland`.
2.  **Systemd Generator**: The `99-` prefix ensures this file is processed *after* any `90-` or lower priority files, effectively winning the configuration merge.

## Next Steps
> [!IMPORTANT]
> **A Logout/Login is required** for these changes to take effect.
> After logging back in, the warning should disappear.
