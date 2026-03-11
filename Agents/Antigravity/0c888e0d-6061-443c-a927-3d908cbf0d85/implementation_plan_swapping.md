---
type: antigravity-artifact
session_id: 0c888e0d-6061-443c-a927-3d908cbf0d85
date: 2026-03-04
title: "Implementation Plan Swapping"
aspect: doer
neural:
  activation: 0.316
  stage: embryo
  cluster: Agents
---

# Dynamic Model Swapping and Priority Slots

This phase implements hierarchical resource management for local SLMs. It ensures that "Critical" agents (Strategist, Controller) can proactively evict "Scout" or "Wrangler" models from VRAM when the system is under pressure.

## Proposed Changes

### [Swarm Core]

#### [MODIFY] [swarm_types.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/swarm_types.py)
- Add `priority: int = 3` to `SwarmConfig`.

#### [MODIFY] [base.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/base.py)
- Use `self.priority` from config.
- Update `_call_ollama` to optionally call a resource preparation hook.

### [Management Layer]

#### [MODIFY] [model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- Add `PRIORITY_MAP` defining hierarchical urgency (1=Critical, 4=Low).
- Implement `prepare_resources_for_priority(priority: int)`:
    - If VRAM is tight (>70%) and requested priority is high (<3), evict lower priority models first.
    - Use the non-privileged `keep_alive: 0` strategy.

### [Reliability Layer]

#### [MODIFY] [monitor.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/monitor.py)
- Expose a method to unload specific models rather than just "all".

## Verification Plan

### Automated Tests
- Create `tests/automated/test_priority_eviction.py`.
- Simulate high VRAM load with "Scout" models and verify that requesting a "Strategist" model triggers proactive unloading of the scouts.

### Manual Verification
- Observe VRAM logs in `system_heartbeat.log` during a simulated handover between agents of different priorities.
