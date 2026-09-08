---
name: gemma4-thinking-mode-output
description: |
  Fix for Gemma-4 thinking-mode models (Gemma-4-E4B-it-GGUF, Gemma-4-E2B-it-GGUF)
  returning empty content via Lemonade /v1/chat/completions. Use when:
  (1) Lemonade response has content="" but reasoning_content is set (thinking models
      put the answer in reasoning_content, not content), (2) model wraps JSON output
      in ```json ... ``` markdown fences, (3) model returns responses too long for
      max_tokens=400 (thinking models need ≥1500 tokens to fit CoT + answer).
  Trigger symptoms: parse failures, empty output, LOSS=100% in bughunt loops,
  or a model scoring 0/N on a benchmark it should pass.
  NOT Gemma-only: any llama.cpp-served thinking model can do this (verified on
  Bonsai-27B-gguf, which matches NO entry in _THINKING_MODEL_MARKERS). In this
  codebase, ALWAYS build chat_fn with build_gaia_llm_tier(), never with a
  hand-rolled _GaiaLLMClientShim — see "Cohezion-specific" section.
author: Claude Code
version: 1.3.0
---

# Gemma-4 Thinking-Mode Output Handling

## Problem

Gemma-4 models in thinking mode (E4B-it-GGUF, E2B-it-GGUF via Lemonade OmniRouter)
return their answer in `reasoning_content`, not `content`. Standard OpenAI-compatible
parsers that only read `content` get an empty string and silently fail.

Additionally:
- JSON responses are wrapped in ` ```json ... ``` ` markdown fences
- Thinking models need more tokens — 400 is too small; use ≥1500

## Solution

### 1. Promote reasoning_content → content

```python
msg = data["choices"][0]["message"]
content = msg.get("content") or msg.get("reasoning_content") or ""
return content.strip()
```

### 2. Strip markdown code fences

```python
if "```" in response:
    import re

    m = re.search(r"```(?:json)?\s*(\{.*?\})\s*```", response, re.DOTALL)
    if m:
        response = m.group(1)
```

### 3. Set max_tokens ≥ 1500

```python
"max_tokens": 1500,  # thinking models need CoT space
```

### 4. Fix double-}} JSON edge case (some model variants)

```python
while candidate.endswith("}}") and not candidate.endswith('"}}'):
    candidate = candidate[:-1]
```

## Context

- Affects: Gemma-4-E4B-it-GGUF (iGPU), Gemma-4-E2B-it-GGUF (CPU/CLaSp)
- Does NOT affect: llama3.2-1b-FLM (NPU) — returns content normally, no CoT
- Lemonade promotes reasoning_content automatically when using the OmniRouter's
  built-in `/v1/chat/completions`, but raw HTTP callers must handle this themselves
- Reference fix in: `scripts/drivers/routine_pyright_bughunt.py` (commit 094b19e58)

## Calibration: ≥1500 is for SHORT prompts — CoT scales with input (v1.2.0, 2026-07-20)

The `≥1500` figure above was calibrated on short prompts. **CoT length scales with
input length**, so it is NOT a universal floor. Measured on Gemma-4-26B-A4B doing
structured JSON extraction from ~24k-char article bodies: `max_tokens=4096` failed
**7 of 22** calls. Raising to `16384` fixed **8 of 8** retries.

Rule of thumb: for long-document extraction, budget `max_tokens` at roughly
**16k**, not 1.5k. Local inference is $0 — a frugal cap only manufactures false
negatives (see the `local-inference-generous-token-budget` memory).

### Diagnosing truncation vs a genuinely bad response

Truncation has a distinctive signature. Check these before blaming the prompt:

| Signal | Meaning |
|---|---|
| `finish_reason: "length"` | Definitive: the cap was hit |
| `content_len: 0` + `reasoning_len: 16580` | All budget spent in CoT; nothing emitted |
| `completion_tokens` == your `max_tokens` exactly | Hit the ceiling |
| JSON error **mid-structure** at line 40+: `Expecting ',' delimiter`, `Unterminated string` | Output was CUT OFF, not malformed |
| All failures cluster at the same wall-clock time (the cap) | Systematic, not content-specific |

A JSON parse error saying `Expecting value: line 1 column 1` means *no JSON at
all* (a real formatting problem). An error deep in the object means **truncation**
— raise `max_tokens`, do not rewrite the prompt.

## Trap: max_tokens too small → silent fallback → uniform garbage scores

When `max_tokens` is too low (e.g. 200), a Gemma-4 thinking model spends ALL tokens on
`reasoning_content` and produces EMPTY `content`. If the caller treats empty content as an
error and falls back to `llama3.2-1b-FLM`, it gets low-quality uniform outputs (e.g. all
`q=0.90`). The pipeline completes with exit 0 — no exception, no warning, all results wrong.

**Detection**: all quality scores in a batch are identical. Example: 60/60 records with `q=0.90`.

**Fix**: use `max_tokens ≥ 1500` for Gemma-4 thinking models, OR replace with a non-thinking
model like `DeepSeek-Qwen3-8B-GGUF` (vulkan, 35.98 TPS) for evaluation/enrichment tasks.

```python
# For evaluation pipelines — prefer non-thinking model
REASON_MODEL = "DeepSeek-Qwen3-8B-GGUF"  # confirmed non-thinking; returns content directly

