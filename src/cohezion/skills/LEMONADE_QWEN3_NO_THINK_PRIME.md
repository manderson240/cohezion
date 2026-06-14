---
name: lemonade-qwen3-no-think
description: "Diagnose and fix Qwen3 thinking-mode in Lemonade llamacpp backends where the model fills reasoning_content and produces empty content. Use the /no_think system message, NOT extra_body enable_thinking=false (that is a cloud-API parameter ignored by llamacpp)."
---

# SKILL: LEMONADE_QWEN3_NO_THINK_PRIME

## DOMAIN EXPERTISE

Diagnosing and suppressing Qwen3 extended-thinking mode in local Lemonade llamacpp backends.

## SYMPTOM

Qwen3-*-GGUF models served via llamacpp in Lemonade default to chain-of-thought (thinking) mode.
The model fills `reasoning_content` with all tokens and returns an empty `content` field.

```json
{
  "choices": [{
    "finish_reason": "length",
    "message": {
      "content": "",
      "reasoning_content": "Okay, let me think... [200 tokens of reasoning]"
    }
  }]
}
```

Increasing `max_tokens` only extends the think loop — it never produces output.

## ROOT CAUSE

Qwen3 llamacpp templates support a `/no_think` system-message instruction that bypasses
the reasoning phase and routes tokens directly to `content`.

## FIX

Prepend a system message with `content: "/no_think"` before the first user message:

```python
messages = [
    {"role": "system", "content": "/no_think"},
    {"role": "user",   "content": your_prompt},
]
```

**Do NOT use** `extra_body: {"enable_thinking": false}` — this is a cloud Qwen API parameter
that is silently ignored by Lemonade's OpenAI-compat layer.

## ALREADY HANDLED — USE PROVIDED CLIENTS

The fix is wired in two modules. New callers should not reimplement:

| Module | Class / function | Behavior |
|--------|-----------------|----------|
| `cohezion.inference.direct_tier` | `DirectLemonadeTier` | Auto-prepends `/no_think` for `_NO_THINK_MODELS` |
| `cohezion.compound.fleet_client` | `LemonadeRouterClient.chat()` | Same `_NO_THINK_MODELS` check |
| `cohezion.compound.fleet_client` | `fleet_review()` | Uses `LemonadeRouterClient.chat()` |

To add a new Qwen3 model, add its `model_name` to `_NO_THINK_MODELS` in **both** files.

## AFFECTED MODELS (2026-06-07)

```python
_NO_THINK_MODELS = frozenset({
    "Qwen3-0.6B-GGUF",
    "Qwen3-8B-GGUF",
    "Qwen3-14B-GGUF",
    "Qwen3.5-35B-A3B-GGUF",
    "Qwen3.5-4B-MTP-GGUF",
})
```

## VERIFICATION

- Without `/no_think`: `content=""`, `reasoning_content` = full budget, `finish_reason=length`
- With `/no_think`: `content="[answer]"`, `finish_reason=stop`, latency ~500ms
- Confirmed on Qwen3-0.6B-GGUF via :13305 router (CPU tier), 2026-06-07

## GOTCHAS

- `extra_body: {enable_thinking: false}` is **silently ignored** by Lemonade llamacpp.
- With `/no_think`, `max_tokens=200-300` is sufficient for short answers.
- Only Qwen3 thinking-mode checkpoints need this. Llama/Granite/Gemma do NOT use it.

## FUTURE HOOKS
- [ ] Router-level `/no_think` injection: have LemonadeRouterClient detect model family
  and inject automatically regardless of caller
- [ ] Streaming support: verify `/no_think` works with `stream=True` responses

## KEY LEARNINGS
- L397: **qwen3-no-think-llamacpp** — `/no_think` system message; `enable_thinking=false` is
  cloud-API-only and has no effect on local llamacpp Lemonade servers.
