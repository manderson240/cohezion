---
type: antigravity-artifact
session_id: 735aa620-d836-44f9-ae9c-797a789b5c57
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.66
  stage: growing
  synapse_in: 0
  synapse_out: 0
---

# Crostini Recovery Plan

This plan outlines steps to diagnose and fix the Crostini terminal crash on your Pixelbook without resorting to a full Linux reset.

## User Review Required

> [!IMPORTANT]
> Some of these steps involve using the ChromeOS Developer Shell (`crosh`). Please follow the instructions carefully to avoid modifying other system settings.

> [!WARNING]
> If these steps fail, a "Remove and Re-enable Linux" might be necessary, which **will delete all files within the Linux container**. Ensure any critical data is backed up if you manage to get temporary shell access.

## Proposed Steps

### Phase 0: Environment Verification
Before running recovery commands, we must ensure you are in the correct shell. These commands **will not work** inside the Linux Terminal (penguin) or the Chrome Developer Shell; they must be run in `crosh`.

1. Open a new Chrome browser tab.
2. Press **Ctrl + Alt + T**.
3. You should see a prompt that looks exactly like this:
   ```text
   crosh>
   ```
4. If you see a different prompt (like `$` or `chronos@localhost`), please let me know what it displays.

### Phase 1: Forced Subsystem Restart
Once in `crosh`, we will force a stop of the Linux VM.

1. Run the following command to stop the VM:
   ```bash
   vmc stop termina
   ```
3. Run the following to start it manually and check for error codes:
   ```bash
   vmc start termina
   ```

### Phase 2: Manual Container Access
If the Terminal app crashes but the VM starts, we can bypass the UI and enter the container via a lower-level command.

1. In `crosh`, first verify your VM and container names:
   ```bash
   vmc list
   ```
2. Try starting the container directly:
   ```bash
   vmc container termina penguin
   ```
   *(Note: If you get an error that the container doesn't exist, wait 10 seconds and try again—this is a known timing bug).*

3. If that still fails, enter the VM shell first:
   ```bash
   vmc start termina
   ```
   **IMPORTANT**: If this works, your prompt will change to `(termina) chronos@localhost ~ $`. You are now **inside** the VM. `vmc` commands will no longer work here.

4. From the `(termina)` prompt, check your container status:
   ```bash
   lxc list
   ```
5. If `penguin` is "STOPPED", start it:
   ```bash
   lxc start penguin
   ```
6. Enter the container shell directly:
   ```bash
   lxc exec penguin -- /bin/bash
   ```

### Phase 3: Diagnostic Fixes (Inside Penguin)
Now that you have a shell (`lxc exec penguin -- /bin/bash`), let's find out why the UI is crashing.

1. **Test Shell Stability**:
   If your standard terminal crashes, it might be an error in your `.bashrc`. Try entering without loading it:
   ```bash
   bash --norc
   ```
   If this stays open, the issue is in your configuration files.

2. **Check Display Sockets**:
   Crostini uses `sommelier` to show windows. Check if the display sockets exist:
   ```bash
   ls -l /tmp/.X11-unix/
   ls -l $XDG_RUNTIME_DIR/wayland-0
   ```

3. **Check for "Zombies"**:
   Look for old processes from your remote desktop attempt that might be hung:
   ```bash
   ps aux | grep -i "remote\|chrome\|vnc\|rdp"
   ```

4. **Clear Tmp Files**:
   Since you have space, let's clear potential lock file issues:
   ```bash
   sudo rm -rf /tmp/.X*
   ```

5. **Check Linux Logs**:
   Look for recent errors that happened when you tried to open the Terminal app:
   ```bash
   sudo journalctl -t sommelier -n 50
   ```

### Phase 4: User Configuration Check
Since the root shell is stable, the issue is likely in your user-specific configuration (`/home/manderson240/.bashrc`).

1. **Test User Shell**:
   From your current `#` prompt, try switching to your actual user:
   ```bash
   su - manderson240
   ```
   *If this crashes or exits immediately, your `.bashrc` or `.profile` is the culprit.*

2. **Inspect .bashrc**:
   If the switch above failed, go back to the root shell and look at the end of the user's config:
   ```bash
   tail -n 20 /home/manderson240/.bashrc
   ```
   Look for any lines related to `export DISPLAY`, `remmina`, `vnc`, or `chrome-remote-desktop`.

3. **Temporary Bypass**:
   Rename the config to see if the Terminal app starts with a default one:
   ```bash
   mv /home/manderson240/.bashrc /home/manderson240/.bashrc.bak
   ```
   Now try opening the **Terminal app** from the ChromeOS launcher.

### Phase 6: Forced Reset (The "Clean Slate" Method)
Since `lxc exec` is having parsing and "no medium" errors, the container's disk is likely in a locked state. Let's do a clean reset of the entire Virtual Machine.

1. **Exit the (termina) prompt**:
   Type `exit` until you are back at the `crosh>` prompt.

2. **Nuclear Shutdown**:
   This kills the entire VM and all hung processes:
   ```bash
   vmc stop termina
   ```

3. **Verify it is stopped**:
   Ensure `vmc list` shows it as stopped or not running.

4. **Restart & Check Container Status**:
   ```bash
   vmc start termina
   # Once at the (termina) prompt:
   lxc list
   ```

5. **Manual Repair (If "No Medium Found" persists)**:
   If you still see errors, try this inside the `(termina)` prompt to fix the filesystem:
   ```bash
   lxc start penguin
   # If it fails to start, try:
   lxc storage info default
   ```

### Phase 7: Final Cleanup & Disabling Autostart
Now that the container is running, let's make sure it stays clean.

1. **Check for orphans manualy**:
   ```bash
   lxc exec penguin -- ps aux
   ```
   *Look for anything with "remmina", "vnc", "chrome", or "remote".*

2. **Force-kill any survivors**:
   ```bash
   lxc exec penguin -- pkill -9 remmina
   lxc exec penguin -- pkill -9 chrome-remote-desktop
   lxc exec penguin -- pkill -9 vnc
   ```

3. **Disable the Autostart Loop**:
   This is the most important step to prevent it from happening again. We will rename the autostart folder.
   ```bash
   lxc exec penguin -- mv /home/manderson240/.config/autostart /home/manderson240/.config/autostart.bak
   ```

4. **Clear Display Locks**:
   ```bash
   lxc exec penguin -- rm -f /tmp/.X11-unix/X0
   lxc exec penguin -- rm -f /tmp/.X0-lock
   ```

5. **Verify stability**:
   Open a fresh **Terminal app** window from the ChromeOS launcher. It should stay open now without trying to connect to the Framework.
