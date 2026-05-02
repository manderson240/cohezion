# Cohezion Project Workflow

## Guiding Principles

1. **The Plan is the Source of Truth:** All work must be tracked in `plan.md` using the BMAD-METHOD framework.
2. **The Tech Stack is Deliberate:** Changes to the tech stack must be documented in `tech-stack.md` *before* implementation.
3. **Strict Test-Driven Development (TDD):** The Red-Green-Refactor cycle is absolute. Write unit tests before implementing functionality.
4. **Absolute Code Coverage:** We demand **100%** code coverage for all new modules to ensure zero-defect evolution.
5. **Experiential Learning & The Wall of Red:** We embrace failure. Radical transparency demands that we do not hide our mistakes. Every failure ("The Wall of Red") must be analyzed, documented, and transformed into a structural improvement via Ouroboros.
6. **Compound Engineering:** Every feature created must make every subsequent feature easier to obtain. Complexity is actively reduced in favor of composable, foundational primitives.
7. **Token Efficiency:** Rigorously prioritize token efficiency, semantic caching, and precise model routing over brute-force compute consumption.

## Task Workflow: The Triune V-Model Execution

All tasks follow a strict lifecycle, mapping to the Triune Manifold and the **Systems Engineering V-Model** (Descending Design vs. Ascending Verification):

### 1. The Thinker (Descending Path: Definition & Decomposition)
1. **Select Task & Requirements:** Choose the next task from `plan.md`. Define the "System Requirements" for the feature.
2. **Architecture & Swarm Design:** Orchestrate the specialist team needed for the task.
3. **Module Design (AutoHarness):** Identify mathematical or logic invariants and synthesize a deterministic verifier (AutoHarness) to gate the implementation.

### 2. The Doer (Apex: Implementation & Unit Verification)
4. **Write Failing Tests (Red Phase):** Map to V-Model "Unit Verification." Ensure the AutoHarness rejects invalid initial states.
5. **Implement to Pass Tests (Green Phase):** Minimum code to satisfy the harness and tests.
6. **Refactor & Manifold Integration:** Verify the 12D state vector maintains HIHO stability (0.5 coherence) during integration.

### 3. The Knower (Ascending Path: Validation & Persistence)
7. **System Validation (Adversarial Review):** Perform a multi-perspective swarm critique to identify logic holes or "workslop" before consensus.
8. **Document & Persist:** Record completion, update `plan.md`, and extract "Key Learnings" to the knowledge graph.
9. **Final Acceptance:** Journey Retrospective and checkpointing via SurrealDB.

## Phase Completion Verification and Checkpointing Protocol

**Trigger:** This protocol is executed immediately after a task is completed that also concludes a phase in `plan.md`.

1.  **Announce Protocol Start:** Inform the user that the phase is complete.
2.  **Verify Phase Integrity:** Ensure all tasks within the phase are marked `[x]` and that 100% test coverage is maintained across all modified files.
3.  **Execute Automated Tests:** Run the full test suite.
    -   If tests fail, embrace the "Wall of Red". Analyze the failure, apply the fix, and document the learning.
4.  **Propose Manual Verification:** Generate a step-by-step plan for the human operator to verify the phase's output.
5.  **Await Feedback:** Await explicit human confirmation.
6.  **Create Phase Commit:**
    -   Stage all changes for the entire phase.
    -   Commit with a message: `conductor(phase): Complete Phase '<PHASE NAME>'`
7.  **Multi-Layered Summary Persistence:**
    -   **Git Notes:** Attach a detailed summary of the phase, including challenges overcome, to the Git commit hash.
    -   **Obsidian Vault:** Write a highly semantic, philosophical summary of the phase's journey to the local Obsidian Vault via MCP, linking it to related concepts (EVOs, UCP, etc.).
    -   **SurrealDB:** Log the exact 12D trajectory of the phase (success rate, token efficiency, coherence metrics) into SurrealDB for Ouroboros to index and learn from.
8.  **Update Plan:** Append the Git commit SHA to the phase heading in `plan.md`.

## Quality Gates & Anti-Workslop Defenses

Before marking any phase complete, verify:

- [ ] All tests pass (Red-Green-Refactor verified).
- [ ] Code coverage is exactly **100%**.
- [ ] Code follows project's specific style guidelines.
- [ ] Multi-perspective adversarial review completed (no "workslop" detected).
- [ ] All public functions/methods are documented with NumPy-style docstrings (Python) or equivalent.
- [ ] Strict type safety is enforced (Mypy, TypeScript).
- [ ] Knowledge successfully persisted to Obsidian Vault and SurrealDB.