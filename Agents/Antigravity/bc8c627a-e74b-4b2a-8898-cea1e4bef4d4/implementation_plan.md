---
type: antigravity-artifact
session_id: bc8c627a-e74b-4b2a-8898-cea1e4bef4d4
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.318
  stage: embryo
  cluster: Agents
---

# Remote Connection Enablement Plan

The goal is to enable remote access to this desktop from the user's Pixelbook. Currently, Tailscale is active, but SSH and Chrome Remote Desktop (CRD) services are inactive.

## User Review Required

> [!IMPORTANT]
> I will attempt to start the SSH and Chrome Remote Desktop services. If these require `sudo` permissions that I don't have, I will provide the commands for you to run.
> Please confirm if you have a preferred PIN for Chrome Remote Desktop if it hasn't been set up yet.

## Proposed Changes

### System Configuration
- Install `openssh-server` if missing.
- Enable and start `ssh` service.
- Enable and start `chrome-remote-desktop` service.
- Configure `ufw` (firewall) to allow SSH connections.

### Notification
- Generate a connection guide including Tailscale IP and connection strings.
- Send this guide to the user's email using the `EmailNotifier` component.

## Verification Plan

### Automated Tests
- `systemctl is-active sshd`
- `systemctl is-active chrome-remote-desktop`

### Manual Verification
- Ask the user to try connecting via SSH from their Pixelbook terminal using the provided Tailscale IP.
- Ask the user to verify the Chrome Remote Desktop connection.
