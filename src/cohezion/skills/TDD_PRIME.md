---
name: tdd-prime
description: Strict enforcement of the RED-GREEN-REFACTOR cycle. Use during the 'Execute' phase of the development loop. Mandatory for all source code changes.
metadata:
  version: "1.0"
  legacy-name: TDD_PRIME
---

# SKILL: TDD_PRIME

## DOMAIN EXPERTISE
Mastery of the RED-GREEN-REFACTOR loop. This skill treats code as a byproduct of a passing test, ensuring that no logic is written without a preceding verification requirement.

## THE WORKFLOW (MANDATORY)
You MUST follow these steps for every single task in the implementation plan.

1. **RED (The Failure)**:
   - Write a minimal test case that exercises the required behavior.
   - Run the test. **It MUST fail.**
   - **Symmetry Check**: Verify the failure is "Correct" (it fails for the right reason, not a syntax error).

2. **GREEN (The Minimal Implementation)**:
   - Write the *absolute minimum* amount of code necessary to make the test pass.
   - Avoid "pre-emptive" coding. Do not add "future-proof" logic.
   - Run the test. **It MUST pass.**

3. **REFACTOR (The Symmetry Alignment)**:
   - Now that the behavior is verified, align the code with the project's symmetry.
   - Check for:
     - **FLUME-First**: Are semantic operations encoded/decoded through the VAE?
     - **Geometric Correspondence**: Is the logic aligned with the target topological regime?
     - **Naming**: Does the naming match the project's a-priori standards?
-   Clean up redundant logic and remove "developer-scaffolding."

4. **COMMIT (The Baseline)**:
   - Commit the change immediately after the REFACTOR step.
   - Include the test and the implementation in the same commit.

## KNOWLEDGE ANCHORS
- **Vault**: `~/vaults/cohezion-vault/skills/tdd-prime/`
- **SurrealDB**: `node:skill_tdd_prime`
- **Latent Seed**: `regime:B`

## ANTI-PATTERNS (RED FLAGS)
- "I'll write the tests after the code is done." $\rightarrow$ **WRONG**. This is "test-after" development, not TDD.
- "The test passes, so the code is correct." $\rightarrow$ **WRONG**. The test only proves the behavior is correct for that one case.
- "I'll just use a print statement to verify." $\rightarrow$ **WRONG**. Prints are not verifications.

## VERSION
v1.0
