---
type: antigravity-artifact
session_id: 54572c73-c846-47dd-a756-f1073dd5036e
date: 2026-03-04
title: "Implementation Plan V4"
aspect: doer
neural:
  activation: 0.322
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Local Offload & Context Harnessing

This plan introduces a formal mechanism for offloading "menial" tasks to local SLMs with a dedicated context-optimization harness, ensuring high fidelity and token efficiency.

## Proposed Changes

### [Component] Reliability Layer
#### [NEW] [context_harness.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/context_harness.py)
A utility class to:
- **Prune Context**: Intelligently truncate or summarize non-essential data.
- **Anchor Truth**: Integrate `HallucinationResolver` truth anchors.
- **Specialize Prompt**: Apply instruction-following templates for specific SLMs (e.g., Phi-4-mini).

#### [NEW] [offload_manager.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/reliability/offload_manager.py)
A manager to classify tasks as "menial" (documentation, formatting, simple summaries) vs "complex" (logic, architecture).

### [Component] Swarm Agents
#### [MODIFY] [base.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/base.py)
Add `offload_to_local` method:
- Uses `OffloadManager` to verify task type.
- Uses `ContextHarness` to prepare the payload.
- Directly invokes `_call_ollama` with the optimized harness.

### [Component] MCP Bridge
#### [MODIFY] [cohezion_mcp.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/cohezion_mcp.py)
Expose a new MCP tool: `offload_task`.
- Allows external agents (like Gemini CLI) to delegate menial background tasks to the local swarm.

## Verification Plan

### Automated Tests
- Create a test script that offloads a documentation task and verifies it succeeds locally without premium API calls.
- Verify `ContextHarness` correctly truncates a 100k-character context to fit a target SLM's sweet spot.

### Manual Verification
- Review the "Harnessed" prompt and ensure it retains all "Truth Anchors".

## Related Vault Notes

- [[cohezion]]
- [[token-efficiency]]
