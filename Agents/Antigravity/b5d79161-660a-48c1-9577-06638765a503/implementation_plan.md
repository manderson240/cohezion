---
type: antigravity-artifact
session_id: b5d79161-660a-48c1-9577-06638765a503
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.324
  stage: embryo
  cluster: Agents
---

# Mission: Infinity and Beyond (Adversarially Hardened)

This mission launches the **Transcendence Mission** and scales swarm simulations, with critical hardening to prevent **Router Sovereignty** and **Dilation Traps** identified in Learning 90.

## User Review Required

> [!IMPORTANT]
> This plan now includes a fundamental shift in how the `LocalExpertRouter` handles intent. It will no longer override agent-specified models, preventing OOM events during high-concurrency periods.

## Proposed Changes

---

### Swarm & Evolution

#### [MODIFY] [router.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/core/routing/router.py)
- **Intent Preservation**: Update `route_task` to prioritize `context.get("force_model")` over internal selection.
- **Lightweight Tiers**: Add `light-reasoning` (phi4:mini) and `light-coding` (qwen3-coder:7b) for rapid verification.
- **Dilation Hardening**: Force legacy/mini models when `dilation < 0.5` regardless of RAM availability.

#### [MODIFY] [base.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/agents/base.py)
- **Explicit Override**: Update `_call_ollama` to pass the agent's `model_name` as `force_model` to the router.
- **Multimodal Toggle**: Respect `COHEZION_DISABLE_MULTIMODAL` environment variable.

#### [NEW] [transcendence_mission.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/transcendence_mission.py)
- Wrapper to run `TranscendenceAgent` in a loop.
- Uses `light-reasoning` for identification phases to save VRAM.

#### [MODIFY] [tsunami_simulator.py](file:///home/mike-anderson/dev/cohezion/scripts/drivers/tsunami_simulator.py)
- Scale to 10M epochs with dynamic dilation support.

---

### Infrastructure

#### [MODIFY] [engine.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/universe/engine.py)
- Bypass async asset scheduling if `COHEZION_DISABLE_MULTIMODAL` is active.

## Verification Plan

### Automated Tests
- `uv run scripts/test_router_sovereignty.py`: Verifies that `force_model` is respected.
- `uv run scripts/test_dilation_guard.py`: Simulates 0.05 dilation and verifies model downscaling.

### Manual Verification
- Execute `COHEZION_DISABLE_MULTIMODAL=true uv run scripts/drivers/transcendence_mission.py` and monitor `htop`.

## Related Vault Notes

- [[cohezion]]
