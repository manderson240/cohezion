# Fleet Benchmark Report

- **Generated:** 2026-06-04 12:11:09 EDT
- **Git SHA:** `92be2abb1`
- **Corpus:** 20 deterministic routing prompts available; this run executed 2 (use `--prompts 20` for the full benchmark)
- **Status:** PILOT (n<20, not statistically conclusive)
- **Dispatch:** streaming SSE (`stream=True`) for B/C/D so TTFT is the moment the first reasoning/content chunk arrives; Config A uses `claude -p` (non-streaming, total-latency proxy).

## Fleet health at run time

```
Fleet health @ Thu Jun  4 12:08:19 2026:
  ✗ npu            http://localhost:13306               -  [Errno 111] Connection refused
  ✓ igpu_rocwmma   http://localhost:13307            11ms  17 models
  ✗ igpu_unified   http://localhost:13308               -  [Errno 111] Connection refused
  ✗ cpu            http://localhost:13309               -  [Errno 111] Connection refused
  ✓ ollama         http://localhost:11434            11ms  19 models
  ~ claude         cli:/home/mike-anderson/.local/bin/claude  1142ms  exit 1
  ✓ gemini         cli:/home/linuxbrew/.linuxbrew/bin/gemini  1713ms  0.42.0
```

## Headline table

| Config | Calls (ok/total) | Wall time | TTFT p50 | TTFT range | Cost | Lanes used |
|--------|------------------|-----------|----------|------------|------|------------|
| A — Claude-only | 0/2 | 13.30s | n/a | n/a | $0.00000 | — |
| B — Local-only | 0/2 | 0.00s | n/a | n/a | $0.00000 | — |
| C — Hybrid $0.001 | 0/2 | 0.00s | n/a | n/a | $0.00000 | — |
| D — Hybrid quality≥0.85 | 0/2 | 0.00s | n/a | n/a | $0.00000 | — |

## Derived claims

- (Derived claims unavailable — config A or B did not complete)

---

*Reproduce: `make benchmark-fleet`. V-Model plan: `docs/vmodel/PHASE2_BENCHMARK_PLAN.md`.*
