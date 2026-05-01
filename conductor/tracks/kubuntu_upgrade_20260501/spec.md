# Specification: Kubuntu 26.04 LTS Upgrade & Inference Optimization

## Overview
This track details the safe, forced in-place upgrade (`-d` flag) of a system running Ubuntu/Kubuntu 24.04 LTS to Kubuntu 26.04 LTS (Resolute Raccoon) on a Framework Desktop. It includes strict requirements for preserving all local data, explicitly protecting the Obsidian Knowledge Vault and SurrealDB databases. The track leverages the official Kubuntu 26.04 release (incorporating KDE Plasma on Wayland) and mandates post-upgrade optimization for the Strix Halo hardware profile (AMD Ryzen AI MAX+ 395, Radeon 8060S iGPU, 128GB Unified Memory) utilizing a Lemonade server for local inference. It also mandates the restoration and verification of critical AI agent CLI environments.

## Functional Requirements
- **Code Synchronization:** All local code repositories must have their current state committed and pushed to remote origins before proceeding with the upgrade.
- **Cloud Backup:** All critical user data, configurations, and files not tracked in Git repositories must be backed up to Google Drive.
- **Critical Data Preservation:** Explicit backup procedures must be executed for the Obsidian Knowledge Vault and all SurrealDB instances/data files.
- **System Snapshot & Specific Backups:** The system must be fully backed up using an automated snapshot tool (e.g., Timeshift). A manual backup of `/etc/default/grub` is required due to a known 26.04 upgrade bug.
- **Pre-flight System Checks:**
  - Verify `cgroup v2` is active (`stat -fc %T /sys/fs/cgroup/` must return `cgroup2fs`).
  - Disable all 3rd-party PPAs to prevent calculation errors during the upgrade.
- **In-place Upgrade:** The upgrade process will utilize `do-release-upgrade -d` (development release forced upgrade) targeting the Kubuntu 26.04 release.
- **Desktop Environment:** The system must utilize the Kubuntu 26.04 default KDE Plasma Desktop Environment on Wayland.
- **Inference Powerhouse Optimization (Strix Halo):** Post-upgrade, the system must be optimized for the AMD Ryzen AI MAX+ 395 (Strix Halo) hardware profile:
  - Ensuring Kernel 6.18.4+ is active and dynamically scaling UMA up to ~112 GB.
  - Reinstalling/verifying the latest ROCm (7.2.2+) and AMDGPU firmware (`strix_halo*` blobs).
  - Configuring a `lemonade` server to manage local inference on the AMD hardware.
  - Re-establishing connections to Ollama Cloud for open-weight models.
- **AI Agent & Database Restoration:** Post-upgrade, the following services and CLIs must be restored, reconfigured if necessary, and verified to be fully operational:
  - Obsidian Knowledge Vault
  - SurrealDB
  - Gemini CLI
  - Claude Code
  - Pi Agent
  - Hermes Agent

## Non-Functional Requirements
- **Safety & Reversibility:** The upgrade process must include clear rollback procedures in case of kernel panic (7.0) or GRUB failure.
- **Downtime Minimization:** The upgrade should be performed in a manner that minimizes system unavailability.

## Acceptance Criteria
- [ ] All active code repositories are pushed to remote servers.
- [ ] Obsidian Vault, SurrealDB data, and other non-repo data are backed up to Google Drive.
- [ ] `/etc/default/grub` is manually backed up.
- [ ] `cgroup v2` is verified and 3rd-party PPAs are disabled.
- [ ] System snapshot (Timeshift) is created.
- [ ] `do-release-upgrade -d` successfully executes and the system reboots.
- [ ] Kubuntu 26.04 (KDE Plasma on Wayland) is the default desktop environment.
- [ ] Kernel 6.18.4+ and AMD ROCm 7.2.2+ are verified working with the 8060S iGPU.
- [ ] The Lemonade server utilizes the AMD GPU via ROCm for local inference.
- [ ] Connectivity to Ollama Cloud models is restored.
- [ ] Obsidian Vault and SurrealDB data are successfully restored and the services are functioning.
- [ ] Gemini CLI, Claude Code, Pi Agent, and Hermes Agent are fully functional.

## Out of Scope
- Hardware upgrades or physical disk replacement.
- Significant restructuring of the filesystem or partition layout.