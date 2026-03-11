---
type: antigravity-artifact
session_id: 0c888e0d-6061-443c-a927-3d908cbf0d85
date: 2026-03-04
title: "Root Cause Analysis and Guardrail Enhancement Plan"
tags: [agent-output, antigravity, root-cause-analysis, guardrails]
aspect: doer
neural:
  activation: 0.360
  stage: embryo
  cluster: Agents
---

# Root Cause Analysis and Guardrail Enhancement

The system became unresponsive due to **iGPU VRAM exhaustion (99.9% pressure detected)**. The existing emergency shutdown mechanism in `ResourceMonitor` failed to alleviate the pressure because it attempted to run `sudo systemctl stop ollama`, which required a password that wasn't provided in the automated context.

## Proposed Changes

### [Reliability Component]

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- **Restore 3-Tier Guardrail System**:
    - **Tier 1 (Warning, 80%)**: Logs warning and prepares checkpoints.
    - **Tier 2 (Throttle, 85%)**: Throttles new requests and increases wait times.
    - **Tier 3 (Emergency, 92%)**: Triggers `emergency_shutdown`.
- **Implement Robust AMD VRAM Monitoring**:
    - Specifically target `/sys/class/drm/card1/device/mem_info_vram_*` for the Framework 16 iGPU.
- **Fix Emergency Shutdown Logic**:
    - Move away from `sudo systemctl`.
    - **Non-Privileged Ollama Unload**: Use the Ollama HTTP API (`POST /api/generate` with `keep_alive: 0`) for all currently running models to free VRAM without requiring sudo.
    - **Process Pruning**: Continue killing runaway Python mission processes via `psutil`.

## Verification Plan

### Automated Tests
- **Monitor Stress Test**:
    - Run `python3 tests/automated/test_monitor_stress.py`.
    - I will update this test to ensure it correctly triggers the new non-privileged shutdown logic and verifies the VRAM paths.

### Manual Verification
1. I will trigger a Tier 3 event by mocking high VRAM usage and observe the logs to ensure the Ollama API is called and no `sudo` errors occur.
2. I will manually run `ollama ps` after a simulated Tier 3 shutdown to confirm models were unloaded.

## Related Vault Notes

- [[ai-safety]]
- [[cohezion]]
