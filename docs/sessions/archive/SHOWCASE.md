# Cohezion — Reviewer Showcase

**One-page guide for reviewers.** Cohezion is a research platform for building, evaluating, and orchestrating agentic AI on a physics-grounded training manifold — backed by a local inference fleet that runs the whole Gemma 4 family across NPU, iGPU, and CPU on AMD Strix Halo.

---

## 5 Files That Capture the Core

| Read this | To understand |
|-----------|---------------|
| [`src/cohezion/inference/fleet.py`](src/cohezion/inference/fleet.py) | Unified `route()` / `extend_claude()` over 4 silicon lanes + cloud fallback |
| [`src/cohezion/inference/registry.py`](src/cohezion/inference/registry.py) | Model × Lane × Task registry — the single source of truth for routing |
| [`src/cohezion/sandbox/isolation.py`](src/cohezion/sandbox/isolation.py) | COW filesystem + Linux namespace + network isolation for agent episodes |
| [`src/cohezion/environments/manifold_env.py`](src/cohezion/environments/manifold_env.py) | OpenAI Gymnasium env on a 12D Riemannian manifold — OpenEnv-compatible |
| [`src/cohezion/core/symmetry_hardware_bridge.py`](src/cohezion/core/symmetry_hardware_bridge.py) | SU(2) spinor coherence → TurboQuant KV-cache rotation axis (physics→silicon bridge) |

---

## 4 Demos That Prove It

| Command | What you see | Runtime |
|---------|--------------|---------|
| `uv run pytest tests/inference/ -q --no-cov` | 25 tests pass covering registry, health, and fleet routing | ~2 s |
| `uv run python -c "from cohezion.inference import check_fleet, format_fleet_summary; print(format_fleet_summary(check_fleet(force=True)))"` | Live status across NPU :13306 / iGPU :13307 / iGPU :13308 / CPU :13309 / Ollama :11434 / Claude | ~1 s |
| `scripts/symphony_warmstart.sh` | Full 4-lane Gemma 4 fleet comes online (E2B on NPU, E4B on iGPU ROCWMMA, 26B-A4B on iGPU Unified, 31B on CPU) | 30–60 s |
| `make validate` | 23 compound-engineering loop checks | ~18 s |

---

## Strix Halo Symphony — The Inference Fleet

The signature capability: all four Gemma 4 variants running locally on heterogeneous AMD silicon, orchestrated through one Python API.

| Lane | Port | Model | Role (manifest translation) |
|------|------|-------|-----------------------------|
| **NPU (XDNA 2)** | `:13306` | Gemma-4-E2B-it-GGUF | Sensing / *Fire by Friction (Doer)* |
| **iGPU ROCWMMA** | `:13307` | Gemma-4-E4B-it-GGUF | Governance / *Electric Fire (Knower)* |
| **iGPU Unified** | `:13308` | Gemma-4-26B-A4B-it-GGUF (MoE) | Reasoning / *Solar Fire (Thinker)* |
| **CPU AVX-VNNI** | `:13309` | Gemma-4-31B-it-GGUF | Architect / Safety |

**TurboQuant** (Google Research, ICLR 2026) is activated on the NPU path via Omnibus `cache` gateway, which sets `TRITON_AMD_WMMA=1` and `HSA_OVERRIDE_GFX_VERSION=11.5.1` to unlock the gfx1151 hardware identity. The SU(2) spinor axis is injected into each inference payload as `turboquant_axis`, aligning KV-cache random rotation with the agent's coherence state.

**Usage:**

```python
from cohezion.inference import route, extend_claude

# Task-affine routing across the fleet
result = await route("Summarize this commit diff...", task="summarization")
# => Model=Gemma-4-E2B-it-GGUF, Lane=npu, cost=$0.00

# Claude-availability extension: local first, cloud only if needed
result = await extend_claude(prompt, claude_model="claude-sonnet-4-6")
# => If local output passes quality gate, saved ~$0.003–0.015 per call
```

**Verified end-to-end** 2026-04-18: `route("Reply with a single word: ping", task="routing")` → dispatched to NPU → returned "ping" in 3.8 s at $0 cost. See `docs/archaeology/INFERENCE_AUDIT.md` for the full probe.

---

## Why This Matters for Training Universes

Universes-scale agent training means 1000s of env-eval cycles per iteration. Each cycle typically contains one or more LLM calls. Two axes matter: **latency** and **cost**.

### Latency — the bigger win for training loops

Unlike cost, you can't buy more wall-clock time. Measured via live `route(..., stream=True)` against NPU Gemma-4-E2B on 2026-04-18, 5 warm calls, reasoning-mode SSE streaming:

