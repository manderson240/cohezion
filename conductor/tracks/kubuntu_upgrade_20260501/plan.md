# Implementation Plan: Kubuntu 26.04 LTS Upgrade

## Phase 1: The Thinker (Pre-flight & Synchronization)
- [~] Task: Synchronize Code Repositories
    - [ ] Commit and push all pending changes in local Git repositories to remote origins.
    - [ ] Verify remotes are up-to-date.
- [ ] Task: Cloud Backup (Google Drive)
    - [ ] Identify critical non-repo data, Obsidian Knowledge Vault, and SurrealDB data files.
    - [ ] Copy/Sync data to Google Drive.
    - [ ] Verify successful upload of critical data.
- [ ] Task: Pre-flight System Checks
    - [ ] Verify `cgroup v2` is active (`stat -fc %T /sys/fs/cgroup/`).
    - [ ] Disable all 3rd-party PPAs in software sources.
    - [ ] Manually backup `/etc/default/grub`.
- [ ] Task: System Snapshot
    - [ ] Run Timeshift (or equivalent) to create a full system snapshot.
    - [ ] Verify snapshot integrity.
- [ ] Task: Conductor - User Manual Verification 'The Thinker (Pre-flight & Synchronization)' (Protocol in workflow.md)

## Phase 2: The Doer (In-place Upgrade)
- [ ] Task: Execute OS Upgrade
    - [ ] Run `sudo do-release-upgrade -d`.
    - [ ] Follow on-screen prompts, ensuring Kubuntu/KDE plasma packages are retained/upgraded.
    - [ ] Handle any GRUB or configuration conflicts (rely on backups if needed).
- [ ] Task: System Reboot
    - [ ] Reboot the system.
    - [ ] Verify successful boot into Kubuntu 26.04 LTS.
- [ ] Task: Conductor - User Manual Verification 'The Doer (In-place Upgrade)' (Protocol in workflow.md)

## Phase 3: The Knower (Optimization & Verification)
- [ ] Task: Hardware & Inference Optimization (Strix Halo)
    - [ ] Verify Kernel 6.18.4+ is active and UMA frame buffer is scaling.
    - [ ] Reinstall/verify AMDGPU firmware and ROCm 7.2.2+.
    - [ ] Configure Lemonade server for local inference with ROCm support.
    - [ ] Verify Ollama Cloud connectivity.
- [ ] Task: AI Agent & Database Restoration
    - [ ] Restore/verify SurrealDB functionality and data integrity.
    - [ ] Restore/verify Obsidian Knowledge Vault access.
    - [ ] Re-initialize and test Gemini CLI.
    - [ ] Re-initialize and test Claude Code.
    - [ ] Re-initialize and test Pi Agent.
    - [ ] Re-initialize and test Hermes Agent.
- [ ] Task: Final System Verification
    - [ ] Confirm KDE Plasma (Wayland) is stable.
    - [ ] Ensure general system stability and application functionality.
- [ ] Task: Conductor - User Manual Verification 'The Knower (Optimization & Verification)' (Protocol in workflow.md)