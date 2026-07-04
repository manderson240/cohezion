# Cohezion Inference — Onboarding Guide

**You need local inference.** This guide tells you which function to call.

---

## TL;DR — Decision Tree

```
I want to...
│
├─ Call a model once (not in a compound loop)
│   └─ use: route() / extend_claude()
│
├─ Wire into CompoundExecutor / SkillRefiner
│   └─ use: make_provider()  ← the only thing you need
│
├─ Reason-heavy tasks (deepseek-r1 NPU first)
│   └─ use: build_reasoning_orchestrator()
│
└─ All three nodes in parallel (fan-out)
    └─ use: build_parallel_fleet_orchestrator()
```

---

## Pattern 1 — One-off async call

```python
from cohezion.inference import route, lemonade_available

if lemonade_available():
    result = await route("Summarize this diff...", task="summarization")
    print(result.text)
else:
    # Lemonade OmniRouter (:13305) is offline — fall back to Claude API
    ...
```

`route()` uses the fleet registry (NPU→iGPU→CPU cascade) and returns a `RouteResult`.

---

## Pattern 2 — CompoundExecutor backbone

```python
from cohezion.inference import make_provider
from cohezion.compound.executor import CompoundExecutor

# make_provider() returns None when Lemonade is offline — CompoundExecutor handles None
executor = CompoundExecutor(mcp_client, inference_provider=make_provider())
```

Or use the factory (identical result):

```python
from cohezion.compound import make_executor
executor = make_executor(mcp_client)
```

---

## Pattern 3 — Extend Claude with local pre-filter

```python
from cohezion.inference import extend_claude

result = await extend_claude(
    "Explain this stack trace...",
    claude_model="claude-sonnet-4-6",
)
# NPU/iGPU/CPU tried first; escalates to Claude only on quality gate failure.
```

---

## Pattern 4 — Reasoning-first (deepseek-r1)

```python
from cohezion.inference.triune_orchestrator import build_reasoning_orchestrator

orch = build_reasoning_orchestrator()        # omni_port=13305 default
result = await orch.run("Prove P=NP or refute...")
```

Tier lineup: deepseek-r1-0528-8b-FLM (NPU 10.6 TPS) → Gemma-4-E4B (iGPU) → Gemma-4-31B (CPU).

---

## OmniRouter — the only port you need

All local inference goes through **:13305** (Lemonade OmniRouter). It dispatches to
NPU/iGPU/CPU hardware on demand; you never need to know or hardcode which physical
port serves each tier.

```bash
# Health check
curl -s http://localhost:13305/v1/models | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data'][:5]])"
```

Per-port servers (:13306 NPU, :13307 iGPU, :13309 CPU) are optional and often offline.
The OmniRouter is the single authoritative endpoint.

---

## Builder quick reference

| Builder | Description | Use when |
|---------|-------------|----------|
| `build_triune_omni_orchestrator()` | llama3.2→Gemma-E4B→Gemma-31B via OmniRouter | Default cascade ✓ |
| `build_reasoning_orchestrator()` | deepseek-r1→Gemma-E4B→Gemma-31B via OmniRouter | Math / multi-step reasoning |
| `build_parallel_fleet_orchestrator()` | All 3 nodes dispatched simultaneously | Max throughput |
| `build_triune_orchestrator()` | Legacy per-port cascade | Backwards compat only |

---

## OOM safety (N3 harness invariant)

**Never load a model with `ctx_size=0` on a heavy (≥26B) model** — it allocates the
full KV cache and will hard-hang the machine on Strix Halo with partial memory usage.

`lemonade_available()` is a safe non-blocking probe (no model load, no network write):

```python
from cohezion.inference import lemonade_available

if not lemonade_available():
    return None   # Don't crash, don't block
```

---

## Token accounting

`make_local_execute_fn()` in `compound/local_inference.py` tracks per-session usage:

- `local_tokens` — free (NPU + iGPU + CPU)
- `cloud_cost_usd` — metered (Claude API)
- `cloud_savings_usd` — what the local path saved vs cloud

Access via `get_session_token_record()`.

---

## Tier temperatures (TR1 harness invariant)

| Tier | Temperature | Why |
|------|-------------|-----|
| NPU | 0.0 | Short-context classification; T=0 is coherence-safe |
| iGPU | 0.1 | Medium synthesis; small diversity nudge |
| CPU | 0.3 | Long reasoning chains; avoids deterministic collapse |

These are wired automatically by `build_triune_omni_orchestrator()` and
`build_reasoning_orchestrator()` — you don't need to set them manually.
