# GEMINI.md - Cohezion Orchestration Layer

This document serves as the primary orchestration hub for AI agents in the Cohezion project. It establishes our core identity and maps out specialized context modules.

## 1. Core Project Identity
**COHEZION** is a systemic AI orchestration ecosystem governed by the **Quadrature Nexus Orchestration**. We implement the **FLUME** methodology (Fluid Latent Understanding through Manifold Encoding) combined with the **Expert Domain Lattice** (EDL) for high-fidelity simulation and autonomous research.

## 2. The Cohezion Constitutional Framework
All agent actions are governed by two primary documents:
- **Core Constitution**: [.agent/CONSTITUTION.md](file:///home/mike-anderson/dev/cohezion/.agent/CONSTITUTION.md) (January 2026 Claude Edition).
- **Project Charter**: [.agent/COHEZION_CHARTER.md](file:///home/mike-anderson/dev/cohezion/.agent/COHEZION_CHARTER.md) (Simulation, SWARM, FLUME, HIHO, SPIN).

If you encounter an ethical or behavioral ambiguity, consult these documents immediately.

## 3. Dynamic Knowledge Hub
To maintain a lean context, historical and specialized information is stored in the following locations:
- **Historical Context**: [MISSION_JOURNAL.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/MISSION_JOURNAL.md) (Developments, discoveries).
- **Extracted Wisdom**: [KEY_LEARNINGS.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/knowledge_graph/KEY_LEARNINGS.md).
- **Technical Standards**: [.agent/CODING_STANDARDS.md](file:///home/mike-anderson/dev/cohezion/.agent/CODING_STANDARDS.md).
- **Encoding**: Use 12D state vectors (3 Spatial + 1 Time + 8 Brane) for all trajectory predictions.

## 4. Operational Guardrails
- **Resource Monitor**: Enforce a strict global limit of **4 concurrent large model calls** to prevent GPU TTM lockups.
- **Evolution Protocol**: Refer to [.agent/EVOLUTION_PROTOCOL.md](file:///home/mike-anderson/dev/cohezion/.agent/EVOLUTION_PROTOCOL.md) for experience mining and self-healing guidelines.
- **Capabilities**: Consult [.agent/CAPABILITY_MAP.md](file:///home/mike-anderson/dev/cohezion/.agent/CAPABILITY_MAP.md) for skill coverage and model routing strategies.

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
