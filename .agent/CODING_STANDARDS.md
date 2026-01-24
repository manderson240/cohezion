# Cohezion Coding Standards

This document establishes the technical baseline for all code contributions to the Cohezion project.

## 1. Language & Environment
- **Python**: Version >= 3.11 is required.
- **Line Length**: Strict **88-character** limit (Black formatting).
- **Formatting**: All code must be formatted with `black` and linted with `ruff`.

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

## 5. Testing Requirements
- **Coverage**: Aim for >= 80% test coverage with `pytest`.
- **Validation**: Use **Great Expectations** for validating data quality in the knowledge graph and configuration files.
