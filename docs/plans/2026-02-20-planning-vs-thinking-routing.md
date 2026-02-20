# Planning vs Thinking Mode Routing Implementation Plan

Created: 2026-02-20
Status: PENDING
Approved: Yes
Iterations: 0
Worktree: Yes

> **Status Lifecycle:** PENDING → COMPLETE → VERIFIED
> **Iterations:** Tracks implement→verify cycles (incremented by verify phase)
>
> - PENDING: Initial state, awaiting implementation
> - COMPLETE: All tasks implemented
> - VERIFIED: All checks passed
>
> **Approval Gate:** Implementation CANNOT proceed until `Approved: Yes`
> **Worktree:** Set at plan creation (from dispatcher). `Yes` uses git worktree isolation; `No` works directly on current branch

## Summary

**Goal:** Add a task mode classifier that determines whether an LLM call benefits from "planning mode" (broad exploration, multi-step reasoning, large context) vs "thinking mode" (deep chain-of-thought reasoning, debugging, algorithmic challenges), then dynamically configures Ollama API parameters accordingly.

**Architecture:** Extend the existing `QueryComplexityAnalyzer` in `CostAwareRouter` with a new `TaskModeClassifier` that classifies tasks into PLANNING or THINKING mode. This classifier produces a `TaskMode` that feeds into the Ollama API call sites (`ResilientOllamaClient`, `SmartRouter`, `LocalExpertRouter`) to set mode-specific parameters like `think: true` (for qwen3 models), adjusted `num_ctx`, `num_predict`, and `temperature`.

**Tech Stack:** Python 3.13+, Ollama API (local models), existing CostAwareRouter/SmartRouter infrastructure

## Scope

### In Scope

- New `TaskModeClassifier` that classifies tasks as PLANNING or THINKING (or DEFAULT)
- New `TaskMode` enum and `ModeConfig` dataclass for mode-specific Ollama parameters
- Integration into `CostAwareRouter.select_model()` to include mode in routing decisions
- Integration into `ResilientOllamaClient.generate()` and `SmartRouter.execute()` to apply mode-specific parameters
- Cost/token budget awareness: thinking mode consumes more tokens (chain-of-thought), planning mode needs larger context windows
- Update `InferenceConfig` with mode-specific defaults

### Out of Scope

- Changes to `RequestAlignmentAnalyzer` (separate concern, already handles intent classification)
- Anthropic API integration (this is Ollama-focused, local models only)
- UI or API endpoint changes
- Changes to the compound executor pipeline beyond passing mode through

## Prerequisites

- Existing `CostAwareRouter` and `QueryComplexityAnalyzer` working (verified)
- Ollama running locally with qwen3 and deepseek-r1 models
- No new dependencies required

## Context for Implementer

- **Patterns to follow:** The `QueryComplexityAnalyzer` pattern in `src/cohezion/swarm/cost_aware_router.py:82-244` — keyword-based classification with heuristics, returns an enum, tracks history
- **Conventions:** Dataclasses for configs/decisions, enums for classifications, factory functions for singletons
- **Key files:**
  - `src/cohezion/swarm/cost_aware_router.py` — Main routing with complexity analysis, will be extended
  - `src/cohezion/swarm/token_client.py` — `ResilientOllamaClient.generate()` at line 74, where Ollama API call happens
  - `src/cohezion/swarm/smart_router.py` — `SmartRouter.execute()` at line 364, another Ollama call site
  - `src/cohezion/core/routing/router.py` — `LocalExpertRouter.route_task()` at line 80, third Ollama call site with most dynamic options
  - `src/cohezion/core/config.py` — `InferenceConfig` at line 76, where inference defaults live
- **Gotchas:**
  - Ollama's `think` parameter only works on certain models (qwen3, deepseek-r1). Other models ignore it silently.
  - `ResilientOllamaClient.generate()` uses synchronous `requests.post` (not httpx), so the options dict goes in the JSON body
  - All model costs in `CostAwareRouter` are $0.00 (local models). The "cost" difference between modes is token count, not dollar cost
  - The `CostAwareRouter` singleton has a `reset()` method used in tests via `conftest.py` — new state must be reset there too
