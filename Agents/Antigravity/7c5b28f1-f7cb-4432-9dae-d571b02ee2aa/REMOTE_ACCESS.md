---
type: antigravity-artifact
session_id: 7c5b28f1-f7cb-4432-9dae-d571b02ee2aa
date: 2026-03-04
title: "Remote Access"
aspect: doer
neural:
  activation: 0.345
  stage: embryo
  cluster: Agents
---

# 🌐 Cohezion Remote Access Guide: Pixelbook Setup

This guide provides instructions for connecting to the Cohezion Platform (Framework Desktop 16) from a Pixelbook or any other secondary device.

## 🛡️ Recommended Architecture: Tailscale

Tailscale is the recommended solution for secure, zero-config mesh networking. It allows you to access your desktop as if it were on the local network, regardless of your location.

### 1. Host Setup (Framework Desktop)
1. Install Tailscale:
   ```bash
   curl -fsSL https://tailscale.com/install.sh | sh
   sudo tailscale up
   ```
2. Note the Tailscale IP of your host (e.g., `100.x.y.z`).

### 2. Client Setup (Pixelbook)
1. Install the Tailscale Android app (from Play Store) or use the Linux (Crostini) client.
2. Sign in with the same account.
3. Your Pixelbook can now "see" the Framework Desktop at its Tailscale IP.

---

## 💻 Working Remotely

### Terminal Access (SSH)
From the Pixelbook's Linux terminal:
```bash
ssh mike-anderson@100.125.138.97
```

#### 🛠 Troubleshooting: "Connection Refused"
If you see `Connection Refused`, the SSH server is likely not installed on the host. Run this on your Framework:
```bash
sudo apt update && sudo apt install openssh-server -y
sudo systemctl enable --now ssh
```

#### What is `tmux`?
`tmux` is a tool that keeps your code running even if your laptop closes or disconnects.
- **Install**: `sudo apt install tmux`
- **Start**: `tmux new -s cohezion`
- **Detach**: Press `Ctrl+B`, then `D`.
- **Reattach**: `tmux attach -t cohezion`

### 📊 Marimo Dashboard (Universe Explorer)
I have started the dashboard for you! Access it on your Pixelbook browser at:
`http://100.125.138.97:8765`

*Note: Verified connectivity from Docker simulation.*

---

## 🎙️ Narration Playback
Narrations are persisted as text files in `audio/narrations/`.
- **Away from Desk**: You can `cat` these files over SSH or sync them using `scp` / `rsync`.
- **Audio Stream**: For live audio streaming over SSH, consider using `PulseAudio` network sinks or `ssh -X` with `espeak` (though bandwidth may be limited).

---
*Status: Connectivity Enabled. Sovereignty Maintained.*

## Related Vault Notes

- [[cohezion]]
