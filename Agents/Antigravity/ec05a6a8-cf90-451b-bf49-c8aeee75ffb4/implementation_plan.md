---
type: antigravity-artifact
session_id: ec05a6a8-cf90-451b-bf49-c8aeee75ffb4
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.305
  stage: embryo
  cluster: Agents
---

# Fix GTK X11 Configuration

## User Review Required
> [!NOTE]
> I could not locate the specific file setting `GDK_BACKEND=x11` (checked `.bashrc`, `.profile`, etc.). The fix involves forcefully setting it to `wayland` using the standard systemd user environment configuration. This is the modern and correct way to configure session variables.

## Proposed Changes

### Configuration
#### [NEW] [90-gdk-wayland.conf](file:///home/mike-anderson/.config/environment.d/90-gdk-wayland.conf)
- Create directory `~/.config/environment.d/` if it doesn't exist.
- Create file with content:
  ```ini
  GDK_BACKEND=wayland
  ```

## Verification Plan

### Manual Verification
1.  **Restart Session**: You will need to log out and log back in (or reboot) for the changes to take effect.
2.  **Verify Variable**: Run `echo $GDK_BACKEND` in a terminal. It should output `wayland`.
3.  **Check Notification**: The "Desktop Icons NG" warning should disappear.
