---
description: "Project Management Prime: Managing Chaos with R-Zero Methodology."
---

# Project Management Prime

## 1. Core Philosophy: The R-Zero Approach
Project management in Cohezion is not just about tracking tasks; it's about navigating the tension between **Ambition** (Challenger) and **Execution** (Solver).

### The Triad
*   **Challenger (Ambition):** Defines the "Impossible" constraints. (e.g., "Run 1M sims on local hardware").
*   **Solver (Execution):** Finds the pragmatic path to satisfy constraints.
*   **Pragmatist (Review):** Strips away hype and validates hard boundaries.

## 2. Project Lifecycle

### Phase 1: Initiation (The Challenge)
*   **Artifact:** `implementation_plan.md`
*   **Action:** Define the **Challenger Constraints**.
    *   *Bad:* "Build a fast API."
    *   *Good:* "Build an API that handles 10k req/s with <50ms latency on 1 CPU."

### Phase 2: Execution (The Solver)
*   **Artifact:** `task.md`
*   **Action:** Break down the solution into atomic **Solver Steps**.
*   **Rule:** Every step must be verifiable via command line.

### Phase 3: Review (The Pragmatist)
*   **Artifact:** `walkthrough.md`
*   **Action:** Verify against **Edge Cases**.
    *   Did we violate physics/logic?
    *   Did we use buzzwords ("Hyper-Scaled") to mask poor engineering?

## 3. Templates (Ref: `.cohezion/templates/`)

### Project Template
Use for new major initiatives.
```markdown
# Project: [Name]
## Challenger Constraints
1. [Constraint A]
2. [Constraint B]
## Edge Cases to Verify
- [ ] Case Zero
- [ ] Case Infinite
```

### Task Template
Use for complex tickets.
```markdown
# Task: [Name]
## R-Zero Checklist
- [ ] Solver: Happy Path Works?
- [ ] Challenger: Edge Case Handled?
- [ ] Pragmatist: No Hype?
```

## 4. Anti-Patterns (The "Overhype" Penalty)
*   **Conflation:** Mixing simple logic with complex names to sound smart.
*   **Hallucination:** Claiming a feature exists when it's just a placeholder.
*   **Plateauing:** Doing the same easy task repeatedly without increasing difficulty.

## 5. Course Correction
If a project hits a plateau:
1.  **Inject Entropy:** Introduce a new constraint (e.g., "Cut memory usage by 50%").
2.  **Verify:** If the team/agent solves it, the plateau is broken.
