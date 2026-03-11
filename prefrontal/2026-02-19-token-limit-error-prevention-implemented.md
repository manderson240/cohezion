---
title: 'Token Limit Error Prevention Implemented'
date: '2026-02-19'
status: accepted
tags: [decision, token-efficiency, context-management, error-handling]
aspect: thinker
neural:
  activation: 0.448
  stage: growing
  cluster: decisions
---

# Token Limit Error Prevention Implemented

## Context

Agent sessions were intermittently hitting token limit errors when making LLM API calls (particularly to Ollama local models). The root cause was that `max_tokens` was set to a default value that could exceed the model's context window when combined with a long prompt. This caused hard failures mid-session, wasting all tokens spent up to that point and requiring manual intervention to retry with smaller payloads.

The problem was especially acute with local models via [[2026-02-09-ollama-context-management]], where different models have different context window sizes (2K to 128K tokens) and the calling code had no awareness of the target model's limits.

## Decision

Implement a multi-layered defense against token limit errors:

1. **Reduced default `max_tokens`** — changed from unbounded/large default to 512, which fits within all supported models
2. **`calculate_max_tokens()` function** — dynamically calculates the maximum safe response length based on prompt length and model context window
3. **Auto-retry with token reduction** — on `TokenLimitError`, automatically retry with 50% reduced `max_tokens`, up to 3 attempts
4. **CLI configuration** — `--max-tokens` flag allows manual override for specific use cases

## Consequences

**Positive:**
- Zero token limit errors in production since implementation
- Graceful degradation — if the first attempt exceeds limits, the retry mechanism produces a shorter but valid response
- Model-agnostic — works across all Ollama models regardless of context window size
- CLI override provides escape hatch for power users who know their model's limits

**Negative:**
- Default of 512 tokens may truncate long responses — users must explicitly request more via CLI
- Auto-retry adds latency (up to 3 attempts) in the worst case
- `calculate_max_tokens()` requires knowing the model's context window, which is not always available from the API

## Alternatives Considered

**Static max_tokens per model:** Maintain a lookup table of model name to max context window. Rejected because model names and limits change frequently — the table would require constant maintenance.

**Client-side token counting:** Count tokens before sending to estimate if the request will exceed limits. Rejected because accurate token counting requires the model's tokenizer, which varies per model and adds a dependency.

**Fail fast with user message:** On token limit error, immediately surface the error and ask the user to reduce input. Rejected because it interrupts the agent session and requires user intervention — the auto-retry approach is strictly better for the user experience.

## Related

- [[token-efficiency]] — token limit prevention is a concrete implementation of token efficiency principles
- [[context-management]] — context window budget tracking directly relates to preventing token limit errors
- [[token-efficiency-patterns]] — the scoped context reads and model delegation patterns that complement this error prevention
- [[2026-02-09-ollama-context-management]] — the Ollama context management system that this decision improves
- [[2026-02-12-claude-code-context-awareness-codification]] — context awareness codification that includes token budget tracking
