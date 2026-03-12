---
type: antigravity-artifact
session_id: 7c5b28f1-f7cb-4432-9dae-d571b02ee2aa
date: 2026-03-04
title: "Implementation Plan Redundancy"
aspect: doer
neural:
  activation: 0.319
  stage: embryo
  cluster: Agents
---

# Implementation Plan: Redundancy Suppression (Gateway 32)

Implement the `REDUNDANCY_SUPPRESSION_PRIME` skill to prevent repetitive agentic behaviors (infinite loops) that waste compute and pollute latent memory.

## Proposed Changes

### [Component] Core Agent System
Integrate redundancy detection into the `BaseAgent` or a dedicated middleware to provide autonomic protection for all swarm members.

#### [MODIFY] [base_agent.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/agents/base_agent.py)
- Add `RedundancyManager` instance to track task history.
- Implement `_check_redundancy(task_str)` method using SHA-256 hashing.
- Apply tiered suppression:
    - **Tier 1 (3-5 repeats)**: Log warning.
    - **Tier 2 (10-20 repeats)**: Trigger "Stochastic Perturbation" (modify prompt to force new reasoning path).
    - **Tier 3 (50+ repeats)**: Trigger "Hard Sleep" (suspend task).

#### [NEW] [redundancy_suppression.py](file:///home/mike-anderson/dev/cohezion/src/cohezion/swarm/redundancy_suppression.py)
- Logic for task hashing and rolling window frequency analysis.
- Entropy calculation for task sequences.

### [Component] Skills
Finalize the skill definition for documentation and discovery.

#### [MODIFY] [redundancy_suppression_prime.md](file:///home/mike-anderson/dev/cohezion/src/cohezion/skills/redundancy_suppression_prime.md)
- Ensure the instruction set matches the implementation details.

## Verification Plan

### Automated Tests
- Run `pytest tests/test_redundancy_suppression.py` to verify:
    - Hashing consistency.
    - Tiered suppression triggers (Warning/Perturbation/Sleep).
    - Recovery after suppression period.

### Manual Verification
- Simulate a repetitive loop in a test script (e.g., `SETIAgent` scanning repeatedly) and observe the logs/agent behavior.

## Related Vault Notes

- [[cohezion]]