# If you must use Gemma-4, set max_tokens high enough
"max_tokens": 1500,  # thinking models spend ~800-1200 tokens on CoT alone
```

Confirmed: enrichment script fix in `~/cohezion-labs/catalog/enrich_knowledge_catalog.py`
after switching from Gemma-4-E4B-it-GGUF → DeepSeek-Qwen3-8B-GGUF (2026-06-24).

## Avoid the problem: use llama3.2-1b-FLM for fast structured JSON

For classification/extraction tasks where response is short JSON, skip Gemma-4 entirely:

```python
MODEL = "llama3.2-1b-FLM"  # NPU, 30 TPS, no thinking overhead, ~2s/call
# max_tokens=180 is sufficient; no reasoning_content field to handle
```

`llama3.2-1b-FLM` returns `content` directly, no code fences, no CoT. Use Gemma-4 only
when you need vision, tool-calling, or multi-step reasoning with high quality.

## Trap: str.format() on Python source code in prompt templates

When the prompt contains Python source code with `{variable}` braces, `.format()` raises
`KeyError` on every `{` that isn't a named placeholder:

```python
# WRONG — crashes when source contains {braces}
prompt = "Classify this:\n```python\n{source}\n```".format(source=src)

# RIGHT — use string concatenation for code-containing template parts
prompt = "Classify this:\n```python\n" + source + "\n```"
```

## Robust JSON extraction with brace counting

`re.search(r'\{[^{}]*\}', text)` fails when the JSON has nested objects.
Use brace-depth counting instead:

```python
def extract_json(text: str) -> dict:
    import re, json

    text = re.sub(r"^```(?:json)?\n?", "", text.strip())
    text = re.sub(r"\n?```$", "", text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find("{")
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            depth += (ch == "{") - (ch == "}")
            if depth == 0:
                try:
                    return json.loads(text[start : i + 1])
                except json.JSONDecodeError:
                    break
    m = re.search(r'"role"\s*:\s*"([A-Z+]+)"', text)
    if m:
        return {"role": m.group(1), "wiring_gap": "partial parse"}
    return {"role": "UNKNOWN", "wiring_gap": "parse failed"}
```

## Verification

After applying: bughunt WIN rate went from 0% → 40%+ per batch with Gemma-4-E4B.
After v1.1.0: producer/consumer audit went from 0% parse success → 69%+ with llama3.2-1b-FLM.

---

## Cohezion-specific: use the BUILDER, never the raw shim (v1.3.0, 2026-07-28)

`_GaiaLLMClientShim` is **not** the blessed entry point — `build_gaia_llm_tier()` is.
The builder applies `reasoning_format="none"` (keeping the answer in `content`) and
resolves model-card sampling defaults. Constructing the shim directly skips both.

```python
# WRONG — silently returns "" for any thinking model
chat_fn = _GaiaLLMClientShim(client, model, max_tokens=N, temperature=T).prompt

# RIGHT
from cohezion.inference.gaia_adapter import build_gaia_llm_tier
chat_fn = build_gaia_llm_tier(model, max_tokens=N).agent.prompt
```

### The marker list is a heuristic, not a capability probe

`_THINKING_MODEL_MARKERS = ("gemma-4", "gemma4", "gemma-3", "qwen3", "deepseek-r1")`
is a SUBSTRING match (`*-FLM` excluded — FastFlowLM has no reasoning channel). Any
thinking model whose id misses that list gets no fix and fails silently.

**Verified 2026-07-28:** `Bonsai-27B-gguf` matches no marker →
`finish_reason='length', content=0, reasoning_content=456`.

v1.3.0 adds a fallback in `_GaiaLLMClientShim.prompt`:
```python
return (msg.get("content") or "").strip() or (msg.get("reasoning_content") or "")
```
This makes the marker list an OPTIMISATION rather than a correctness dependency.
`.strip()` is load-bearing — `or ""` alone does not catch `"\n  "`, which is truthy.
Tests: `tests/inference/test_gaia_shim_reasoning_fallback.py` (5 cases, 2 discriminating,
both verified to FAIL against the pre-fix implementation).

### Why this matters beyond parse failures

Two consumers turn an empty string into a WRONG DECISION rather than a visible error:

1. **`skill_refiner`'s adversarial gate** treats an empty reply as fail-open **APPROVE**.
   An unlisted thinking model there is a gate that cannot fail.
2. **A benchmark measures your harness, not the model.** `Bonsai-27B-gguf` scored **0/8**
   on a code-review benchmark — consistent with a plausible external research claim that
   "Q1_0/ternary collapses format compliance before delivering capacity." After the
   fallback fix, same model and same prompts scored **8/8**. Accepting the first result
   would have written a false finding into the permanent record and condemned a 3.54 GB
   model that is actually best-in-class.

**Rule:** before concluding a model is incapable, confirm it is not returning empty
`content`. A 0/N score is a harness hypothesis first, a model verdict second.
