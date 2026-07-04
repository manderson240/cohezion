---
name: lemonade-gbnf-structured-output
description: |
  Get structured JSON from Lemonade :13305 NPU tier (llama3.2-1b-FLM) using
  native GBNF grammar mode. Use when: (1) NPU returns malformed JSON for tool
  calls or classifiers, (2) evaluating outlines/guidance libraries and finding
  they don't enforce structure on Lemonade, (3) CompoundExecutor tool dispatch
  needs schema-validated responses, (4) task_classifier needs guaranteed JSON
  output. Key insight: outlines' response_format is silently ignored by the NPU
  tier; llama.cpp native grammar field works directly via raw requests.
author: Claude Code
version: 1.0.0
tags: [lemonade, npu, gbnf, structured-output, outlines, task-classifier, compound-executor]
---

# Lemonade GBNF Structured Output

## Problem

NPU tier (llama3.2-1b-FLM on Lemonade :13305) occasionally returns malformed JSON.
The `outlines` library's BlackBox path just passes `response_format` to the server,
which the NPU tier **silently ignores** — producing no structured output enforcement.

## Key Discovery

llama.cpp native `grammar` field works directly on :13305 without any new dependencies:

```bash
curl -X POST http://localhost:13305/v1/chat/completions \
  -d '{"grammar": "root ::= (\"yes\" | \"no\")", "model": "llama3.2-1b-FLM", ...}'
# → "yes"  (constrained)
```

The `grammar` field is a GBNF (GGML BNF) grammar string applied at the token level.

## Solution

Use `src/cohezion/inference/structured_npu.py` (created 2026-06-23):

```python
from cohezion.inference.structured_npu import npu_structured_json

schema = {
    "properties": {"node": {"type": "string"}, "confidence": {"type": "number"}},
    "required": ["node", "confidence"],
}
result = npu_structured_json("Classify: 'What is HIHO?' Reply with node and confidence.", schema)
# → {"node": "npu", "confidence": 0.85}
```

The module converts a minimal JSON schema to GBNF grammar and calls `:13305` via raw `requests`.

## Why NOT outlines

| Approach | Works? | Why |
|----------|--------|-----|
| `outlines.from_openai(lemonade_client)` | ❌ | NPU ignores `response_format` |
| `outlines[llamacpp]` direct | ✅ | But loads 2nd model copy — ~1.3 GB extra RAM |
| Native `grammar` via `requests` | ✅ | No extra deps, no extra RAM |

## GBNF Primer

```
root ::= object
object ::= "{" ws fields ws "}"
fields ::= field ("," ws field)*
field ::= key ws ":" ws value
key ::= "\"" [a-zA-Z_]+ "\""
value ::= string | number | boolean
string ::= "\"" [^"]* "\""
number ::= "-"? [0-9]+ ("." [0-9]+)?
boolean ::= "true" | "false"
ws ::= [ \t\n]*
```

## Verification

```bash
curl -s -X POST http://localhost:13305/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model":"llama3.2-1b-FLM","messages":[{"role":"user","content":"yes or no?"}],
       "grammar":"root ::= (\"yes\" | \"no\")","max_tokens":5}' \
  | python3 -c "import sys,json; print(json.load(sys.stdin)['choices'][0]['message']['content'])"
```

Expected: `yes` or `no` — never prose.
