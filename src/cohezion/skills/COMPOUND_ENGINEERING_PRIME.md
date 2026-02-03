# SKILL: COMPOUND_ENGINEERING_PRIME

## DOMAIN EXPERTISE
Unified technical methodology for cross-platform agentic orchestration, local model optimization, and defensive intelligence (Hallucination Mitigation) within the Cohezion ecosystem.

## KEY TEXTS & CONCEPTS
- **Unified Configuration**: Centralizing shared parameters (compound_engineering, logging, performance) in standalone JSON blocks to avoid tool-specific schema conflicts.
- **MCP Bridge Topology**: Using the `cohezion-bridge` (`cohezion_mcp.py`) as the single source of truth for telemetry, model selection, and dynamic tool discovery across Gemini, IDE, and Claude environments.
- **Registry-Driven Swarm**: Dynamically configuring model rosters based on `model_registry.json` and verification of local availability.
- **Defensive Grounding**: The mandatory use of "Truth Anchors" and `HallucinationResolver` to prevent spec-attribution errors.
- **Offload Parity**: Ensuring menial tasks (docs, formatting) are always routed to local SLMs with a dedicated `ContextHarness`.

## INSTRUCTION
1. **Plan via Implementation Plan**: For all complex tasks, create a gated `implementation_plan.md` for user approval.
2. **Execute with Grounding**:
    - Consult `get_truth_anchors` for hardware/path vitals.
    - Check model availability via `ollama list` before assignment.
3. **Offload Menials**:
    - Identify supportive tasks (docstrings, READMEs).
    - Use `offload_task` or `BaseAgent.offload_to_local`.
4. **Verify & Walkthrough**:
    - Provide a concrete `walkthrough.md` with proof-of-work (command output, screenshots).
5. **Extract Wisdom**:
    - Update `KEY_LEARNINGS.md` with at least one 12D-encoded learning.
    - Update the relevant Retrospective.

## VERSION
v1.0

## SEE ALSO
- PERSISTENT_QUALITY_PRIME
- HALLUCINATION_RESOLVER_PRIME
- LOCAL_OFFLOAD_PRIME
- COHEZION_BRIDGE_PRIME
