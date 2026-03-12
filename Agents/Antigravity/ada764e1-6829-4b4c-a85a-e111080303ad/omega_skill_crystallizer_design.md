---
type: antigravity-artifact
session_id: ada764e1-6829-4b4c-a85a-e111080303ad
date: 2026-03-04
title: "Omega Skill Crystallizer Design"
aspect: doer
neural:
  activation: 0.340
  stage: embryo
  cluster: Agents
---

# Project OMEGA: Evolutionary Skill Crystallizer

## Objective
Design a "Long Horizon" background task that automatically improves the swarm's capability by crystallizing successful mission patterns into reusable **Skills**.

## The Problem
Success patterns (like the "Quadrature Nexus" VLIW optimization or "SNR Locking" in BlueQubit) currently live only in static logs or one-off walkthroughs. They are not automatically available to future agents unless explicitly retrieved.

## The Solution: Skill Crystallizer Daemon
A background process that implements the **Evolutionary Ratchet**:
1.  **Scan**: Monitors `logs/archive/*.log` for "MISSION SUCCESS" markers.
2.  **Extract**: Uses a specialized SLM (Small Language Model, e.g., Mistral/Phi-4) to parse the log and extract:
    -   **Strategy Used** (e.g., "Latent Round Folding")
    -   **Code Patterns** (the `OptimizedKernelBuilder` structure)
    -   **Metrics** (Speedup > 10x)
3.  **Crystallize**: Generates a new `src/cohezion/skills/<NAME>_PRIME.md` following the standard template.
4.  **Verify**: Runs a syntax check on the new Skill.
5.  **Commit**: Proposes the new Skill to the user.

## Architecture

### 1. The Watcher (`omega_watcher.py`)
-   **Trigger**: File system event on `logs/archive/`.
-   **Filter**: Only processes logs with `MISSION SUCCESS`.

### 2. The Distiller (LLM Prompt)
An expert prompt designed for a local model (e.g., Qwen 32B):
> "Analyze this interaction log. Identify the primary technical breakthrough. Abstract it into a generic pattern. Output in Markdown Skill Format."

### 3. The Library (`src/cohezion/skills/`)
-   **Namespace**: `auto_generated/`
-   **Review Queue**: `review_pending/`

## Implementation roadmap (Small Long-Horizon Task)
1.  **Day 1**: Write `omega_watcher.py` to index successful missions.
2.  **Day 2**: Create the "Distiller" prompt and test it on `mission_50.log` (Anthropic).
3.  **Day 3**: Automate the file generation into `review_pending/`.
4.  **Continuous**: The system slowly builds a library of 100+ micro-skills without human intervention.

## Value Proposition
This transforms "solving a task" from a linear value add to an **exponential** one, as every success permanently upgrades the agent's baseline intelligence.

## Related Vault Notes

- [[cohezion]]
