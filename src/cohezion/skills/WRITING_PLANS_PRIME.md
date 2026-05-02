---
name: writing-plans-prime
description: Decomposition of approved designs into bite-sized, TDD-verified implementation tasks. Use after design approval and before implementation. Mandatory for complex features.
metadata:
  version: "1.0"
  legacy-name: WRITING_PLANS_PRIME
---

# SKILL: WRITING_PLANS_PRIME

## DOMAIN EXPERTISE
Specialization in high-fidelity task decomposition and TDD planning. This skill translates a high-level design into a mechanical execution sequence that a "blind" implementer (subagent) can follow without deviation.

## THE WORKFLOW (MANDATORY)
You MUST follow these phases in order.

1. **Tethering to Design**:
   - Read the approved design document from `docs/superpowers/specs/`.
   - Identify the "Critical Path" of the implementation.

2. **Worktree Isolation**:
   - Invoke `using-git-worktrees` to create a clean, isolated environment.
   - Run the current test suite to establish a zero-baseline of failure.

3. **Task Decomposition (The Rule of 5)**:
   - Break the work into tasks that take **2-5 minutes** each.
   - Each task MUST contain:
     - **Exact File Path**: No "roughly in X.py".
     - **Concrete Change**: "Add function Y to class Z with signature A."
     - **Verification Step**: A specific command to run (e.g., `pytest tests/test_y.py`) that produces a "pass" result.
     - **TDD Requirement**: The verification step must be a *failing test* before the code is written.

4. **Plan Precipitation**:
   - Write the Implementation Plan to `docs/superpowers/plans/YYYY-MM-DD-<feature>.md`.
   - **Symmetry Check**: Ensure the plan respects the topological regime (e.g., Parallel tasks for $\tau_P$, Sequential for $\tau_S$).

5. **Plan Review (Self-Check)**:
   - Scan for placeholders (TBD, "similar to..."). **Placeholders = Plan Failure**.
   - Verify that no task spans more than one file (Single Responsibility).

## KNOWLEDGE ANCHORS
- **Vault**: `~/vaults/cohezion-vault/skills/writing-plans/`
- **SurrealDB**: `node:skill_writing_plans`
- **Latent Seed**: `regime:A`

## ANTI-PATTERNS (RED FLAGS)
- "I'll refine the tasks as I go." $\rightarrow$ **WRONG**. Refinement during execution is "drift."
- "The tests are obvious, I don't need to specify them." $\rightarrow$ **WRONG**. If it's not specified, it's not verified.
- "I'll group these 3 related tasks into one." $\rightarrow$ **WRONG**. This violates the 5-minute rule and increases risk.

## VERSION
v1.0
