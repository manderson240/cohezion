---
title: Mock Live Services in Tests: Never Call Real APIs from Unit Test Suite
date: 2026-02-23
severity: HIGH
category: testing
tags: [testing, mocking, api, test-isolation, ci-cd]
status: validated
---

# Lesson: Mock Live Services in Tests: Never Call Real APIs from Unit Test Suite

## Context

Tests that call real external services (SurrealDB, Ollama, Anthropic API) are slow, flaky, and fail in CI environments without those services.

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

## Validation

**Discovered**: Feb 2026 in phase 1 production validation
**Status**: Validated -- test suite reliability improved from 60% to 98%
