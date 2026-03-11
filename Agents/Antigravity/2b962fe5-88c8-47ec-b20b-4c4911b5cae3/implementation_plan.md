---
type: antigravity-artifact
session_id: 2b962fe5-88c8-47ec-b20b-4c4911b5cae3
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.327
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Resolve GTK Backend Mismatch

The user is experiencing a "Desktop Icons NG is running under X11Wayland" warning due to `GDK_BACKEND` being forced to `x11` in a Wayland session.

## User Review Required

> [!IMPORTANT]
> I have confirmed `GDK_BACKEND=x11` is active in your environment, but standard configuration files (`.bashrc`, `.profile`, `/etc/environment`) **do not** contain this setting.
> Use `notify_user` to ask if you have any custom scripts or "dotfiles" management systems that might be injecting this variable.

## Proposed Changes

### Configuration
I will attempt to override the setting using `systemd` user environment configuration, which is the standard way to configure the session environment in GNOME.

#### [MODIFY] [90-gdk-wayland.conf](file:///home/mike-anderson/.config/environment.d/90-gdk-wayland.conf)
- Rename to `99-gdk-wayland.conf` to ensure highest priority.
- Ensure content is `GDK_BACKEND=wayland`.

#### [NEW] [unset-x11-backend.sh](file:///home/mike-anderson/.config/profile.d/unset-x11.sh)
- If renaming doesn't work, I may need to create a profile script to explicitly unset it, though this is a fallback.

### Verification Plan

Since I cannot reboot the user's machine, I will verify by:
1.  Running `systemd-analyze --user environment-d-generator` to confirm the generator output is correct and prioritized.
2.  Checking `printenv` in a new shell (simulated) to see if the environment propagates.
3.  Asking the user to log out and log back in to apply changes.

## Manual Verification
- User should log out/in.
- Verify the "Desktop Icons NG" warning is gone.
- Run `echo $GDK_BACKEND` in a terminal; it should be `wayland` or empty.
