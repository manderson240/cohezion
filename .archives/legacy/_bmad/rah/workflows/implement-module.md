# WORKFLOW: RAH Module Implementation

## PURPOSE
Create a new "Resilience & Autonomic Healing" (RAH) module using all available agentic skills.

## PREREQUISITES
- Access to Research (ArXiv/HF)
- Access to Knowledge Graph (Library/Skills)
- Access to Swarm Reasoning (Architect/Engineer/Critic)
- Access to BMAD Tooling (PRD/Arch/Epic generation)

## STEPS

### 1. Intelligence Gathering (Research Skill)
- Search ArXiv for "Autonomic Computing MAPE-K loop AI agents".
- Identify SOTA healing strategies (e.g., sentinel systems, self-reflective repair).
- Output: Research summary in `_bmad/rah/research/SOTA.md`.

### 2. Requirements Definition (BMAD BMM Skill)
- Create PRD for RAH module using `bmad_bmm_create_prd`.
- Define User Stories for "System Self-Healing", "Proactive Resource Rebalancing", and "Failure Isolation".
- Output: `_bmad/rah/prds/PRD.md`.

### 3. Architectural Design (Swarm Skill)
- Trigger Swarm Debate (`run_debate`) with ARCHITECT, ENGINEER, and CRITIC perspectives.
- Debate: "Centralized vs. Decentralized Autonomic Management in Cohezion Swarms".
- Output: Decision record in `_bmad/rah/architecture/ARCHITECTURE.md`.

### 4. Visual Blueprint (Design Skill)
- Generate architecture diagram using `/diagram`.
- Focus on the control loop between `ResourceMonitor` and `AutonomicManager`.
- Output: `_bmad/rah/architecture/diagram.png`.

### 5. Implementation (Coding Skill)
- Scaffold the Python module in `src/cohezion/resilience/`.
- Implement `AutonomicManager` (MAPE-K loop).
- Implement `HealingStrategy` interface and first 3 strategies (Restart, Scale, Swap).
- Output: Functional source code.

### 6. Persistence & Learning (Surreal Skill)
- Store module blueprint as a Universe Node (`store_node`).
- Extract and store design learnings (`store_learning`).
- Output: Persistence records in SurrealDB.

### 7. Verification (TEA Skill)
- Design and execute TDD stories (`bmad_tea_test_design`).
- Ensure 80%+ coverage for healing logic.
- Output: Test results in `_bmad/rah/tests/RESULTS.md`.

## SUCCESS CRITERIA
- RAH module can autonomously detect simulated memory pressure and trigger a `MODEL_SWAP`.
- All documentation artifacts are cross-linked in `_bmad/rah/INDEX.md`.
- No regressions in existing `reliability` patterns.
