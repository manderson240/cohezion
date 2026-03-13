---
title: Mock Live Services in Tests: Never Call Real APIs from Unit Test Suite
date: 2026-02-23
severity: HIGH
category: testing
cost_of_forgetting: "Flaky, slow test suite that fails in CI -- reliability drops from 98% to 60%"
tags: [testing, mocking, api, test-isolation, ci-cd]
status: validated
aspect: knower
neural:
  activation: 0.76
  stage: growing
  synapse_in: 13
  synapse_out: 7
---

# Lesson: Mock Live Services in Tests: Never Call Real APIs from Unit Test Suite

## Context

During Cohezion phase 1 production validation, the test suite called real external services: SurrealDB for agent context storage, Ollama for embedding generation, and the Anthropic API for LLM calls. These tests passed reliably on development machines where all services were running locally. In CI environments -- clean Docker containers without those services -- the same tests either failed immediately (connection refused) or hung indefinitely (see [[lesson-34-test-hang-unmocked-live-service]]).

## Problem

Real service calls in unit tests create three failure categories:

1. **Flakiness**: Tests pass or fail depending on external service availability, not code correctness. A passing test gives false confidence; a failing test may have nothing to do with the code under test.
2. **Slowness**: Network round trips add 100ms-10s per test. An embedding test that takes 5ms with a mock takes 500ms with real Ollama. Across 100 tests, this is the difference between 30 seconds and 50+ seconds.
3. **CI incompatibility**: CI runners do not have SurrealDB, Ollama, or API keys pre-configured. Every new contributor or CI environment requires service setup before tests pass.

Test suite reliability was approximately 60% -- meaning 4 out of 10 CI runs failed for reasons unrelated to code changes.

## Core Learning

**All external service calls in unit tests MUST be mocked. Integration tests (with real services) run separately from the unit suite.**

### Pattern
```python
# WRONG: calling real Ollama
def test_embedding():
    result = ollama.embed("text")  # Real call -- slow and flaky

# RIGHT: mock the client
@patch("src.embeddings.ollama_client")
def test_embedding(mock_ollama):
    mock_ollama.embed.return_value = [0.1] * 768
    result = embed("text")
    assert len(result) == 768
```

## Solution

The test suite was restructured:

1. **All external calls mocked in unit tests**: Using `@patch` at the client level (not individual methods) for cleaner mocks
2. **Integration tests separated**: Created `tests/integration/` directory for tests that need real services, marked with `@pytest.mark.integration`
3. **CI default command**: `pytest -m "not integration"` runs only mocked unit tests. Integration tests run in a separate CI stage with services provisioned.
4. **Mock fixtures centralized**: Common mocks (SurrealDB client, Ollama client) are shared via `conftest.py` fixtures

Result: test suite reliability improved from 60% to 98%, and CI run time dropped from 50+ seconds to under 30 seconds.

## Prevention

- **Mock at the client level**: Patch the client object, not individual methods. This is cleaner and catches new method calls automatically.
- **Use conftest fixtures**: Centralize common mocks so every test file does not reinvent them
- **Separate integration tests by directory**: `tests/unit/` (mocked) vs `tests/integration/` (real services)
- **CI default is unit-only**: Only run integration tests in environments with services provisioned

## Cost of Forgetting

- **60% test reliability** instead of 98%: 4 out of 10 CI runs fail for non-code reasons
- **50+ second CI times** instead of 30 seconds: real network calls dominate test execution time
- **CI environment fragility**: Every service dependency becomes a CI setup requirement
- **Developer frustration**: "Tests fail, retry" becomes the default workflow instead of investigating

## Recommendations

### Do
- Mock at the client level for cleaner tests
- Run integration tests in a separate tests/integration/ directory
- Use pytest -m "not integration" as the default CI command

### Don't
- Call real services from tests/unit/ or unmarked test files
- Use live service responses as expected values in tests (brittle)

## Related Concepts

- [[compound-engineering]] - Reliable test suites enable reliable compound deployment
- [[testing-agent-skills-with-evals]] - The evals framework's four-category approach (outcome, process, style, efficiency) requires properly mocked external services to isolate agent skill under test
- [[lesson-34-test-hang-unmocked-live-service]] - Related failure mode: unmocked live services cause test hangs, not just flakiness
- [[concept-testing]] - mock live services is a foundational testing discipline
- [[concept-isolation]] - mocking is the primary isolation mechanism for external service dependencies
- [[concept-modularity]] - clean module boundaries enable mocking at the client level
- [[lesson-10-gitlab-ci-runner]] - CI environments are clean rooms; mocking eliminates the dependency gap between local and CI

## Validation

**Discovered**: Feb 2026 in phase 1 production validation
**Impact**: Test suite reliability improved from 60% to 98%; CI time from 50s to 30s
**Status**: Validated
