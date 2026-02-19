# GEMINI.md - Cohezion Orchestration Layer

This document serves as the primary orchestration hub for AI agents in the Cohezion project. It establishes our core identity and maps out specialized context modules.

## 1. Core Project Identity

**COHEZION** is a systemic AI orchestration ecosystem governed by the **Quadrature Nexus Orchestration** and **Hermetic Compound Engineering** ("As Above, So Below"). We implement the **FLUME** methodology combined with **JEPA-aligned World Models** for high-fidelity simulation, autonomous research, and value precipitation via **UCP/MCP**.

## 2. The Cohezion Constitutional Framework

All agent actions are governed by two primary documents:

- **Core Constitution**: [.agent/CONSTITUTION.md](file:///home/mike-anderson/dev/cohezion/.agent/CONSTITUTION.md) (January 2026 Claude Edition).
- **Project Charter**: [.agent/COHEZION_CHARTER.md](file:///home/mike-anderson/dev/cohezion/.agent/COHEZION_CHARTER.md) (Simulation, SWARM, FLUME, HIHO, SPIN).
- **Strategic Roadmap**: [STRATEGIC_ROADMAP_PRIME.md](file:///home/mike-anderson/.gemini/antigravity/brain/2a476f70-c770-4044-8d44-e6e507591ec1/STRATEGIC_ROADMAP_PRIME.md).
- **Core Architecture (v1.6)**: [ARCHITECTURE_MICROSERVICES_DRAFT.md](file:///home/mike-anderson/.gemini/antigravity/brain/1e3cf111-f844-4787-9bd4-34bf6de8cf53/ARCHITECTURE_MICROSERVICES_DRAFT.md).
- **Transformative Synthesis**: [COHEZION_TRANSFORMATIVE_SYNTHESIS.md](file:///home/mike-anderson/.gemini/antigravity/brain/1e3cf111-f844-4787-9bd4-34bf6de8cf53/COHEZION_TRANSFORMATIVE_SYNTHESIS.md).

If you encounter an ethical or behavioral ambiguity, consult these documents immediately.

## 3. Dynamic Knowledge Hub

To maintain a lean context, historical and specialized information is stored in the following locations:

- **Historical Context**: [MISSION_JOURNAL.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/MISSION_JOURNAL.md) (Developments, discoveries).
- **Extracted Wisdom**: [KEY_LEARNINGS.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md).
- **Technical Standards**: [.agent/CODING_STANDARDS.md](file:///home/mike-anderson/dev/cohezion/.agent/CODING_STANDARDS.md).
- **Encoding**: Use 12D state vectors (3 Spatial + 1 Time + 8 Brane) for all trajectory predictions.
- **Package Management**: **UV** is the single source of truth for dependencies and environments.
- **Physics Core**: Quark Gluon Plasma (QGP) Liquid Phase serves as the substrate for high-density agent generation.

## 4. Operational Guardrails

- **Resource Monitor**: Enforce a strict global limit of **4 concurrent large model calls**.
- **Polyglot Architecture**: Move compute-heavy Simulations (QGP, Magnetohydrodynamics) to **Rust** via PyO3 bindings.
- **Evolution Protocol**: Refer to [.agent/EVOLUTION_PROTOCOL.md](file:///home/mike-anderson/dev/cohezion/.agent/EVOLUTION_PROTOCOL.md).
- **Fine-Tuning**: Local Corpus -> QLoRA adaptation for `mistral` / `deepseek` models.
- **Capabilities**: Consult [.agent/CAPABILITY_MAP.md](file:///home/mike-anderson/dev/cohezion/.agent/CAPABILITY_MAP.md) for skill coverage.
- **New Capabilities (2026-01-31)**:
  - **HITL Context Coordinator**: Humanintent steering as a primary governance layer.
  - **Reward & Ratchet**: Economic ascension for successful agents/skills.
  - **JEPA World Model**: Meaning-based predictive trajectories.
  - **UCP/MCP Interoperability**: Protocol-sovereign commerce and context.
  - **Quadrature Nexus Orchestration (v1.0)**: Canonical 4-fabric swarm governance established (2026-02-18).
  - **Agentic Journey Perception**: Truth-anchored 12D trajectory capture and HUD visualizer.
  - **Compound Engineering Unification**: Unified model selection and telemetry via `cohezion-bridge`.

## 6. Standard Operating Protocols

- **Protocol: Hallucination Resolution**: Always invoke `resolve_claims` or `HallucinationResolver` to ground system specs in "Truth Anchors" (`residency_awareness.py`: AMD Ryzen AI Max, 128GB RAM).
- **Protocol: Sovereign Persistence**: Use `remember_fact` and `recall_context` via `cohezion-bridge` for cross-session intelligence continuity (MEMORY_MCP_PRIME).
- **Protocol: Vanguard Research**: Trigger `DailyScoutAgent` via `daily_scout_research` to maintain Tip-of-the-Spear SLM awareness.
- **Protocol: Local Offload**: Route all menial tasks (docs, formatting, basic summaries) to local SLMs via `VaultGuidedRouter` to preserve token credits.
- **Protocol: Token Telemetry**: All LLM calls MUST be recorded via `TokenEfficiencyTracker` to maintain R-Zero fiscal visibility.
- **Protocol: Session Isolation**: High-horizon development tasks MUST use `WorktreeOrchestrator` to allocate dedicated worktrees in `/tmp/cohezion_swarm/`.

## 5. Repository Layout & Key Locations

Refer to [ARCHITECTURE.md](file:///home/mike-anderson/dev/cohezion/knowledge_graph/ARCHITECTURE.md) for the structural blueprint.

- **Source**: `src/cohezion/` - Core package.
- **Research**: `research/` - Challenges, Notebooks, and Experiments.
- **Apps**: `apps/` - Web applications (React/Vite).
- **Ops**: `ops/` - Deployment configurations (Docker/K8s).
- **Knowledge**: `knowledge_graph/` - Persistent memory and architecture docs.
- **Scripts**: `scripts/drivers/` - Automation and simulation drivers.
- **Templates**: `templates/` - Standard artifacts (Skills, Retrospectives).

> [!NOTE]
> This file is the "Root of Trust" for the agent. If information is missing here, it will be found in one of the linked modules.
