# Code Quality Notes

This document documents intentional code quality exemptions and architectural decisions in Cohezon's codebase.

## Intentional Security Exemptions

### Dynamic Agent Compilation (`src/cohezion/agents/factory.py`)
- **Lines**: 283, 321
- **Issue**: `exec()` usage (rule: S102)
- **Rationale**: Dynamic compilation of agent classes from skill specifications is a core feature. The `exec()` call is constrained to a restricted namespace with controlled builtins. Skill specs are trusted inputs from the skill registry.
- **Mitigation**: Namespace sandboxing, spec validation, skill registry curation

### Gymnasium Environment Assertions (`src/cohezion/rl/environment.py`, `src/cohezion/simulation/rl_framework.py`)
- **Lines**: environment.py:107, rl_framework.py:167
- **Issue**: `assert` statements (rule: S101)
- **Rationale**: Assertion-based state validation is standard practice in reinforcement learning environments. These assertions guard against programming errors in the simulation, not production failures.
- **Context**: Training environments, not production code

### System Privilege Escalation (`src/cohezion/healing/amd_s2idle_report.py`)
- **Line**: 42
- **Issue**: `os.execvp()` for sudo relaunch (rule: S102)
- **Rationale**: System diagnostics tool requires root privileges to read kernel logs and hardware counters. User explicitly runs the script, which relaunches with sudo when needed.
- **Mitigation**: Explicit user awareness, no silent escalation

## Code Organization Decisions

### Archive Code (`src/cohezion-archive/`)
- **Status**: Excluded from linting via `pyproject.toml`
- **Rationale**: Contains 472 historical versions of modules (2.6M lines). Used for reference and git archaeology, not active execution.
- **Policy**: No active development, minimal maintenance

### SQL Schema Line Length (`src/cohezion/universe/schema.py`)
- **Lines**: 100-122
- **Issue**: E501 - SurrealDB index creation lines exceed 100 characters
- **Rationale**: SurrealDB's vector index syntax requires inline type/parameters. Breaking these multi-part definitions would reduce readability and template manageability.
- **Example**: `DEFINE INDEX idx_knowledge_vector ON knowledge_extract FIELDS embedding TYPE VECTOR DIMENSION 512 DIST COSINE;`
- **Decision Acceptable**: SQL statements have different readability conventions than Python

## Type Checking Strategy

### mypy Configuration (`pyproject.toml`)
```toml
[tool.mypy]
disallow_untyped_defs = false  # Migration in progress
check_untyped_defs = true
```
- **Status**: Permissive migration in progress
- **Goal**: Incremental type coverage (currently ~70%)
- **Blocking items**: 
  - Un-typed legacy code (`cohezion-archive/`, migration modules)
  - Dynamic agent compilation (intentionally un-typed)
  - Third-party library integration points

### Type Ignore Usage
- **Count**: 41 `# type: ignore` comments in active codebase
- **Categories**:
  1. Dynamic code (agent compilation, skill loading)
  2. Third-party library stubs (SurrealDB, MCP adapters)
  3. Complex generic types that mypy cannot resolve
  4. Ongoing migration from Python 3.11 → 3.13 type syntax

## Pre-commit Configuration

### Commit Stage (Fast)
- **Ruff**: Format check + quick syntax errors only F, E9, E501, UP
- **Purpose**: Sub-second feedback during development
- **Comprehensive linting**: Delegated to CI

### Push Stage (Safety)
- **Secrets detection**: detect-secrets with baseline
- **Bandit**: Security scanning (severity: medium+)
- **Large files**: 1MB maximum (larger files registered in artifact system)

## Python 3.11 Pinned Environment (ROCm/Triton)

### Status (2026-04-05)
- [x] Pinned to Python 3.11 in `pyproject.toml`
- [x] Updated `.python-version`
- [x] Resolved ROCm/Triton dependency conflicts
- [x] Updated system paths and scripts

### Consistency Checks
- [x] mypy `python_version = "3.11"`
- [x] ruff `target-version = "py311"`
- [x] CI/CD environment variables

## Code Quality Metrics

### Ruff Linting (as of 2026-03-21)
- **Initial errors**: 917
- **Fixed**: 292 (32%)
- **Remaining**: 625
  - Line length (E501): 185 (SQL schemas, markdown templates)
  - Unused imports (F401): 124 (lazy loading, backward compatibility)
  - Type checking incomplete (TC series): 200+ (migration in progress)

### Test Coverage
- **Total tests**: 4,426
- **Passing**: 3,486 (78.7%)
- **Integration tests**: Require live services (Ollama, SurrealDB)
- **Fast unit tests**: ~1,200 (@pytest.mark.fast)

## Contributing Guidelines for Code Quality

1. **Pre-commit hooks**: `pip install pre-commit && pre-commit install`
2. **Local validation**: `make format && make lint`
3. **Type checking**: `make type-check` (mypy)
4. **Full CI**: `make all` (format + lint + type-check + test)
5. **Security reviews**: Run `bandit -r src/cohezion` before adding subprocess/git/shell usage

When adding intentional code quality exemptions:
1. Document rationale in this file
2. Add `# noqa: RULE_CODE` with explanation
3. Consider alternative implementations
4. Review with maintainers for long-term impacta: RULE_CODE` with explanation
3. Consider alternative implementations
4. Review with maintainers for long-term impact