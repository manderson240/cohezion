---
name: lemonade-gpu-lru-500-recovery
description: |
  Diagnosis and fix for HTTP 500 errors from the Lemonade OmniRouter (:13305) on
  GPU/iGPU-classified tasks (node=gpu or node=igpu). Use when:
  (1) local_executor logs "OmniRouter HTTP 500 for task X" for tasks that should route
      to Gemma-4-E4B-it-GGUF or similar vulkan models,
  (2) lemond journal shows "Evicted model: <name>" + "waiting for GPU driver cleanup"
      immediately before the 500s,
  (3) 500s are transient (NPU tasks and later GPU tasks succeed normally).
  Root cause: OmniRouter auto-loads a newly downloaded model → LRU evicts an existing
  model → vulkan GPU driver cleanup takes iGPU backend offline for ~200-500ms →
  in-flight requests to the evicted/other vulkan models return HTTP 500.
author: Claude Code
version: 1.0.0
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

## Related

- `flm-npu-context-recovery` — same pattern for FLM/NPU stale context
- Harness N1: auto-load anomaly documentation
- Harness N3: ctx_size=0 OOM crasher (different failure mode — this is transient, not OOM)
