---
name: thinking-model-quality-gate-stripping
description: |
  Strip <think>...</think> blocks from thinking model output BEFORE quality gate checks.
  Use when: (1) adding DeepSeek R1, Qwen3 ThinkingCoder, or any CoT model to a TieredOrchestrator
  tier; (2) QualityGate.min_chars passes on what appears to be good output but callers receive
  raw XML chain-of-thought; (3) building GAIA tier adapters for thinking models. Critical invariant:
  quality gates must measure stripped text length, not raw output length, or 800-char thinking
  traces mask empty final answers.
author: Claude Code
version: 1.0.0
---

# Thinking Model Quality Gate Stripping

## Problem

Adding a thinking model (DeepSeek R1, Qwen3 ThinkingCoder) to a `TieredOrchestrator` tier
causes two bugs if `<think>` blocks are not stripped before the quality gate:

1. **False gate passes**: An 800-char thinking trace + empty answer passes `min_chars=100`.
   The tier returns garbage — empty or near-empty — as if it were a quality response.
2. **Raw XML to callers**: Downstream code receives `<think>Let me reason...</think>\n\nThe answer`.
   Prompts that expected clean text get XML noise.

## Context / Trigger Conditions

- You see `<think>` or `</think>` in orchestration output
- Quality gate escalation is NOT happening even though final answers are empty/short
- You are wiring `deepseek-r1-0528-8b-FLM`, `Qwen3.6-35B-A3B-ThinkingCoder`, or similar
  to a `TieredOrchestrator` via `build_gaia_llm_tier()`

## Solution

Strip in `GaiaAgentTier.run()` — the single entry point where GAIA model output first enters
the orchestration chain — **before** constructing the `OrchestrationResult`:

```python
# At top of gaia_adapter.py
import re
_THINK_RE = re.compile(r"<think>.*?</think>\s*", re.DOTALL)

def _strip_thinking_tokens(text: str) -> str:
    stripped = _THINK_RE.sub("", text).strip()
    # CRITICAL: fall back to original if strip leaves empty —
    # so quality gate correctly rejects it rather than passing an empty string
    return stripped if stripped else text
```

In `GaiaAgentTier.run()`:
```python
out = await loop.run_in_executor(None, run_fn, prompt)
text = _strip_thinking_tokens(out if isinstance(out, str) else str(out))  # strip BEFORE return
```

## Why not strip in TieredOrchestrator.run() after gate?

If you strip after the gate:
- `min_chars=100` measures raw text → 800-char `<think>` block passes
- Escalation never triggers even when the actual answer is empty
- You silently return thinking traces as "good" output

Stripping before the gate:
- `min_chars=100` measures the *answer* length
- An empty post-strip answer (model only produced thinking) falls back to raw text
  → gate sees short text → escalation fires correctly → next tier runs

## Verification

```python
from cohezion.inference.gaia_adapter import _strip_thinking_tokens

# Normal: extracts answer after </think>
assert _strip_thinking_tokens("<think>trace</think>\n\nThe answer is 42.") == "The answer is 42."

# Empty after strip: falls back to original (gate rejects correctly)
result = _strip_thinking_tokens("<think>only thinking</think>")
assert result == "<think>only thinking</think>"  # NOT empty string

# Passthrough: non-thinking models unaffected
assert _strip_thinking_tokens("Paris is the capital.") == "Paris is the capital."
```

## References

- `src/cohezion/inference/gaia_adapter.py` — implementation
- `src/cohezion/inference/orchestrator.py` — `QualityGate.check()` min_chars logic
- `src/cohezion/inference/triune_orchestrator.py` — `build_reasoning_orchestrator()` tier config
- Awesome-Latent-Space backlog B5: future upgrade path is FLUME latent encoding of COT
  rather than stripping (arXiv:2604.02029 "Hidden Chain-of-Thought Decoding")
