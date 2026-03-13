---
type: antigravity-artifact
session_id: 32e2fd59-f8f9-4b75-ae6b-4efe45e69c1d
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.52
  stage: embryo
  synapse_in: 0
  synapse_out: 0
---

# Walkthrough - Resolving Desktop Icons NG X11 Conflict

I have successfully identified and resolved the issue causing the "Desktop Icons NG is running under X11Wayland" warning.

## Changes Made

### Environment Configuration
I modified [.profile](file:///home/mike-anderson/.profile) to include a conditional check that unsets `GDK_BACKEND` if it is set to `x11` during a Wayland session.

```bash
# Fix for Desktop Icons NG X11/Wayland warning
if [ "$XDG_SESSION_TYPE" = "wayland" ] && [ "$GDK_BACKEND" = "x11" ]; then
    unset GDK_BACKEND
fi
```

This ensures that GTK applications can natively use the Wayland backend for better performance and to avoid the sub-optimal XWayland warning.

## Verification Results

### Path to Resolution
1.  **Discovery**: Identified that `GDK_BACKEND=x11` was being forced in the systemd user environment, likely by Chrome Remote Desktop initialization scripts (specifically `/opt/google/chrome-remote-desktop/chrome-remote-desktop`).
2.  **Implementation**: Added the conditional unset to `~/.profile` to ensure local Wayland sessions are not affected by this override.
3.  **Active Fix**: Manually ran `systemctl --user unset-environment GDK_BACKEND` to apply the fix to the current session.

### Environment Status
- **Current `GDK_BACKEND`**: Unset (correct for Wayland auto-detection).
- **Systemd Environment**: `GDK_BACKEND=wayland` (inherited from `~/.config/environment.d/99-gdk-wayland.conf`).

The Desktop Icons NG warning should no longer appear on subsequent logins or after restarting the session.