- **Domain context:**
  - **Planning mode** = tasks needing broad context (large `num_ctx`), multi-step reasoning, structured outputs. Examples: "design an architecture", "implement across multiple files", "refactor this module"
  - **Thinking mode** = tasks needing deep chain-of-thought (enable `think: true`), higher `num_predict` for reasoning traces, reasoning-focused model preference. Examples: "debug this error", "optimize this algorithm", "solve this logic puzzle"
  - Ollama's `think` parameter enables internal chain-of-thought for supported models (qwen3, deepseek-r1), which produces better reasoning but uses more tokens

## Progress Tracking

**MANDATORY: Update this checklist as tasks complete. Change `[ ]` to `[x]`.**

- [ ] Task 1: TaskMode enum and ModeConfig dataclass
- [ ] Task 2: TaskModeClassifier with keyword/heuristic classification
- [ ] Task 3: Integrate mode into CostAwareRouter
- [ ] Task 4: Apply mode parameters at Ollama call sites
- [ ] Task 5: Integration test for end-to-end mode routing

**Total Tasks:** 5 | **Completed:** 0 | **Remaining:** 5

## Implementation Tasks

### Task 1: TaskMode enum and ModeConfig dataclass

**Objective:** Define the core data types for task mode classification — a `TaskMode` enum (PLANNING, THINKING, DEFAULT) and a `ModeConfig` dataclass that holds mode-specific Ollama parameters.

**Dependencies:** None

**Files:**

- Create: `src/cohezion/swarm/task_mode.py`
- Test: `tests/swarm/test_task_mode.py`

**Key Decisions / Notes:**

- `TaskMode` enum: `PLANNING`, `THINKING`, `DEFAULT` (fallback, no mode-specific params)
- `ModeConfig` holds: `think` (bool), `num_ctx_multiplier` (float), `num_predict_multiplier` (float), `temperature_override` (float | None), `preferred_models` (list[str])
- Follow the `QueryComplexity` enum pattern from `cost_aware_router.py:46-52`
- Include a `get_mode_config(mode: TaskMode) -> ModeConfig` factory that returns preset configs:
  - PLANNING: `think=False`, `num_ctx_multiplier=2.0`, `num_predict_multiplier=1.5`, `temperature=0.5`, preferred models = large-context models
  - THINKING: `think=True`, `num_ctx_multiplier=1.0`, `num_predict_multiplier=2.0`, `temperature=0.3`, preferred models = reasoning models (deepseek-r1, phi4)
  - DEFAULT: neutral multipliers (1.0), no overrides

**Definition of Done:**

- [ ] All tests pass (unit)
- [ ] No diagnostics errors
- [ ] `TaskMode.PLANNING`, `TaskMode.THINKING`, `TaskMode.DEFAULT` are importable
- [ ] `get_mode_config(TaskMode.THINKING).think` returns `True`
- [ ] `get_mode_config(TaskMode.PLANNING).num_ctx_multiplier` returns `2.0`

**Verify:**

- `uv run pytest tests/swarm/test_task_mode.py -q`

### Task 2: TaskModeClassifier with keyword/heuristic classification

**Objective:** Build a classifier that analyzes task descriptions and returns a `TaskMode`. Uses keyword matching and heuristics (similar pattern to `QueryComplexityAnalyzer`).

**Dependencies:** Task 1

**Files:**

- Modify: `src/cohezion/swarm/task_mode.py` (add classifier to same module)
- Test: `tests/swarm/test_task_mode.py` (extend)

**Key Decisions / Notes:**

