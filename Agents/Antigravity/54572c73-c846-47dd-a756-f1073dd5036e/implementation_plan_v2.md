---
type: antigravity-artifact
session_id: 54572c73-c846-47dd-a756-f1073dd5036e
date: 2026-03-04
title: "Implementation Plan V2"
aspect: doer
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 0
  synapse_out: 2
---

# Compound Engineering Enhancements: Telemetry, Selection, and Skills

This plan covers the next three major steps in the compound engineering evolution: adding real-time telemetry to the MCP bridge, integrating the model registry into `ModelWrangler`, and enabling dynamic skill discovery via MCP.

## Proposed Changes

### 1. Enhanced Telemetry (MCP Bridge)

#### [MODIFY] [cohezion_mcp.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/cohezion_mcp.py)
- Import `ResourceMonitor` from `cohezion.reliability.monitor`.
- Update `get_compound_config` to include real-time VRAM and RAM vitals.
- Ensure the JSON-RPC loop handles the overhead of importing these modules.

### 2. Dynamic Model Loading (ModelWrangler)

#### [MODIFY] [model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- Load `model_registry.json` on initialization.
- Refactor `get_model_for_role` to use the registry instead of the static `SLM_ROSTER`.
- Update `prepare_resources_for_priority` to be more granular based on the memory limits defined in the registry.

### 3. Dynamic Skill Registration (MCP Bridge)

#### [MODIFY] [cohezion_mcp.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/cohezion_mcp.py)
- Update `list_tools` to dynamically scan the `skill_registry.json`.
- Export each registered skill as a top-level MCP tool.
- Implement `call_tool` logic to route these dynamic tool calls to `execute_skill`.

## Verification Plan

### Automated Tests
- Call `gemini list-tools` to verify that skills are listed as tools.
- Call `gemini execute cohezion-bridge get_compound_config` and verify that `vitals` are present.
- Unit test `ModelWrangler.get_model_for_role` with mock registry data.

### Manual Verification
- Check Antigravity IDE tool list for the newly exported skills.

## Related Vault Notes

- [[cohezion]]
- [[compound-engineering]]
