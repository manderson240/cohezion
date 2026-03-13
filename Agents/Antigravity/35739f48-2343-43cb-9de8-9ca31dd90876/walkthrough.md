---
type: antigravity-artifact
session_id: 35739f48-2343-43cb-9de8-9ca31dd90876
date: 2026-03-04
title: "Walkthrough"
aspect: doer
neural:
  activation: 0.62
  stage: embryo
  synapse_in: 0
  synapse_out: 1
---

# Walkthrough - Model Wrangler Roster Upgrade

I have successfully upgraded the `ModelWrangler` agent to incorporate a "Tip of the Spear" roster of SOTA Small Language Models (SLMs) optimized for your 12GB VRAM environment.

## Changes

### `src/cohezion/swarm/agents/model_wrangler_agent.py`

I introduced a strictly typed `SLM_ROSTER` and role-based retrieval methods.

#### New SLM Roster
| Role | Model | Capability |
| :--- | :--- | :--- |
| **Reasoning** | `deepseek-r1:8b` | Chain-of-Thought, Logic |
| **Coding** | `qwen2.5-coder:7b` | SOTA Python/System Coding |
| **Routing** | `phi4:mini` | (3.8B) Extremely fast instruction following |
| **Vision** | `minicpm-v:latest` | Multimodal analysis |
| **Creative** | `mistral-nemo:12b` | Nuance (Conditional on VRAM) |

#### Key Methods Added
- `deploy_roster()`: Checks `ollama list` and flags missing models for pulling.
- `get_model_for_role(role)`: Returns the specialist model for a given task type.
- `scout_sota_slms()`: Updated prompt to look for 2026-era post-transformer architectures.

## Verification Results

### Manual verification Script (`test_model_wrangler_roster.py`)
I ran a test script to initialize the wrangler and query the roster status.

**Output Summary:**
- **Initialization**: Successful.
- **Roster Check**: Correctly identified missing models (since they haven't been pulled yet) or available ones.
- **Role Mapping**: confirmed `reasoning` -> `deepseek-r1:8b`, `coding` -> `qwen2.5-coder:7b`.

## Next Steps

> [!TIP]
> **Action Required**: The `ModelWrangler` is now aware of these models, but they may need to be pulled to your local Ollama instance.
> Run `ollama pull <model_name>` for the ones you want to activate immediately, or let the `ModelWrangler` manage it in future agentic loops.

## Related Vault Notes

- [[cohezion]]
