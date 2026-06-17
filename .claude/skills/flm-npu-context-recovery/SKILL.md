---
name: flm-npu-context-recovery
description: |
  Fix for FLM (FastFlowLM) NPU inference returning HTTP 500 "the current context does
  not logits computation. skipping" on XDNA2 hardware via Lemonade OmniRouter :13305.
  Use when: (1) llama3.2-1b-FLM or any FLM model returns HTTP 500 on inference,
  (2) lemonade load reports "Model loaded successfully" but inference still fails,
  (3) daemon restart alone doesn't fix it, (4) /v1/health shows model on npu device
  but curl to /v1/chat/completions returns 500. Root cause: browser or other process
  holds a persistent connection to the port, preventing the new lemond from binding
  IPv4 — it starts on IPv6 instead and inherits stale FLM context from the old daemon.
author: Claude Code
version: 1.1.0
---

# FLM NPU Context Recovery

## Problem

FLM backend on XDNA2 NPU returns HTTP 500 permanently:
```
{"error": {"code": 500, "message": "the current context does not logits computation. skipping"}}
```

This persists through:
- `lemonade --port 13305 load llama3.2-1b-FLM` (reports success, inference still fails)
- `pkill -9 lemond && lemond --port 13305 &` (new daemon starts but can't bind IPv4)
- Clearing `~/.cache/lemonade/bin/flm/npu/` (FLM context is in-process memory, not files)

## Root Cause

The Lemonade daemon can't bind IPv4 on :13305 if another process holds a socket on
that port — commonly Chrome or another browser using a Lemonade web UI. The log shows:

```
[Error] (Server) Failed to bind IPv4 HTTP server to 127.0.0.1:13305
```

Despite this error, lemond starts on IPv6 (::1) and accepts requests — but the FLM
inference context is stale because the old daemon's state leaked.

## Solution — API-first (no daemon restart needed, works from sandbox)

```bash
# 1. Unload the stale FLM entry
curl -s -X POST http://localhost:13305/v1/unload \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.2-1b-FLM"}'
# Expected: {"status":"success","message":"Model unloaded successfully"}

# 2. Reload fresh on NPU with bounded ctx_size
curl -s -X POST http://localhost:13305/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.2-1b-FLM", "ctx_size": 16384}'
sleep 3

# 3. Verify
curl -s --max-time 20 http://localhost:13305/v1/chat/completions \
  -H "Content-Type: application/json" \
  -d '{"model": "llama3.2-1b-FLM", "messages": [{"role": "user", "content": "ping"}], "max_tokens": 5}'
```

## Fallback — Full daemon restart (only when lemond itself is down)

```bash
# From a full terminal (not PID-namespaced sandbox — kill won't work inside bwrap):
lsof -i :13305 | grep -v COMMAND | awk '{print $2}' | xargs kill -9 2>/dev/null
sleep 1
lemond --port 13305 &
sleep 4
curl -s -X POST http://localhost:13305/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "llama3.2-1b-FLM", "ctx_size": 16384}'
```

## Auto-Recovery Pattern (for executor HTTP 500 handlers)

```python
def _recover_npu(base_url: str, model: str = "llama3.2-1b-FLM") -> bool:
    import json, time, urllib.request
    try:
        for path, body in [("/v1/unload", {"model_name": model}),
                           ("/v1/load", {"model_name": model, "ctx_size": 16384})]:
            req = urllib.request.Request(f"{base_url}{path}",
                data=json.dumps(body).encode(),
                headers={"Content-Type": "application/json"}, method="POST")
            urllib.request.urlopen(req, timeout=30)
        time.sleep(3)
        return True
    except Exception:
        return False
```

## Verification

Success: response contains `"content"` with text and `"decoding_speed_tps"` around 60+ TPS.

```json
{"choices": [{"message": {"content": "Hello! It's nice to meet you..."}}],
 "usage": {"decoding_speed_tps": 62.66, "prefill_speed_tps": 92.82}}
```

Failure: still returns `"the current context does not logits computation"`.

## Key Signals

| Signal | Meaning |
|--------|---------|
| `Failed to bind IPv4 HTTP server to 127.0.0.1:13305` in lemond log | Something holds the port — run `lsof -i :13305` to find it |
| `FLM binary found at: flm` (not full path) | FLM cache was cleared; lemond finding it via PATH — OK |
| `FLM binary found at: /home/.../.cache/lemonade/bin/flm/npu/flm` | Normal cached path |
| `WebSocket) Configured port: 9003` (not 9002) | Prior instance still running, new one is secondary |

## Notes

- This error is **undocumented** in FastFlowLM/Lemonade GitHub issues as of 2026-06-16
- `force_reload` parameter is not available in Lemonade 10.6.0 (may exist in 10.7+)
- qwen3.5-4b-FLM is 5x slower than llama3.2-1b-FLM on XDNA2 — don't substitute
- After recovery, NPU runs at ~62 TPS decode / ~92 TPS prefill on XDNA2
