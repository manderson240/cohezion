---
name: maker-checker
description: Asymmetric Maker-Checker verification for CompoundExecutor — fast Maker, higher-effort Checker via Lemonade :13305
version: "1.0.0"
tags: [compound, loop-engineering, verification, maker-checker, lemonade, asymmetric]
---

# Maker-Checker Pattern — Asymmetric Verification

## Purpose

Implements the asymmetric Maker-Checker pattern from loop engineering research
(lushbinary.com/blog/loop-engineering-ai-coding-agents-guide/):

- **Maker**: fast execution tier (NPU/iGPU via Lemonade :13305)
- **Checker**: higher-effort verification tier (separate model, separate inference budget)

The Checker is always a SEPARATE concern from the Maker — not the same agent re-reading
its own output. Asymmetry is the key: the Checker uses a richer model with more
reasoning budget to catch what the fast Maker missed.

## Module

`src/cohezion/compound/maker_checker.py`

## Key Components

### CheckerResult
- `verdict`: "pass" | "fail" | "partial" | "skipped" | "error"
- `confidence`: 0.0–1.0
- `reason`: one-sentence explanation
- `latency_seconds`: wall-clock time
- `model`: which model was used for checking

### MakerCheckerVerifier

```python
from cohezion.compound.maker_checker import build_maker_checker

checker = build_maker_checker()  # default: Gemma-4-E4B at :13305

# Synchronous (waits up to timeout_seconds=8.0):
result = checker.verify(task_description, maker_output)

# Async with bounded timeout (preferred in executor):
result = checker.verify_async(task_description, maker_output)

metrics.update(result.to_metrics_dict())
# → checker_verdict, checker_confidence, checker_reason, checker_latency_s, checker_model
```

## Checker Model

**Gemma-4-E4B-it-GGUF** at Lemonade :13305
- Always present in Strix Halo catalog
- ctx=16384 (N3-safe)
- Fast iGPU for bounded verification latency

Note: Granite-4.1-8B was the original intent but is NOT in the Strix Halo catalog. Gemma-4-E4B
is the correct alternative.

## System Prompt

```
You are a rigorous output verifier. Given a task description and the output produced 
by an AI assistant, evaluate whether the output correctly addresses the task.
Respond with exactly one JSON object:
{"verdict": "pass"|"fail"|"partial", "confidence": <0.0-1.0>, "reason": "<one sentence>"}
Do not include any other text.
```

## Integration Points

- **CompoundExecutor Step 3.5**: `checker.verify_async(task_description, output)`
- **ExecutorFactory**: auto-creates via `build_maker_checker()`
- **Non-blocking**: `verify_async()` runs in background thread, returns "skipped" on timeout
- **Additive**: checker verdict is logged to metrics but NEVER blocks the result

## Design Rationale

The 8-second bounded timeout (`verify_async`) ensures the checker never blocks the user
from receiving their result. A "skipped" verdict (timeout) is better than a delayed result.

Input truncation: task_description[:800], maker_output[:1200] — fits comfortably in
Gemma-4-E4B's 16K context with system prompt overhead.

## Source

lushbinary.com loop engineering guide — Maker-Checker split as component #1 of 6-component
outer loop. arXiv:2602.19065 (Agentic Problem Frames) validates asymmetric verification
as a reliability invariant separate from execution.
