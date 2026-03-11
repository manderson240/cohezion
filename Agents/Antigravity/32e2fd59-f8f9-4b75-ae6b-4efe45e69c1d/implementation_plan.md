---
type: antigravity-artifact
session_id: 32e2fd59-f8f9-4b75-ae6b-4efe45e69c1d
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.326
  stage: embryo
  cluster: Agents
---

# Resolution of Desktop Icons NG X11/Wayland Conflict

The system is currently forcing `GDK_BACKEND=x11` even in Wayland sessions, likely due to a Chrome Remote Desktop configuration. This causes GTK applications like Desktop Icons NG (DING) to run under XWayland, which is suboptimal and triggers a warning.

## Proposed Changes

### User Environment Configuration
#### [MODIFY] [.profile](file:///home/mike-anderson/.profile)
Add a conditional block to unset `GDK_BACKEND` when running in a Wayland session. This ensures that the default behavior (automatic backend selection) is restored for local sessions while allowing remote sessions that specifically set it to continue working.

```bash
# Fix for Desktop Icons NG X11/Wayland warning
if [ "$XDG_SESSION_TYPE" = "wayland" ] && [ "$GDK_BACKEND" = "x11" ]; then
    unset GDK_BACKEND
fi
```

#### [MODIFY] [.config/environment.d/99-gdk-wayland.conf](file:///home/mike-anderson/.config/environment.d/99-gdk-wayland.conf)
Ensure this file exists and contains `GDK_BACKEND=wayland` (verified as already present, but will ensure it's properly recognized).

## Verification Plan

### Automated Verification
1.  **Environment Check**:
    ```bash
    systemctl --user unset-environment GDK_BACKEND
    # Restart session or source .profile
    echo $GDK_BACKEND
    ```
    Expected: Output should be empty or `wayland` in a native Wayland terminal.

2.  **DING Status**:
    Check if the warning window still appears upon login or when restarting DING.

### Manual Verification
1.  Log out and log back in to the local Wayland session.
2.  Confirm that the "Desktop Icons NG" warning does not appear.
3.  (Optional) Verify that Chrome Remote Desktop still works as expected (if used).
