# Specification: Mycelium Test Synthesis

## 1. Overview
Mycelium (the ShadowScripter) is an autonomous, background layer of the Cohezion ecosystem that ensures persistent quality. It observes the journeys of sovereign EVO agents and organically "grows" comprehensive regression test suites around newly generated code, completing the strict Test-Driven Development (TDD) loop and preventing "workslop" from accumulating in the substrate.

## 2. Core Requirements
- **AST/Change Observation**: A mechanism to detect and parse new code changes introduced by an agent (e.g., analyzing the Git diff or AST of a completed task).
- **ShadowScripter Agent**: A specialized agent (inheriting from `BaseAgent`) that takes the detected changes and synthesizes a set of `pytest` test cases.
- **Coverage Loop**: The agent must interact with a tool to run the generated tests and check coverage, iterating until the target 100% coverage is reached for the modified file.
- **Integration**: Must run automatically as a post-action hook or asynchronous background process after an EVO Agent completes a generation task.

## 3. Technical Constraints
- Language: Python 3.13+
- Framework: Tight integration with `pytest` and `coverage`.
- Strict TDD: 100% test coverage required for the Mycelium logic itself.
- Code Style: Must adhere strictly to `conductor/code_styleguides/python.md`.