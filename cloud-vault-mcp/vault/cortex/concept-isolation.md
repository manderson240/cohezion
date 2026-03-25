---
title: "Concept Isolation"
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

Concept isolation is the practice of ensuring that individual units -- whether knowledge concepts, test cases, or service dependencies -- operate independently without unintended interference from shared state, concurrent access, or external dependencies. In testing, this means mocking live services and using isolated resources per worker. In knowledge management, this means concept notes are self-contained and can be validated independently.

The principle operates at multiple levels of the Cohezion stack: at the knowledge layer (each [[concept]] note is independently meaningful), at the testing layer (each test runs without shared state), and at the infrastructure layer (each service can fail without cascading). Isolation is the enforcement mechanism for [[concept-modularity]] -- modularity is the design goal, isolation is how you achieve it.

## Key Properties

- **Test isolation**: Unit tests must not depend on live services; mock external dependencies to prevent flaky tests and hangs. Real service calls belong in separate integration tests with explicit dependency declarations.
- **Resource isolation**: Parallel test workers need unique resources (temp directories, dynamic ports) to avoid contention. Use `tmp_path` fixtures and dynamic port allocation rather than hardcoded paths and ports.
- **Environment isolation**: Virtual environments must not be shared across concurrent install processes to prevent package corruption. Serialize all installs to a given venv or use separate venvs per worker.
- **Concept isolation**: Knowledge notes should be independently retrievable and useful without requiring their full graph neighborhood. A reader should understand a [[concept]] note from its content alone, even if [[wiki-links]] provide deeper context.
- **Failure containment**: Isolated components fail independently without cascading to unrelated systems. A failed health check on Ollama should not prevent the [[cloud-vault-mcp]] server from serving non-embedding queries.
- **State isolation**: Each test, each agent session, and each CI job should start from a clean, predictable state. Shared mutable state is the primary source of flaky behavior.

## Related Papers

- [[lesson-18-mock-live-services-in-tests]]
- [[lesson-34-test-hang-unmocked-live-service]]
- [[lesson-36-mcp-configuration-requires-end-to-end-test-new]]

## Isolation Anti-Patterns

| Anti-Pattern | Symptom | Fix |
|--------------|---------|-----|
| Shared temp directory | Flaky tests that fail non-deterministically | Use `tmp_path` per test |
| Hardcoded ports | "Address already in use" errors in parallel CI | Dynamic port allocation |
| Live service dependency in unit tests | Tests hang or timeout sporadically | Mock external services |
| Shared venv across concurrent installs | Package corruption, import errors | Serialize installs or separate venvs |
| Global mutable state in test fixtures | Tests pass individually, fail together | Reset singletons between tests |

## Related Concepts

- [[concept-modularity]] -- modularity is the design principle; isolation is the enforcement mechanism
- [[concept-testing]] -- isolated concepts are easier to test and validate independently
- [[runbook-ci-cd-pipeline]] -- CI pipelines enforce isolation by running each job in a clean environment
- [[non-blocking-observability]] -- observability systems must be isolated from the services they monitor

## Key Lesson Links

- [[lesson-32-concurrent-pytest-contention]] — parallel test workers sharing resources cause flaky tests; use worker-unique resource identifiers (tmp_path, dynamic ports)
- [[lesson-25-uv-venv-contention]] — concurrent uv installs to the same venv cause package corruption; serialize all installs to a given venv
- [[lesson-18-mock-live-services-in-tests]] — isolate unit tests from live services with mocks; real service calls belong in separate integration tests

## Primary Sources

- Michael Feathers (2004). *Working Effectively with Legacy Code*. Prentice Hall. Established isolation as prerequisite for testable code.
- Gerard Meszaros (2007). *xUnit Test Patterns*. Addison-Wesley. Defined test isolation patterns including fresh fixture, shared fixture, and test double patterns.

## Relevance to Cohezion

Concept isolation addresses multiple failure modes encountered during Cohezion development: test suites hanging on unmocked live services, concurrent pytest workers corrupting shared resources, and uv venv contention during parallel installs. The linked lessons document each incident and the isolation strategy that resolved it.

At the knowledge layer, concept isolation ensures that each vault note is a self-contained unit of knowledge. When agents retrieve context via `vault_find_relevant_context`, each concept note must be independently useful -- an agent should not need to follow five links to understand a single concept. This property makes the vault robust to partial retrieval and context window constraints.

## Skills

- SANDBOX_ISOLATION_PRIME — Isolation backends for agentic code
