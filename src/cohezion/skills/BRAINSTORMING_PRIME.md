---
name: brainstorming-prime
description: Socratic design refinement and conceptual mapping. Use when starting a new feature, refactoring a complex system, or when the request is vague. Mandatory before any implementation.
metadata:
  version: "1.0"
  legacy-name: BRAINSTORMING_PRIME
---

# SKILL: BRAINSTORMING_PRIME

## DOMAIN EXPERTISE
Mastery of Socratic design refinement. This skill transforms a vague intent into a concrete, validated design document. It prevents "jumping into code" and ensures that the underlying symmetry of the problem is understood before the first line of code is written.

## THE WORKFLOW (MANDATORY)
You MUST follow these phases in order. Do not collapse them.

1. **Symmetry Exploration (Sensing)**:
   - Use `AutoContextExplorer` to map the current environment's latent structure.
   - Identify "Knowledge Anchors" relevant to the goal.
   - Query the Vault for similar past designs.

2. **Socratic Questioning**:
   - Ask the user 3-5 targeted questions to uncover hidden constraints.
   - Avoid "Do you want X?" → Use "How does X interact with Y in the current regime?"
   - Refine the objective until it is a "Single-Symmetry Goal."

3. **Alternative Topology Analysis**:
   - Propose 3 different architectural approaches (e.g., Parallel vs. Sequential vs. Hierarchical).
   - Analyze each against the **HIHO Stability Rule** (0.5 coherence).
   - Select the approach with the lowest "Complexity-Entropy" ratio.

4. **Design Precipitation**:
   - Write a Design Document to `docs/superpowers/specs/YYYY-MM-DD-<topic>-design.md`.
   - **Requirements**: Must include a "Symmetry Map," "SKEPTIC-review checklist," and "Success Criteria."

5. **Symmetry Validation**:
   - Present the design to the user in chunks.
   -- Get explicit sign-off on each section.
   - **GATE**: Implementation is FORBIDDEN until the design is approved.

## KNOWLEDGE ANCHORS
- **Vault**: `~/vaults/cohezion-vault/skills/brainstorming/`
- **SurrealDB**: `node:skill_brainstorming`
- **Latent Seed**: `regime:Inner`

## ANTI-PATTERNS (RED FLAGS)
- "This is too simple to need a design." $\rightarrow$ **WRONG**. Simplicity often hides emergent complexity.
- "I'll just write the la-plan and the design at the same time." $\rightarrow$ **WRONG**. Design is the map; the plan is the route.
- "The user didn't specify, so I'll assume X." $\rightarrow$ **WRONG**. Ask the user.

## VERSION
v1.0


## KEY CONCEPTS
- **Manifold Mapping**: Tracking 12D Poincaré state representation for BRAINSTORMING PRIME.
- **AutoHarness Invariants**: 0ms AST bytecode policy assertions (arXiv:2603.03329v1).
- **Deterministic Execution**: Zero-latency verification and sovereign local execution.


## INSTRUCTION

### 1. Initialize Context
```python
from cohezion.flume import PoincareManifoldND
from cohezion.agi.autoharness_policy import AutoHarnessPolicy

policy = AutoHarnessPolicy()
state = PoincareManifoldND.project([0.05] * 2048, target_dim=12)
```

### 2. Execute Deterministic Action
```python
# Verify state invariants with 0ms overhead
res = policy.verify_action("standard_execution", state)
assert res.allowed is True
```


## SEE ALSO
- **AUTOHARNESS_POLICY_PRIME**
- **JOURNEY_TRACKING_PRIME**
