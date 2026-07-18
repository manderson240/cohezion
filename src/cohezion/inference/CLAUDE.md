# Inference Module — Local Context

Routing, classification, local model tiers. Root `CLAUDE.md` applies.
Omitted: compound loop internals, web UI, Kaggle.

**Read `docs/SILICON_DOCTRINE.md` before writing ANY code that calls a model**
— one page: measured NPU/iGPU/CPU leverage, thinking-model rules, the blessed
call path (`gauntlet._call_model`), and the token law (local ≈ unlimited,
cloud = metered).

## THE ONLY PORT THAT MATTERS

```
:13305  — Lemonade OmniRouter (NPU + iGPU + CPU on demand)
```

Dedicated per-port servers (:13306 NPU, :13307 iGPU, :13309 CPU) are **offline and redundant**.
Do NOT start them, chase them, or reference them as primary inference targets.
Do NOT check `curl :13307/...` — check `:13305/v1/models` instead.

```bash
curl -s http://localhost:13305/v1/models | python3 -c \
  "import sys,json; d=json.load(sys.stdin); print([m['id'] for m in d['data'][:5]])"
```

## OOM Prevention (CRITICAL — ctx_size=0 crasher)

**Never load a model via :13305 with `ctx_size=0`**. At 2026-06-09 a Qwen3.6-35B at ctx_size=0
mapped ~120GB GTT aperture → hard hang, cold boot required. This is N3 in root harness.md.

Safe load pattern:
```bash
curl -s -X POST http://localhost:13305/api/v1/load \
  -H "Content-Type: application/json" \
  -d '{"model_name": "ModelName", "ctx_size": 16384, "save_options": true}'
```

FLM fleet (safe, XDNA2/NPU): `llama3.2-1b-FLM` (42 TPS), `deepseek-r1-0528-8b-FLM` (10.6 TPS), `gemma3-4b-FLM`.

## Routing Order (cheapest-capable first)

NPU (classify/route/short) → iGPU (code/structured) → CPU (reasoning) → Cloud (last resort only)

`feynman_path_weight(q=0.5, cost=0.0) = 0.500` beats `feynman_path_weight(q=1.0, cost=0.01) = 0.368`
— cloud needs ≥2.72× better quality than local to win (CC2).

## Key Entry Points

| Symbol | File | Role |
|--------|------|------|
| `build_triune_omni_orchestrator()` | `triune_orchestrator.py` | Production: all tiers via :13305 |
| `classify()` | `task_classifier.py` | Returns `ClassifyResult(node, output_type, quality_gate_chars)` |
| `SIGReg` | `sigreg.py` | Epps-Pulley isotropy test; EP ≈ 0.423 for N(0,I) |
| `LemonadeEmbedBridge` | (bridge module) | 768D nomic-embed → 256D FLUME mu |
| `feynman_path_weight` | `fractal_metrics.py` | Local-beats-cloud cost guarantee |

## Classifier Invariants

- **CL1**: `classify('Reply with one word only.').node == 'npu'` and `quality_gate_chars == 0`
- **CL2**: prose "class"/"import" must NOT trigger GPU escalation (needs backtick/newline context)
- **CL3**: "What is X?" / "Describe X." patterns → NPU / short_answer

## AIR (Output Intent) Invariants

- **AIR1**: `output_intent=None` is identity (no change)
- **AIR2**: `output_intent='generation'` upgrades NPU → GPU/long_generation
- **AIR3**: `'lookup'/'summary'` downgrades GPU → NPU; `'action'` upgrades NPU → GPU/code

## TR (Triune Recipe) Invariants — 2026-07-07 goal: right model, right recipe

- **TR1**: `build_gaia_llm_tier(model_id)` with no explicit `temperature` resolves the model's
  card default via `model_card_defaults.get_sampling_defaults()`, NOT a blanket `0.0` for every
  model. Previously every tier in `build_triune_omni_orchestrator()`/`build_reasoning_orchestrator()`
  silently got `temperature=0.0` regardless of model family — an explicit `temperature=` kwarg still
  overrides. **Verification**: `uv run pytest tests/inference/test_triune_orchestrator.py -q` → 4
  passed (`test_tr1_omni_orchestrator_tiers_use_model_card_temperature_not_zero` asserts the 3 default
  tiers get `[0.3, 1.0, 1.0]`, not `[0.0, 0.0, 0.0]`).
- **TR2**: `model_card_defaults.py` (previously an unimplemented stub — both functions raised
  `NotImplementedError`) is now implemented against its own pre-written test suite. Distinct from
  `recipe_guard.py`: `recipe_guard` corrects a model's SERVER-SIDE `recipe_options` via
  `/api/v1/load`; `model_card_defaults` supplies CLIENT-REQUEST sampling defaults for callers like
  `build_gaia_llm_tier`. Both matter — a request can omit a param even when the server recipe is
  correct. **Verification**: `uv run pytest tests/inference/test_model_card_defaults.py -q` → 11 passed.
- **Known gap (Kanban `7d3f05b80839`)**: `lemonade_health.py`'s `probe_lemonade()` is a separate,
  still-unimplemented stub (9 failing tests) — a fleet-level hazard/health detector, not touched by
  TR1/TR2. Not blocking; filed for a future pass.

## Port Bypass Guard

Pattern `\b(11434|1330[6-9])\b` must not appear in `src/cohezion/**` outside the allow-list.
Inline override: `# allow-direct-port: <reason>`. Guard: `scripts/ci/check_inference_port_bypass.sh`.

## Tests

```bash
uv run pytest tests/inference/ -q
uv run pytest tests/inference/test_triune_orchestrator.py -q   # TR1 temperature invariants
uv run pytest tests/inference/test_classifier_thinking_routing.py -q  # AIR1-AIR3
```
