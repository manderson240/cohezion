---
title: "Patterns/Runbook Ci Cd Pipeline"
date: 2026-02-19
tags: [concept]
aspect: knower
neural:
  activation: 0.93
  stage: mature
  synapse_in: 15
  synapse_out: 12
---
## Definition

This runbook covers the CI/CD (Continuous Integration / Continuous Deployment) pipeline that validates, tests, and deploys Cohezion vault tooling and infrastructure. The pipeline runs automated checks on every commit -- linting, type checking, unit tests, integration tests, and schema validation -- to catch regressions before they reach production. The pipeline also handles deployment of MCP servers and vault tooling updates.

CI/CD (Continuous Integration / Continuous Delivery) is the practice of automating the build, test, and deployment process so that every code change is automatically validated before reaching production. The CI portion ensures that code integrates cleanly with the existing codebase (tests pass, types check, linting is clean), while the CD portion automates deployment so that validated changes reach production quickly and reliably.

CI/CD for the Cohezion project is distinct from typical application pipelines because the "product" includes both code (cohezion-engine, MCP servers) and structured knowledge (vault notes, frontmatter schemas). Both must be validated. This dual nature means the pipeline must enforce both software engineering quality (type safety, test coverage) and knowledge engineering quality (frontmatter schema compliance, link integrity).

## Key Properties

- **Pre-commit hooks**: Local hooks run linting (ruff), formatting (black), and frontmatter validation before commits enter the pipeline. This "shift-left" approach catches issues at the developer's machine rather than in CI, reducing feedback time from minutes to seconds.
- **Test suite**: `uv run pytest` runs the cohezion-engine test suite; failures block merge. Tests must mock external dependencies per [[concept-isolation]] principles.
- **Type checking**: `basedpyright` or `mypy` ensures type safety across Python code. Type errors are treated as blocking -- no merge without clean types.
- **Schema validation**: Vault note frontmatter is validated against expected field types (tags as arrays, required fields present). This is the knowledge engineering equivalent of type checking.
- **Scope discipline**: CI jobs should only run checks relevant to changed files; avoid full-suite runs on documentation-only changes (see [[lesson-20-ci-scope-discipline]]).
- **Pipeline as code**: CI configuration is version-controlled alongside application code, ensuring pipeline changes are tracked, reviewed, and reversible.
- **Security scanning**: Dependency vulnerability scanning (e.g., `pip-audit`) catches known vulnerabilities before they reach production.

## Pipeline Stages

1. **Lint & Format**: `ruff check` and `black --check` on changed Python files
2. **Type Check**: `basedpyright src/` or `mypy src/` on the cohezion-engine
3. **Unit Tests**: `uv run pytest -q` with mocked external services
4. **Integration Tests**: End-to-end tests against running MCP servers (separate stage, optional)
5. **Vault Validation**: Frontmatter schema checks, broken link detection
6. **Deploy**: Update MCP server configuration if infrastructure files changed

## Related Papers

- [[2026-02-10-phase-a-implementation-complete]]
- [[mcp-infrastructure-architecture]]
- [[runbook-benchmarking-validation]]
- [[troubleshooting-mcp-infrastructure]]

## Primary Sources

- Martin Fowler (2006). *Continuous Integration*. [https://martinfowler.com/articles/continuousIntegration.html](https://martinfowler.com/articles/continuousIntegration.html)
- Jez Humble, David Farley (2010). *Continuous Delivery*. Addison-Wesley. The foundational text on deployment pipeline design.
- Kubernetes Documentation. *Configure Liveness, Readiness and Startup Probes*. Health check patterns used in deployment gates. [https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/](https://kubernetes.io/docs/tasks/configure-pod-container/configure-liveness-readiness-startup-probes/)

## Related Concepts

- [[runbook-health-checks]] -- health checks that run as pre-deployment gates in the pipeline
- [[troubleshooting-mcp-infrastructure]] -- diagnosing failures that CI may surface
- [[data-discipline-prevent-generated-data-in-git]] -- CI enforcement of data discipline rules
- [[concept-testing]] -- vault validation in CI is a form of automated concept testing
- [[concept-isolation]] -- test isolation principles that ensure CI tests are reliable and reproducible
- [[non-blocking-observability]] -- monitoring the pipeline itself for performance degradation and failure trends
- [[data-governance-prevention-through-pre-commit-enforcement]] -- pre-commit hooks as the first CI gate

## Relevance to Cohezion

The CI/CD pipeline is the quality gate for the entire Cohezion project. Without it, broken cohezion-engine code or malformed vault notes could reach the knowledge base and degrade agent performance. The pipeline enforces the lessons learned from operational incidents -- scope discipline, mock discipline, schema validation -- automatically on every commit.

The pipeline's dual validation of code and knowledge is a distinguishing feature. While most CI/CD systems only validate code, Cohezion's pipeline also validates the vault's structural integrity -- checking that [[wiki-links]] resolve, frontmatter schemas are consistent, and concept notes meet quality standards. This ensures that the knowledge base maintains its value as a reliable context source for agents.
