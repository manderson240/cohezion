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
v1.2

## LEARNED REFINEMENTS (2026-06-22)

Verified patterns from multi-agent development sessions. These were discovered by the insights + adversarial review loop and are now wired into CLAUDE.md:

### Agent Communication (Deferred Tool Pattern)
`SendMessage` is **not preloaded** — calling it directly raises `InputValidationError`. Always load first:
```python
ToolSearch(query="select:SendMessage")   # Step 1: loads schema
SendMessage(to="<name>", message="...")  # Step 2: now callable
```
Fallback when `ToolSearch` is unavailable (e.g. `code-reviewer` agent type): write structured report to `~/vaults/cohezion-vault/reports/YYYYMMDD-<slug>.md` and confirm path. Never loop retrying `SendMessage` without loading it.

### Filesystem Constraints (First-Error Pivot)
`~/.claude/` and git worktrees are often read-only. **Treat the first `permission denied` as the signal** — do not retry. Route the write to vault storage (`~/vaults/cohezion-vault/reports/`) immediately. If a worktree blocks commits, escape to the main checkout.

### Inference Port Consolidation
Port `:13305` is the Lemonade router — it serves the entire model catalog (NPU, iGPU, CPU) on demand. Dedicated per-port servers (13306, 13307, 13309) are redundant and often offline. Debug inference against `:13305` only.

### Spawnable Agent Types
See `### ⚡ Development Agent Routing` in CLAUDE.md for the full task→`subagent_type` routing table.

## SEE ALSO
- SKILL_SYNTHESIS_PRIME
- CROSS_PLATFORM_SKILL_FORMAT_PRIME
- PERSISTENT_QUALITY_PRIME
- HALLUCINATION_RESOLVER_PRIME
- LOCAL_OFFLOAD_PRIME
- COHEZION_BRIDGE_PRIME
- RETROSPECTIVE_SKILL
