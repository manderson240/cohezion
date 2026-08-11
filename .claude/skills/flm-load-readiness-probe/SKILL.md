---
name: flm-load-readiness-probe
description: |
  Fix for the FLM/NPU load-readiness RACE on Lemonade OmniRouter :13305: POST
  /api/v1/load returns {"status":"success"} BEFORE the FLM backend can serve, so
  chat calls in the next ~30-60s get HTTP 500 {"type":"model_not_loaded"}, and
  /api/v1/health ALSO lags (can show zero FLM models loaded while the model is
  already answering chats). Use when: (1) chat returns 500 "No model loaded: <X>"
  seconds after a load call reported success, (2) an FLM model's failure is about
  to be recorded as model incapacity in a benchmark/gauntlet, (3) writing ANY
  code that loads an FLM model then immediately calls it (benchmarks, routers,
  daemons). DISAMBIGUATION: if the 500s persist beyond ~3 minutes or say
  "context does not logits computation", that is the PERMANENT stale-context
  failure — use flm-npu-context-recovery instead. This skill covers the
  TRANSIENT race only: no daemon restart needed, just probe-until-serving.
author: Claude Code
version: 1.0.0
---

# FLM Load-Readiness Probe (load "success" ≠ serving)

## Problem

Two status surfaces lie during FLM/NPU model startup on :13305:

1. `POST /api/v1/load` returns `{"status": "success"}` while the FLM backend is
   still booting — chat calls in the next ~30–60 s get
   `HTTP 500 {"error":{"message":"No model loaded: <model>","type":"model_not_loaded"}}`.
2. `GET /api/v1/health` lags in BOTH directions — verified 2026-07-21: it showed
   **zero** FLM models loaded while `llama3.2-3b-FLM` was answering chats in 0.9 s.

Consequence: a benchmark, router, or daemon that trusts either surface records a
healthy model as failed (this misattributed a production triage failure to
"HTTPError = maybe incapacity" before the race was found), or a "success" load
that never actually serves.

## Trigger Conditions

- `model_not_loaded` 500s immediately after a load call that reported success
- FLM model "randomly" failing first calls in a benchmark loop but fine later
- `all_models_loaded` in `/api/v1/health` contradicting live chat behavior

## Solution

**The only trustworthy readiness signal is a real 1-token chat returning
non-empty content.** Load, then probe until serving, THEN make scored/production
calls:

```python
def warmup(model: str, max_wait_s: float = 180.0) -> dict:
    t0 = time.monotonic()
    # 1. Load (bounded ctx — N3 discipline)
    urllib.request.urlopen(urllib.request.Request(
        f"{BASE}/api/v1/load",
        data=json.dumps({"model_name": model, "ctx_size": 16384}).encode(),
        headers={"Content-Type": "application/json"}), timeout=300).read()
    # 2. Probe until it actually serves
    probe = {"model": model, "max_tokens": 5, "stream": False,
             "messages": [{"role": "user", "content": "Reply with one word: yes"}]}
    while time.monotonic() - t0 < max_wait_s:
        try:
            r = urllib.request.urlopen(urllib.request.Request(
                f"{BASE}/api/v1/chat/completions", data=json.dumps(probe).encode(),
                headers={"Content-Type": "application/json"}), timeout=90)
            msg = (json.loads(r.read()).get("choices") or [{}])[0].get("message", {}) or {}
            if (msg.get("content") or msg.get("reasoning_content") or "").strip():
                return {"warm": True, "warmup_s": round(time.monotonic() - t0, 1)}
        except urllib.error.HTTPError as e:
            pass  # model_not_loaded while booting — keep polling
        time.sleep(8)
    return {"warm": False, "warmup_s": round(time.monotonic() - t0, 1)}
```

Side benefit for benchmarks: warming every model before scored runs means **all
scored runs are warm** — swap cost is uniformly excluded (record `warmup_s`
separately as the swap cost).

## Verification

Observed 2026-07-21 (Phase 1.1 triage head-to-head): without probe — llama3.2-1b
failed 4/4 calls with `model_not_loaded` (26–60 s each). With load→probe
protocol — all 5 FLM models (1B–35B MoE) ran 2/2 scored runs cleanly; warmup_s
measured 12.5–131.3 s (the 35B took >2 min to actually serve after "success").

## Notes

- ALWAYS print the HTTP error body — the bare status code was misread as model
  incapacity until `{"type":"model_not_loaded"}` was printed.
- A single HTTPError is never evidence of incapacity; re-run behind the probe.
- Related: `flm-npu-context-recovery` (permanent 500s, stale context, daemon-level
  fix); `lemonade-gpu-lru-500-recovery` (iGPU eviction 500s).

## References

- Runner that encodes this: /tmp/claude/triage_h2h.py (Phase 1.1, 2026-07-21)
- Results proving the fix: /tmp/claude/triage_h2h_results.jsonl
- Vault: reports/20260721-gauntlet-adaptive-harness-plan.md Appendix A
