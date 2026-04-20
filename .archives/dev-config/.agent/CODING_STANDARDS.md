# Cohezion Coding Standards

This document establishes the technical baseline for all code contributions to the Cohezion project.

## 1. Language & Environment
- **Python**: Version >= 3.11 is required.
- **Line Length**: Strict **88-character** limit (Black formatting).
- **Formatting**: All code must be formatted with `black` and linted with `ruff`.
- **Package Management**: **UV** is the single source of truth. All commands must be executed via `uv run`.

## 1.1 Template Driven Development (TDD)
- **Manifestation Protocol**: All new features or logic blocks must be preceded by a formal Skill or Workflow template.
- **As Above, So Below**: Implementation follows the structure established in the `_PRIME.md` definitions.

## 1.2 Systems Engineering & The V-Model
- **Agent Taxonomy**: All specialist agents must operate within a defined stage of the Systems Engineering V-Model (e.g., Requirements Analysis, System Architecture, Detailed Design, Implementation, Integration, Validation).
- **AutoHarness Mandate**: All non-deterministic logic (e.g., LLM tools) MUST be wrapped in deterministic test harnesses (`tests/harnesses/`).
- **Policy Distillation**: Validated non-deterministic behaviors must be distilled into deterministic Python policies in `src/cohezion/policies/` to minimize inference costs and guarantee reliability.

## 2. Type Safety & Documentation
- **Type Hints**: Mandatory for all public function signatures (Mypy --strict compatible).
- **Docstrings**: Use **NumPy-style** docstrings for all modules, classes, and functions.
- **Explanation**: Every complex logic block must include a `#` comment explaining the "Why" (intent), not just the "How".

## 3. Asynchronous Patterns
- Prefer `async`/`await` for all I/O bound operations.
- **Timeouts**: Every external call (API, Database, File) MUST have a timeout.
- **Circuit Breakers**: Use `cohezion.reliability.get_circuit()` for all external integrations.

## 4. Error Handling & Reliability
- **Fail Fast**: Use assertions and schema validation (Pydantic) at boundaries.
- **Recovery**: Implement `try/except` blocks with specific exceptions and logging. Avoid `except Exception:`.
- **Healing**: When an error occurs, the agent should attempt to diagnose and "heal" the repository or code state using `EVOLUTION_PROTOCOL.md` guidelines.

## 6. Elegant Simplicity
- **KISS Principle**: Avoid over-engineering. If a simple one-pass logic works, do not use a multi-agent swarm.
- **Readability**: Code is for humans (and future agents). Avoid deeply nested logic or opaque abstractions.

## 7. Repository Hygiene
- **No Large Files**: Never commit files > 1MB. Use `git-lfs` or external storage if necessary.
- **Clean Diffs**: Ensure `.gitignore` is comprehensive. Check `git status` before committing.
- **Package Integrity**: Every directory in `src/` MUST have an `__init__.py`.
