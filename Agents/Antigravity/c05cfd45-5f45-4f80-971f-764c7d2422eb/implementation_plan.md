---
type: antigravity-artifact
session_id: c05cfd45-5f45-4f80-971f-764c7d2422eb
date: 2026-03-04
title: "Implementation Plan"
aspect: doer
neural:
  activation: 0.334
  stage: embryo
  cluster: Agents
---

# Mission: Compound Engineering & Adaptive Templates

Extract reusable architecture patterns from the Swarm Research Relay into standardized "compounds" and adaptive templates to accelerate future Gateway milestones.

## User Review Required

> [!NOTE]
> This mission focuses on **Metaprogramming** and **Architecture Extraction**. No functional logic will change in the existing agents, but they will be refactored to use standardized base patterns.

---

## Proposed Changes

### Swarm Framework Extraction

#### [NEW] [SWARM_ORCHESTRATION_PRIME.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/SWARM_ORCHESTRATION_PRIME.md)

Detailed skill document defining:
- LangGraph Orchestration standard
- Fan-out (Expert Lattice) patterns
- Async Agent Lifecycle management

#### [NEW] [MEMORY_PERSISTENCE_PRIME.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/MEMORY_PERSISTENCE_PRIME.md)

Distilled skill for:
- `SESSION_SNAPSHOT` synthesis
- Vector-based context recovery (MRP)
- SurrealDB standard node schemas

---

### Adaptive Templates

#### [NEW] [agent_template.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/templates/agent_template.py)

A "ready-to-ignite" template for new expert agents, pre-wired with:
- `BaseAgent` inheritance
- `SYSTEM_PROMPT` structure
- Journey narration and credit management hooks

#### [NEW] [controller_template.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/templates/controller_template.py)

A boilerplate for LangGraph controllers with:
- Standard `AgentState`
- Router/Classifier nodes
- Handoff edge pre-configured

---

### Refactoring & Registry

#### [MODIFY] [capability_registry.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/registry/capability_registry.py)

- Increment `compound_impact_score` for swarm-related components.
- Link new skills to existing agents.

#### [MODIFY] [KEY_LEARNINGS.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md)

- Add Learning 36: **Architectural Liquidity via Templating**.
- Add Learning 37: **The Expert Lattice Fan-out Pattern**.

---

## Verification Plan

### Automated Tests
1. **Lint & Type Check**: Ensure new templates are syntactically valid.
   ```bash
   uv run mypy src/cohezion/templates/agent_template.py
   ```
2. **Registry Audit**: Run `populate_registry.py` to ensure new skills are picked up.

### Manual Verification
1. **Template Dry Run**: Create a dummy "PhysicsAnalyst" agent using the template and verify it "ignites" without errors.
2. **Skill Review**: Verify the new `.md` skills render correctly in the IDE/Walkthrough.
