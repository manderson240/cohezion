---
type: antigravity-artifact
session_id: ec05a6a8-cf90-451b-bf49-c8aeee75ffb4
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.307
  stage: embryo
  cluster: Agents
---

# Walkthrough: Fixing GTK X11/Wayland Configuration

## Changes
I investigated why your system was forcing GTK applications to use the X11 backend on Wayland, which caused the "Desktop Icons NG" warning.

While I couldn't find the specific configuration file that was setting `GDK_BACKEND=x11` (it wasn't in standard locations like `.bashrc` or `.profile`), I applied a robust override using systemd's user environment configuration.

### Created Configuration
#### [NEW] [90-gdk-wayland.conf](file:///home/mike-anderson/.config/environment.d/90-gdk-wayland.conf)
```ini
GDK_BACKEND=wayland
```

## Verification Results

### Automated Verification
- [x] Confirmed file creation and content:
  ```bash
  $ cat /home/mike-anderson/.config/environment.d/90-gdk-wayland.conf
  GDK_BACKEND=wayland
  ```

### Manual Verification Required
You will need to **log out and log back in** (or restart your computer) for this change to take effect system-wide.

After restarting:
1.  The "Desktop Icons NG" warning should be gone.
2.  Running `echo $GDK_BACKEND` in a terminal should output `wayland`.
