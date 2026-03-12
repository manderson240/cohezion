---
type: antigravity-artifact
session_id: 35739f48-2343-43cb-9de8-9ca31dd90876
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.330
  stage: embryo
  cluster: Agents
---

# Implementation Plan - Model Wrangler Roster Upgrade

The goal is to upgrade the `ModelWrangler` agent to actively manage a roster of "Tip of the Spear" Small Language Models (SLMs) suitable for the user's 12GB VRAM / 128GB RAM workstation.

## User Review Required

> [!IMPORTANT]
> **Model Downloads**: This plan includes logic to identifying and pulling new models via Ollama. Ensure you have the disk space (~20GB) for the proposed roster.

## Proposed Changes

### [Swarm] Model Wrangler Agent

#### [MODIFY] [model_wrangler_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/model_wrangler_agent.py)
- **Add `SLM_ROSTER` Constant**: Define the "Tip of the Spear" roster with roles.
    - **Reasoning**: `deepseek-r1:8b` (or 7b/8b variant) - High reasoning capability.
    - **Coding**: `qwen2.5-coder:7b` - SOTA coding SLM.
    - **Routing/Fast**: `phi4:mini` (3.8B) or `mistral:latest` - Efficient instruction following.
    - **Vision**: `minicpm-v` (optional, if available).
- **Update `__init__`**: Initialize with knowledge of this roster.
- **Add `deploy_roster()` method**: Logic to check if models exist (via `ollama list`) and pull them if missing (using `subprocess` or client).
- **Add `get_model_for_role(role)`**: Returns the best available model for a logical role.
- **Enhance `scout_sota_slms`**: Update the prompt to focus on 2026/late 2025 "Post-Transformer" or "Reasoning-First" architectures.

## Verification Plan

### Automated Tests
- **Config Test**: Verify `SLM_ROSTER` structure.
- **Mock Ollama**: Unit test `get_model_for_role` to ensure it returns defaults if primary is missing (or handles errors).

### Manual Verification
1.  **Run Wrangler**: Execute a script to instantiate `ModelWrangler`.
2.  **Check Roster**: Call `deploy_roster()` (simulated or real) and verify it identifies missing models.
3.  **Scout**: Run `scout_sota_slms()` and check the generated report.

## Related Vault Notes

- [[cohezion]]
