---
name: compound-engineering
description: Compound AI orchestration methodology for multi-agent coordination,
  local model optimization, and hallucination mitigation. Use when implementing
  compound features, debugging coherence drift, setting up model routing, or
  when user mentions "compound engineering", "skill refinement", "orchestration loop", "compound
  impact", or treating each feature as a reusable macro for the next. For
  creating/scaffolding NEW skill files, see SKILL_SYNTHESIS_PRIME.
metadata:
  version: "1.1"
  legacy-name: COMPOUND_ENGINEERING_PRIME
---

# SKILL: COMPOUND_ENGINEERING_PRIME

## DOMAIN EXPERTISE
Unified technical methodology for cross-platform agentic orchestration, local model optimization, and defensive intelligence (Hallucination Mitigation) within the Cohezion ecosystem. The core stance is **self-extending engineering**: treat each feature as a reusable macro for the next, so every execution makes future tasks easier.

## KEY TEXTS & CONCEPTS
- **Unified Configuration**: Centralizing shared parameters (compound_engineering, logging, performance) in standalone JSON blocks to avoid tool-specific schema conflicts.
- **MCP Bridge Topology**: Using the `cohezion-bridge` (`cohezion_mcp.py`) as the single source of truth for telemetry, model selection, and dynamic tool discovery across Gemini, IDE, and Claude environments.
- **Registry-Driven Swarm**: Dynamically configuring model rosters based on `model_registry.json` and verification of local availability.
- **Defensive Grounding**: The mandatory use of "Truth Anchors" and `HallucinationResolver` to prevent spec-attribution errors.
- **Offload Parity**: Ensuring menial tasks (docs, formatting) are always routed to local SLMs with a dedicated `ContextHarness`.

## FUTURE HOOKS
- **Registry Integration**: Metadata hooks for `CapabilityRegistry` to suggest this skill in new contexts.
- **State Vector Feedback**: 12D state updates that inform system-wide "Compound Impact" scores.
- **Recursive Refinement**: Automated extraction of sub-skills via `RETROSPECTIVE_SKILL` (skill-creation mechanics live in `SKILL_SYNTHESIS_PRIME`).

## INSTRUCTION (Core Execution + Self-Improvement Loop)
1. **Plan via Implementation Plan**: For all complex tasks, create a gated `implementation_plan.md` for user approval.
2. **Execute with Grounding**:
    - Consult `get_truth_anchors` for hardware/path vitals.
    - Check model availability via `ollama list` before assignment.
3. **Seed the Future (Compound Engineering)**:
    - Every new skill/feature MUST include a `## FUTURE HOOKS` section.
    - List at least 3 ways this feature makes future tasks easier.
4. **Offload Menials**:
    - Identify supportive tasks (docstrings, READMEs).
    - Use `offload_task` or `BaseAgent.offload_to_local`.
5. **Verify & Walkthrough**:
    - Provide a concrete `walkthrough.md` with proof-of-work (command output, screenshots).
6. **Extract Wisdom**:
    - Update `KEY_LEARNINGS.md` with at least one 12D-encoded learning.
    - Increment the `compound_impact_score` in the `CapabilityRegistry`.

## VERSION
v1.1

## SEE ALSO
- SKILL_SYNTHESIS_PRIME
- CROSS_PLATFORM_SKILL_FORMAT_PRIME
- PERSISTENT_QUALITY_PRIME
- HALLUCINATION_RESOLVER_PRIME
- LOCAL_OFFLOAD_PRIME
- COHEZION_BRIDGE_PRIME
- RETROSPECTIVE_SKILL
