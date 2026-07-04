---
name: gemma4-thinking-mode-output
description: |
  Fix for Gemma-4 thinking-mode models (Gemma-4-E4B-it-GGUF, Gemma-4-E2B-it-GGUF)
  returning empty content via Lemonade /v1/chat/completions. Use when:
  (1) Lemonade response has content="" but reasoning_content is set (thinking models
      put the answer in reasoning_content, not content), (2) model wraps JSON output
      in ```json ... ``` markdown fences, (3) model returns responses too long for
      max_tokens=400 (thinking models need ≥1500 tokens to fit CoT + answer).
  Trigger symptoms: parse failures, empty output, LOSS=100% in bughunt loops.
author: Claude Code
version: 1.1.0
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
    text = re.sub(r'^```(?:json)?\n?', '', text.strip())
    text = re.sub(r'\n?```$', '', text.strip())
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        pass
    start = text.find('{')
    if start >= 0:
        depth = 0
        for i, ch in enumerate(text[start:], start):
            depth += (ch == '{') - (ch == '}')
            if depth == 0:
                try:
                    return json.loads(text[start:i + 1])
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