- Planning keywords: "design", "architecture", "multi-step", "implement across", "refactor module", "plan", "organize", "structure", "multi-file", "component", "system"
- Thinking keywords: "debug", "algorithm", "optimize", "solve", "logic", "puzzle", "prove", "mathematical", "trace", "root cause", "performance bottleneck"
- Heuristics: long prompts with code blocks → THINKING; prompts mentioning multiple files/components → PLANNING; short factual prompts → DEFAULT
- The classifier should also accept an optional `operation_type` hint (from SmartRouter's TaskType) to improve accuracy
- Track classification history for analytics (same pattern as `QueryComplexityAnalyzer.history`)

**Definition of Done:**

- [ ] All tests pass (unit)
- [ ] No diagnostics errors
- [ ] `classify("debug this segfault in the allocator")` returns `TaskMode.THINKING`
- [ ] `classify("design a caching layer across 5 modules")` returns `TaskMode.PLANNING`
- [ ] `classify("what is Python")` returns `TaskMode.DEFAULT`
- [ ] At least 10 test cases covering edge cases and ambiguous inputs

**Verify:**

- `uv run pytest tests/swarm/test_task_mode.py -q`

### Task 3: Integrate mode into CostAwareRouter

**Objective:** Extend `CostAwareRouter.select_model()` to include task mode in routing decisions. The `ModelRoutingDecision` gets a new `mode` field, and model selection considers mode preferences.

**Dependencies:** Task 2

**Files:**

- Modify: `src/cohezion/swarm/cost_aware_router.py`
- Modify: `tests/swarm/test_cost_aware_router.py`

**Key Decisions / Notes:**

- Add `mode: TaskMode` field to `ModelRoutingDecision` dataclass
- In `select_model()`, run `TaskModeClassifier.classify(query)` alongside complexity analysis
- When mode is THINKING and complexity is COMPLEX, prefer deepseek-r1 (reasoning model) over phi3
- When mode is PLANNING, prefer large-context models (qwen3-coder with 65K+ context)
- Add `mode_config: ModeConfig` to `ModelRoutingDecision` so downstream consumers can apply parameters
- Token estimation: multiply `EXPECTED_TOKENS[complexity]` by `mode_config.num_predict_multiplier` for budget checks
- Ensure existing tests still pass — the mode field has a `DEFAULT` default that preserves backward compatibility
- Reset the classifier in `CostAwareRouter.reset()` and in `conftest.py` singleton resets

**Definition of Done:**

- [ ] All existing CostAwareRouter tests still pass
- [ ] New tests verify mode is included in routing decisions
- [ ] `select_model("debug this algorithm")` returns decision with `mode=TaskMode.THINKING`
- [ ] `select_model("design multi-module cache")` returns decision with `mode=TaskMode.PLANNING`
- [ ] Token estimates are adjusted by mode multiplier

**Verify:**

- `uv run pytest tests/swarm/test_cost_aware_router.py -q`
- `uv run pytest tests/swarm/test_task_mode.py -q`

### Task 4: Apply mode parameters at Ollama call sites

**Objective:** Modify the three Ollama API call sites to accept and apply `ModeConfig` parameters — specifically setting `think: true` for thinking mode, adjusting `num_ctx` and `num_predict` multipliers, and overriding temperature when specified.

**Dependencies:** Task 3

**Files:**

- Modify: `src/cohezion/swarm/token_client.py` (`ResilientOllamaClient.generate()`)
- Modify: `src/cohezion/swarm/smart_router.py` (`SmartRouter.execute()`)
- Modify: `src/cohezion/core/routing/router.py` (`LocalExpertRouter.route_task()`)
- Test: `tests/swarm/test_task_mode.py` (add integration-style tests)

**Key Decisions / Notes:**

- `ResilientOllamaClient.generate()`: Add optional `mode_config: ModeConfig | None = None` parameter. When provided, merge mode params into the request JSON:
  - If `mode_config.think` is True, add `"think": True` to the request body (not inside `options`)
  - Multiply `num_predict` by `mode_config.num_predict_multiplier`
  - Override `temperature` if `mode_config.temperature_override` is not None
- `SmartRouter.execute()`: After routing decision, apply mode config to the options dict in the same way
- `LocalExpertRouter.route_task()`: Apply mode config to the `options` dict before sending to Ollama. This router already has the most dynamic options handling, so it's the cleanest integration point
- The `think` parameter in Ollama API goes at the top level of the JSON body, not inside `options`. This is important.
- For models that don't support `think` (phi3:mini, gemma3), silently skip the parameter

**Definition of Done:**

- [ ] All existing tests pass (token_client, smart_router, router)
- [ ] New tests verify `think: true` is set in request body when mode is THINKING
- [ ] New tests verify `num_predict` is multiplied by mode multiplier
- [ ] New tests verify temperature override is applied when specified
- [ ] `think` parameter is only added for models that support it (qwen3, deepseek-r1)

**Verify:**

- `uv run pytest tests/swarm/test_task_mode.py -q`
- `uv run pytest tests/unit/test_smart_router.py -q`

### Task 5: Integration test for end-to-end mode routing

**Objective:** Write integration tests that verify the full pipeline: task description → mode classification → model selection → correct Ollama parameters in the API call. Uses mocked Ollama responses.

**Dependencies:** Task 4

**Files:**

- Create: `tests/swarm/test_mode_routing_integration.py`

**Key Decisions / Notes:**

- Mock `httpx.AsyncClient.post` (or `requests.post` for ResilientOllamaClient) to capture the actual JSON payload sent to Ollama
- Test 3 scenarios end-to-end:
  1. "Debug this memory leak in the allocator" → THINKING mode → `think: true` in payload, deepseek-r1 preferred
  2. "Design a distributed caching system across 8 microservices" → PLANNING mode → large `num_ctx`, structured prompt
  3. "What is the capital of France" → DEFAULT mode → standard parameters, no `think`
- Verify the full chain: `CostAwareRouter.select_model()` → `ModeConfig` → Ollama call payload
- Mock at source: `@patch("cohezion.swarm.token_client.requests.post")` (per project conventions)

**Definition of Done:**

- [ ] All tests pass
- [ ] No diagnostics errors
- [ ] 3 integration scenarios verified with captured Ollama payloads
- [ ] Thinking mode payload includes `"think": true`
- [ ] Planning mode payload has larger `num_ctx` than default

**Verify:**

- `uv run pytest tests/swarm/test_mode_routing_integration.py -q`
- `uv run pytest tests/swarm/ -q` — full swarm test suite passes

## Testing Strategy

- **Unit tests:** Task mode enum/config (Task 1), classifier accuracy with diverse inputs (Task 2), router decision includes mode (Task 3), Ollama payload correctness (Task 4)
- **Integration tests:** End-to-end mode routing with mocked Ollama (Task 5)
- **Manual verification:** Run `CostAwareRouter.select_model()` with sample prompts and inspect decisions

## Risks and Mitigations

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| `think` parameter not supported by all Ollama model versions | Medium | Low | Check model name before adding `think` to payload; maintain a `THINKING_CAPABLE_MODELS` set |
| Mode classification misclassifies ambiguous prompts | Medium | Low | DEFAULT mode is the safe fallback — no mode-specific params applied. Classifier errs toward DEFAULT for uncertain cases |
| Token budget overrun from thinking mode's higher token usage | Low | Medium | Multiply estimated tokens by `num_predict_multiplier` in budget check before execution; BudgetEnforcer still enforces hard limits |
| Breaking existing CostAwareRouter tests | Low | High | `TaskMode.DEFAULT` is the default value, preserving backward compatibility. All existing tests should pass unchanged |

## Open Questions

- None — scope is clear and self-contained

### Deferred Ideas

- Adaptive mode selection based on execution history (use vault patterns to learn which mode works best for which task types)
- Anthropic API `extended_thinking` parameter support (different API, different integration)
- Mode-aware caching (thinking mode responses are longer and should have different cache TTLs)
