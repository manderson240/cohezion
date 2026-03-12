---
type: antigravity-artifact
session_id: d9c1fcdb-69db-458c-b64a-f26e49625c33
date: 2026-03-04
title: "Swarm Evolution Protocol"
aspect: doer
neural:
  activation: 0.363
  stage: embryo
  cluster: Agents
---

# SWARM EVOLUTION PROTOCOL (v1.2)
*Governed by the Quadrature Nexus Orchestration*

## 1. Objective
To establish a closed-loop system where the Swarm autonomously identifies defects, resolves them, and systematically improves its own capabilities (Skills) based on these experiences.

**Core Mandate**: All evolutionary actions must flow through the **FLUME Methodology** (Fluid Latent Understanding through Manifold Encoding) and be persisted in **SurrealDB** for future experience mining.

## 2. Core Architecture

### A. The Scout (`issue_scout.py`)
A background daemon that continuously observes the codebase.
- **Mission**: Identify entropy (TODOs, FIXMEs, Failed Tests, Lint Errors).
- **Ouroboros Integration**: Tasks are prioritized based on the **Ouroboros Entropy Vector**. High-entropy components get urgent priority.
- **Mechanism**:
    1.  Scans `.py`, `.ts`, `.md` files for marker tags.
    2.  Parses identifying context (file, line, description).
    3.  Upserts tasks into SurrealDB table `swarm_tasks`.

### B. The Marketplace (A2A/MCP Exchange)
Inter-agent communication handles via **Agent-to-Agent (A2A)** and **Model Context Protocol (MCP)** standards.
- **Protocol**: Agents expose capabilities via MCP. The Marketplace is a UCP (Universal Communication Protocol) bus.
- **Orchestration**: The **Quadrature Nexus** assigns tasks based on 12D Manifold alignment.
- **Schema**:
    ```json
    {
        "id": "task_xyz",
        "type": "refactor|bugfix|doc",
        "entropy_weight": 0.8,  # Derived from Ouroboros
        "validation_suite": "mycelium_v1",
        "flume_vector": [...] # 12D State Encoding
    }
    ```

### C. The Worker (Agent Execution)
Agents (e.g., `small-coder-7b`, `architect-32b`) check the marketplace via A2A.
- **Routing**: **Small Language Models (SLMs)** like *Phi-4* or *Qwen-2.5-7B* handle 80% of tasks (Unit Tests, Docstrings, Simple Fixes) to conserve high-tier tokens.
- **Mycelium Integration**: Before marking complete, the Agent must invoke **Mycelium** to generate a rigid test suite for the fix.
- **Persistence**: Every thought, action, and result is captured in SurrealDB (`universe_nodes`) to build the **Cohezion Experience Dataset**.

### D. The Reward (Evolutionary Crystallization)
Upon successful verification, the Agent receives an **Evolution Token**.

## 3. Safety Guardrails (The Constitution)
1.  **Identity Lock**: Agents cannot modify their own `__init__.py`.
2.  **Consensus Check**: Significant refactors require a **12-Agent Council Vote** (Dual-State Verification across 12 distinct model personas) to ensure massive alignment.
    2.  **Crystalize Wisdom**: Add an entry to `KEY_LEARNINGS.md`.
    3.  **Optimize Prompt** (Restricted): Propose a change to its own system prompt (Requires Human "Adversarial Review").

## 3. Safety Guardrails (The Constitution)
1.  **Identity Lock**: Agents cannot modify their own `__init__.py`.
3.  **Consensus Check**: Significant refactors require a **12-Agent Council Vote** (Dual-State Verification across 12 distinct model personas) to ensure massive alignment.

## 4. Implementation Steps
1.  Create `scripts/drivers/issue_scout.py`.
2.  Define `SwarmTask` schema in `SurrealClient`.
3.  Update `autonomous_bbq.py` to poll `swarm_tasks`.
4.  Implement `refine_skill()` capability.

## Related Vault Notes

- [[12D-Manifold]]
- [[adversarial-review]]
- [[cohezion]]
- [[surrealdb]]
