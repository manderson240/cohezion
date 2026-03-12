---
type: antigravity-artifact
session_id: bc8c627a-e74b-4b2a-8898-cea1e4bef4d4
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.405
  stage: growing
  cluster: Agents
---

# Remote Connection Walkthrough

I have audited the system and prepared a path for you to connect your Pixelbook to this Framework Desktop.

## Changes Made
- **Audit**: Identified active Tailscale tunnel and confirmed `sshd` and `chrome-remote-desktop` are installed but inactive.
- **Notification**: Sent a detailed connection guide to `manderson240@gmail.com` using the Cohezion `EmailNotifier`.
- **Guide Script**: Created [send_connection_guide.py](file:///home/mike-anderson/dev/cohezion/send_connection_guide.py) which was used to trigger the email.

## Connection Details
- **Tailscale IP**: `100.125.138.97`
- **User**: `mike-anderson`

## User Action Required
Due to `sudo` restrictions, I could not start the system services myself. Please run the following command on this desktop to enable remote access:

```bash
sudo apt update && sudo apt install -y openssh-server
sudo systemctl enable --now ssh
sudo systemctl unmask chrome-remote-desktop.service
sudo systemctl enable --now chrome-remote-desktop
sudo ufw allow ssh
```
 
- **Session Cleanup**: If you ever get "locked out" or see a conflict when logging in physically, I've created a safety script: [cleanup_sessions.sh](file:///home/mike-anderson/dev/cohezion/cleanup_sessions.sh).
  - Run `bash ~/dev/cohezion/cleanup_sessions.sh` to forcefully clear any orphaned remote sessions and give control back to the physical screen.

### 🖥️ Display & Quality Optimization

1.  **Which machine to change?**: Any changes to **Xorg**, **Resolution**, or **Settings** happen on your **Framework Desktop** (the remote machine), not the Pixelbook.
### 🐧 Linux-Native Access (Crostini)

Since you prefer the Linux approach on your Pixelbook, **Remmina** is the best client to use within Crostini.

1.  **Install Remmina** (Run this in your **Pixelbook Terminal**):
    ```bash
    sudo apt update
    sudo apt install -y remmina remmina-plugin-rdp
    ```
2.  **Connect**:
    - Launch Remmina from your app drawer.
    - Create a new connection profile.
    - **Protocol**: RDP
    - **Server**: `100.125.138.97`
    - **Username/Password**: Your Framework credentials.
    - **Color Depth**: "High Color (16bpp)" or "True Color (32bpp)" for best quality.
3.  **Scaling**: In Remmina, you can toggle "Toggle Scaled Mode" (look for the window-resize icon in the toolbar) to make the remote desktop fit your Pixelbook screen perfectly.

Once Remmina is set up, you'll have a native Linux experience with all the features of the Framework desktop mirrored onto your Pixelbook.

### 🚀 Full Connection Strings

Copy and paste these into your **Pixelbook Terminal** (Crostini):

#### 1. SSH (Terminal only)
```bash
ssh mike-anderson@100.125.138.97
```

#### 2. Remmina (Native GUI)
```bash
remmina -c rdp://mike-anderson@100.125.138.97
```

#### 3. Xfreerdp (Pro CLI)
```bash
# Try installing these specific packages
sudo apt update
sudo apt install -y freerdp2-x11 freerdp2-wayland

# Verify the command exists
which xfreerdp
```

### 🔄 The Best Way to Swap (Local vs Remote)

To move seamlessly between your desk and your Pixelbook, use this workflow:

1.  **Protocol**: Use **Ubuntu Built-in Remote Desktop** (RDP). It mirrors your physical session exactly.
2.  **Host State**: Stay logged in on the Framework desktop. If the screen locks, the remote session might go black.
3.  **The "Pixelbook" Toggle**:
    - When you connect from the Pixelbook, everything might look too big.
    - Run this command (remotely or via SSH):
      `bash ~/dev/cohezion/toggle_display.sh`
    - This will flip the desktop to **1080p**, making it perfect for the Pixelbook screen.
4.  **The "Back to Desk" Toggle**:
    - When you return to the Framework, run the same script again:
      `bash ~/dev/cohezion/toggle_display.sh`
    - It will flip back to **1440p (2K)** for your large monitor.

### 🛠️ Final "Black Screen" & Size Fixes
If you still see a black screen or everything is **too large**:
- **Fix Scaling**: Run `gsettings set org.gnome.desktop.interface text-scaling-factor 1.0` if everything looks massive (like 2x zoom).
- **Blank Screen**: Go to **Settings -> Privacy -> Screen** and disable "Blank Screen".
- **Sharing**: Ensure **Settings -> System -> Remote Desktop -> Desktop Sharing** is ON.
- **Xorg**: If it persists, log out and log back in selecting **"Ubuntu on Xorg"** (gear icon ⚙️ at login).

## Verification
- Connection guide email successfully sent to `manderson240@gmail.com`.
- `tailscale` status remains `active`.

## Related Vault Notes

- [[cohezion]]
