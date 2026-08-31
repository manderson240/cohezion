---
name: lemonade-gpu-lru-500-recovery
description: |
  Diagnosis and fix for HTTP 500 errors from the Lemonade OmniRouter (:13305) on
  GPU/iGPU-classified tasks (node=gpu or node=igpu). Use when:
  (1) local_executor logs "OmniRouter HTTP 500 for task X" for tasks that should route
      to Gemma-4-E4B-it-GGUF or similar vulkan models,
  (2) lemond journal shows "Evicted model: <name>" + "waiting for GPU driver cleanup"
      immediately before the 500s,
  (3) 500s are transient (NPU tasks and later GPU tasks succeed normally),
  (4) v1.2.0 — you see EMPTY embedding vectors / KeyError on `data` and are about to
      blame eviction. That symptom is a TOKEN-LIMIT rejection, not eviction: the router
      answers HTTP 200 with an ERROR BODY, so raise_for_status() passes and ["data"]
      raises KeyError. It fails deterministically by input LENGTH, not timing.
      DO NOT quote a specific limit — it moves with server flags (measured 256 tokens
      / n_ubatch on 2026-07-27, then 512 tokens / nomic context window on 2026-08-06
      after -b 2048 -ub 2048). PROBE it: send one input of growing length and read the
      rejection body, which names the actual ceiling. ~20s, and it is the only
      trustworthy answer.
  Root cause: OmniRouter auto-loads a newly downloaded model → LRU evicts an existing
  model → vulkan GPU driver cleanup takes iGPU backend offline for ~200-500ms →
  in-flight requests to the evicted/other vulkan models return HTTP 500.
author: Claude Code
version: 1.2.0
---

# Lemonade GPU LRU Eviction → HTTP 500 Recovery

## Problem

The Lemonade OmniRouter (:13305) has an auto-load feature: when a request arrives for
a model not currently loaded, it downloads and loads it, evicting the LRU model to make
room. The eviction triggers a vulkan GPU driver cleanup that takes ALL vulkan-based
backends offline for ~200-500ms. Any in-flight or queued requests to vulkan models
during this window return HTTP 500.

In `local_executor.py`, only `node == "npu"` 500s had recovery logic. GPU-tier 500s hit
the bare `else` branch, logged a WARNING, and incremented `fail_counts` — burning toward
cloud escalation with no attempt to recover.

## Diagnosis

Check lemond journal for the eviction+cleanup sequence:

```bash
journalctl --no-pager --since "15 minutes ago" | \
  grep -E "(Evicted model|GPU driver cleanup|failed to load|HTTP 500|500)" | head -20
```

Confirmed pattern (2026-06-17 15:56:38-55):
```
lemond: Evicted model: Qwen3.6-27B-GGUF
lemond: Process terminated, waiting for GPU driver cleanup...
lemond: Loading model: DeepSeek-Qwen3-8B-GGUF  [→ failed, memory full]
# 15 seconds later:
local_executor WARNING: OmniRouter HTTP 500 for task skill-103-TRANSFORMER_ENGINE_F
local_executor WARNING: OmniRouter HTTP 500 for task skill-104-TURBO_QUANT_PRIME
```

## Why GPU tasks (not NPU)

Skill task descriptions are rich multi-line strings with "Apply", "Identify", "Analyze"
keywords → classifier routes to `node=gpu` / `long_generation` → Gemma-4-E4B-it-GGUF
(vulkan). Short task IDs like "TRANSFORMER_ENGINE_F" alone would classify as `node=npu`,
but the actual `task.description` from `run_agentic_loop.py` is ~10 lines long.

Test actual routing:
```python
from cohezion.inference.task_classifier import classify

classify(task.description).node  # "gpu", not "npu"
```

## Fix

Generalize `_recover_npu` → `_recover_model` and add a GPU recovery branch:

```python
elif exc.code == 500 and node in ("gpu", "igpu"):
    gpu_model = model
    resp = None
    if _recover_model(self._base_url, gpu_model):
        logger.info("task %s: GPU recovery succeeded, retrying %s", task_id, gpu_model)
        try:
            resp = _chat_complete(self._base_url, gpu_model, prompt, ...)
        except Exception as exc2:
            return _error_result(task_id, gpu_model, node, str(exc2), returncode=1)
    else:
        return _error_result(task_id, gpu_model, node, "HTTP 500 (GPU recovery failed)", returncode=2)
```

`_recover_model` uses `POST /api/v1/unload` + `POST /api/v1/load` — same as the existing
NPU recovery, just tier-agnostic. The reload brings the vulkan backend back to a known-good
state after the driver cleanup completes.

## Verification

After fix, GPU-tier 500s during LRU eviction windows should:
- Log `"GPU recovery succeeded, retrying <model>"` instead of WARNING
- Complete the task on retry (driver cleanup is done by then)
- NOT increment fail_counts toward cloud escalation

Committed: `67dda91ed` (2026-06-17)

## v1.1.0 — silent empty-vector failures are usually NOT eviction (2026-07-20)

**Correction.** v1.1.0 originally attributed a batch of empty embeddings to LRU
eviction. That was wrong — a plausible story (a long single-model batch on the iGPU)
built on a `KeyError` that was never traced to its actual message. The real cause was
the embedding model's **physical batch size**:

```
input (562 tokens) is too large to process.
increase the physical batch size (current batch size: 256)
```

The failure is **deterministic by input length**, not load-dependent:

| input | result |
|---|---|
| 50 chars | OK, 768 dims |
| 500 chars | OK, 768 dims |
| 2000+ chars | HTTP 500, batch-size error |

A caller doing `d["data"][0]["embedding"]` raises `KeyError` on the error payload, and
a log-and-continue loop then stores `embedding: []`. Observed: **54 chapters stored,
20 embedded** — the row count said complete while semantic retrieval covered ~37% of
the corpus. Retrying is futile because nothing is transient; the same input fails
identically every time.

### Diagnosis order (do this before blaming eviction)

1. **Read the actual error body.** A `KeyError` in your client is not a diagnosis —
   print the response payload. It usually names the real limit.
2. **Sweep input length.** If short inputs pass and long ones fail deterministically,
   it is a batch/context limit, not eviction.
3. Only if failures are *transient and load-correlated* should you suspect eviction.

### Fix

Raise the embedding model's batch size in its recipe (server-side, persisted):

```bash
curl -X POST localhost:13305/api/v1/load -H 'Content-Type: application/json' -d '{
  "model_name": "nomic-embed-text-v2-moe-GGUF",
  "llamacpp_args": "--batch-size 8192 --ubatch-size 8192",
  "save_options": true}'
```

…and cap client-side input as a belt-and-braces guard, since a raised batch size still
has a ceiling.

### The part that was right

Verify against the **store**, never the loop counter:

```sql
SELECT count() FROM chapter WHERE embedding = [];   -- must be 0
```

Any pipeline writing a vector field must assert non-empty coverage at the end.
"N rows written" and "N rows usable" are different numbers. Note also that
`uv run script.py | tail -6` returns *tail's* exit status — a pipeline can report
success while the script returned failure.

## Related

- `flm-npu-context-recovery` — same pattern for FLM/NPU stale context
- Harness N1: auto-load anomaly documentation
- Harness N3: ctx_size=0 OOM crasher (different failure mode — this is transient, not OOM)
