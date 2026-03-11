---
type: antigravity-artifact
session_id: 7fb808c0-81bf-4a4e-872d-7b712e508ad1
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.336
  stage: embryo
  cluster: Agents
---

# System Hardening & Multi-Tier Resource Safeguards

The system recently suffered a full lockup requiring a hard reboot (REISUB). This indicates that the current 98% emergency shutdown threshold in `ResourceMonitor` is either too late or the "ring reset" happens before the monitor can react. We need a proactive, multi-tiered defense.

## User Review Required

> [!WARNING]
> This plan involves modifying process priority (`oom_score_adj`) and stopping the `ollama` service automatically under high pressure. This may interrupt active model inferences but is necessary to prevent total system stalls.

## Proposed Changes

### Reliability Layer

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- Refactor `_heartbeat_loop` to use a 3-tier threshold system:
  - **85% (Warning)**: Log warnings and start proactive checkpointing.
  - **90% (Throttling)**: Halt new LLM slot acquisition and increase sleep duration.
  - **95% (Pruning)**: Trigger `emergency_shutdown` (currently at 98%).
- Enhance `emergency_shutdown` to target `ollama` and `python` processes more aggressively.
- Add `set_process_priority()` to lower the OOM score for critical system components (e.g., SurrealDB) and increase it for "expendable" agents.

---

### Healing Layer

#### [MODIFY] [immune_system.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/healing/immune_system.py)
- Integrate hardware vitals (from `ResourceMonitor.get_vitals()`) into the `VelocityMonitor`.
- Trigger `SelfDiagnostic` not just on low task velocity, but also on hardware pressure spikes.

---

### Workflow Enhancements

#### [MODIFY] [harden.md](file:///home/mike-anderson/dev/cohezion/.agent/workflows/harden.md)
- Add steps to verify `oom_score_adj` application.
- include `sysctl` tweaks for `vm.swappiness` and `vm.vfs_cache_pressure` to optimize for 128GB RAM.

## Verification Plan

### Automated Tests
- Run `tests/automated/test_monitor_stress.py` (to be created) which mocks high system pressure and verifies that `ResourceMonitor` triggers the correct tier response.
- `python -m cohezion.reliability.monitor` (demo mode) to verify vitals reading.

### Manual Verification
- Run a heavy local model (e.g., DeepSeek-70b) and monitor `logs/system_heartbeat.log` to see if throttling kicks in at 90%.