| Metric | NPU Gemma-4-E2B (measured) | Claude API typical |
|--------|------------------------------|--------------------|
| **TTFT p50** | **80 ms** | 500–1500 ms |
| **TTFT range (5 calls)** | **80–86 ms** (tight) | 500–2500 ms |
| Full-response latency (16 tok) | 196–205 ms | ~1000–3000 ms |
| Sustained throughput | ~80 tokens/sec | ~60–120 tokens/sec |
| **TTFT speedup** | **6–19× faster** | baseline |

Reproduce with:

```
make demo-universes                        # uses streaming mode
make health-fleet                           # live probe
```

A 5-step agent reasoning chain with one LLM call per step:
- **Claude API** @ 1000 ms TTFT × 5 ≈ 5 s minimum
- **NPU fleet** @ 80 ms TTFT × 5 ≈ 400 ms minimum
- **→ 12.5× faster agent-rollout wall-clock** — every training iteration compounds this gap

### Cost — the second-order win

| Claude-only (for reference) | Amount |
|-----------------------------|--------|
| 1000-call batch at Haiku rates | ~$5 |
| 1000-call batch at Sonnet rates | ~$25 |
| 1000-call batch at Opus rates | ~$100 |
| **1000-call batch on local NPU** | **$0** |

### Plus: determinism, sandboxing, data locality

- **Determinism**: Local models with fixed seeds give reproducible training traces; API calls don't.
- **Sandboxing fit**: Local endpoints stay inside the agent's COW filesystem + namespace — no network exfil risk from a sandboxed rollout.
- **Data locality**: Training data never leaves the machine — relevant if Universes-team evals involve sensitive test scenarios.

`extend_claude()` is a drop-in wrapper. Quality gate defers to Claude only when local confidence is insufficient. Your directive — **"extend Claude availability"** — rendered as a callable function.

---

## 3 Competition Results (Execution Evidence)

- **Kaggle Measuring AGI** (March 2026) — epistemic humility benchmarks via R-Zero Challenger/Solver swarm
- **Luma AMD Speedrun** (March 2026) — 510 evolution cycles, 157 adversarial prunes, custom Triton/HIP kernels for AMD MI355X
- **BlueQubit Quantum Challenge** — optimization submission for "Little Dimple" problem

See `docs/competitions/` for reproducers.

---

## 3 Platform Metrics

- **5,200+ passing tests** across 13 CI/CD configurations (2026-04-01)
- **152K LOC** production multi-agent platform — 579 Python modules
- **27.3% cost savings** via `CostAwareRouter` (see `src/cohezion/swarm/cost_aware_router.py`)

---

## Architecture in One Diagram

```
            Agent prompt
                │
                ▼
      ┌─────────────────────────┐
      │ cohezion.inference.route│ ◄─── SymmetryHardwareBridge
      └─────────────────────────┘     (turboquant_axis injection)
                │
                ▼
     ┌──────────┬─────────┬─────────┬────────┬──────────┬────────┐
     ▼          ▼         ▼         ▼        ▼          ▼        ▼
   NPU        iGPU      iGPU       CPU     Ollama    Ollama    Claude
   :13306    :13307    :13308    :13309   :11434   :cloud    API
   E2B        E4B       26B       31B    phi4,...  gemini-3  haiku|
   FLM       ROCWMMA   ROCWMMA   AVX-VNNI         flash,...  sonnet|
                                                             opus
     │          │         │         │
     └──────────┴─────────┴─────────┴──────────┐
                                               ▼
                                     JourneyTracker + JEPA
                                     (12D trajectory + plausibility)
```

---

## Universes-Role Qualification Matrix

| Job requirement | Cohezion artifact |
|-----------------|-------------------|
| Advanced agentic environments | `ManifoldEnv`, `SwarmEnv`, `ArcEnv` (Gymnasium + PettingZoo) |
| Rigorous capability evaluations | `UniverseEvaluator`, `benchmark_fleet.py`, competition corpus |
| Sandboxing / containerization / VMs | `sandbox/isolation.py` (COW + namespaces + veth/bridge) |
| LLM training / fine-tuning / evaluation | Gemma 4 fleet + `extend_claude()` quality gating |
| RL environments / simulation systems | 12D manifold + JEPA world-model plausibility checks |
| Distributed systems | SwarmEnv multi-agent + 6-lane inference orchestration |
| Large-scale ML infrastructure | Compound engineering loop + JourneyTracker + Omnibus gateways |
| Published ML research | TurboQuant (ICLR 2026) integration + physics-grounded environments |
| Senior technical experience | 152 K LOC + 5,200 tests + 3 live competitions |
