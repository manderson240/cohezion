---
title: GitLab CI Runner: Local Pass Does Not Guarantee CI Pass
date: 2026-02-23
severity: HIGH
category: ci-cd
cost_of_forgetting: "Tests pass locally but fail in CI; blocked deployments from undeclared dependencies or missing credentials"
tags: [ci-cd, gitlab, testing, environment-parity]
status: validated
aspect: knower
neural:
  activation: 0.72
  stage: growing
  synapse_in: 7
  synapse_out: 5
---

# Lesson: GitLab CI Runner: Local Pass Does Not Guarantee CI Pass

## Context

During Cohezion CI/CD pipeline setup, tests consistently passed on developer machines but failed in GitLab CI. The CI environment runs in clean Docker containers that start fresh on every run -- no cached virtualenvs, no `.env` files, no locally installed system packages. This clean-room environment exposed every implicit dependency that worked locally by accident.

## Problem

Local development environments accumulate state that masks missing declarations:

1. **Cached virtualenvs**: Packages installed manually (`pip install requests`) exist in the local venv but are not declared in `pyproject.toml`. Tests pass locally; CI installs only declared deps and fails.
2. **Local `.env` files**: API keys, database URLs, and secrets live in `.env` on the developer machine. CI has no `.env` and no access to those secrets unless explicitly configured as CI/CD variables.
3. **Service availability**: Local SurrealDB and Ollama instances are running. CI has no services unless explicitly declared in the `services:` block.
4. **System packages**: Local OS has `libffi-dev`, `libssl-dev`, etc. CI Docker images may not.

Each of these creates a "works on my machine" failure that only surfaces in CI.

## Core Learning

**Treat CI as a hostile clean-room environment. Every dependency must be declared; no local state can be assumed.**

### Pattern
```yaml
# .gitlab-ci.yml -- explicitly install everything
test:
  script:
    - pip install -e ".[dev]"
    - cp .env.example .env
    - pytest tests/ -v
  services:
    - surrealdb/surrealdb:latest
```

## Solution

Environment parity was achieved through three practices:

1. **All deps in `pyproject.toml`**: Every Python dependency, including dev dependencies, is declared in the `[dev]` extras. `pip install -e ".[dev]"` reproduces the full environment.
2. **`.env.example` for CI**: A template `.env` file with dummy values is committed to the repo. CI copies it to `.env` before running tests.
3. **Services declared explicitly**: All external services (SurrealDB, Ollama) are listed in the CI `services:` block.

The final verification step: periodically run tests in a clean Docker container locally (`docker run --rm -v .:/app python:3.11 bash -c "cd /app && pip install -e '.[dev]' && pytest"`) to catch implicit dependencies before they reach CI.

## Prevention

- **Declare every dependency**: If you `pip install` something, add it to `pyproject.toml` immediately
- **Use `.env.example`**: Keep it up to date with all required environment variables (dummy values)
- **Declare CI services**: Any external service needed by tests must be in the CI configuration
- **Test in clean containers periodically**: Run the full install-and-test cycle in a fresh Docker container

## Cost of Forgetting

- **Blocked CI pipeline**: Tests fail, deployments stop, the team is stuck
- **"Works on my machine" debugging**: Hours spent determining that the fix is "add this to pyproject.toml"
- **New contributor friction**: Every new developer hits the same undeclared dependency issues
- **Secret leaks**: If developers hardcode secrets instead of using `.env`, those secrets may end up in git

## Recommendations

### Do
- Run tests in a clean Docker container locally before pushing
- Use .env.example with dummy values for CI
- Declare ALL test dependencies in pyproject.toml [dev] extras

### Don't
- Rely on locally cached virtualenvs being available in CI
- Use local .env secrets in CI (use CI/CD variables)

## Related Concepts

- [[compound-engineering]] - CI parity enables reliable compound deployment pipelines
- [[circleci-ai-cicd-validation]] - CircleCI Chunk's autonomous validation agent addresses the same clean-room assumption
- [[lesson-18-mock-live-services-in-tests]] - mocking eliminates the service availability gap between local and CI
- [[lesson-20-ci-scope-discipline]] - CI scope optimization works within the clean-room constraint
- [[concept-isolation]] - CI's clean-room isolation reveals all implicit environment dependencies

## Validation

**Discovered**: Feb 2026 in Cohezion CI/CD pipeline setup
**Status**: Validated -- CI environment parity now maintained across project
