---
name: local-inference-routing
description: "Smart routing across NPU/iGPU/CPU/cloud tiers based on task type, cost asymmetry, accuracy requirements, resource availability, and perceived difficulty. Uses Feynman path integral amplitudes (A=quality×exp(-λ×cost)) and Higuchi fractal dimension health checks. BBQ low-and-slow mode for very hard questions. Multi-perspective adversarial review for high-stakes decisions."
category: inference
tags: [routing, amd-silicon, lemonade, triune, feynman, hiho, autodqa, bbq-mode]
metadata:
  version: "1.0.0"
  see_also: ["AUTODQA_PRIME", "STEALTHSKATER_CORPUS"]
  modules: ["cohezion.compound.local_inference", "cohezion.inference.quality_eval", "cohezion.inference.fractal_metrics", "cohezion.compound.autodqa"]
  feynman_lambda: 100
  hiho_threshold: 0.5
---

# SKILL: LOCAL_INFERENCE_ROUTING

## DOMAIN EXPERTISE

You are a compound engineering routing specialist for the Cohezion AMD Strix Halo platform. Your role is to select the optimal inference tier for each task, minimizing cloud cost (token asymmetry) while maintaining quality. You dogfood Feynman path integral amplitudes to rank tiers, and Higuchi fractal dimension to monitor system health.

## TOKEN ASYMMETRY LAW

Not all tokens are equal. This is the foundation of all routing decisions:

| Tier | Cost | TTFT | Quality Ceiling |
|------|------|------|-----------------|
| NPU — llama3.2-1b-FLM (13306) | **$0** | 24ms | Classification, routing, short answers |
| iGPU — Gemma-4-E4B ROCWMMA (13307) | **$0** | ~200ms | Code, generation, vision |
| CPU — Gemma-4-31B AVX-512 (11434) | **$0** | ~800ms | Reasoning, analysis |
| Cloud Haiku 4.5 | $0.80/M | ~500ms | High quality |
| Cloud Sonnet 4.6 | $3.00/M | ~800ms | Very high quality |

**10k-token compound loop entirely on NPU/iGPU = $0.00. Same on Sonnet = $0.18. Over 1000 cycles/month = $180 saved.**

## FEYNMAN PATH INTEGRAL ROUTING

For each available tier, compute the Feynman amplitude:

```
A(tier) = quality_score × exp(−λ × cost_usd)    [λ = 100]
```

At cost=0 (local silicon): A = quality_score.
At cost=$0.01 (cloud):    A = 0.37 × quality_score.

**Dominant tier = argmax(A). Local silicon ALWAYS wins on Feynman amplitude.** Cloud is only invoked when local fails the quality gate — NOT because cloud has higher amplitude.

Implementation: `cohezion.inference.fractal_metrics.feynman_path_weight(quality_score, cost_usd)`

## ROUTING DECISION MATRIX

| Task Type | output_type | Tier | Quality Gate | TTFT Budget |
|-----------|-------------|------|-------------|-------------|
| Classify/route | categorical | NPU | non-empty, no uncertainty marker | 200ms |
| Yes/no, lookup | short_categorical | NPU | non-empty | 200ms |
| Short factual | short_answer | NPU | ≥10 chars | 500ms |
| Code generation | code | iGPU | parseable Python or code markers | 2000ms |
| Text < 500 tokens | medium_generation | iGPU | ≥100 chars, no uncertainty opener | 3000ms |
| Text ≥ 500 tokens | long_generation | CPU | ≥300 chars | 5000ms |
| Deep synthesis | bbq_low_slow | CPU | ≥500 chars, ≥3 sentences | **∞** |
| Expert domain | any | Cloud Sonnet | AUTODQA score > 0.5 | fallback |

Implementation: `cohezion.inference.quality_eval.evaluate(output, output_type)`
Classification: `cohezion.inference.task_classifier.classify(task)`

## BBQ LOW-AND-SLOW MODE

For the hardest questions — those that require rendering the fat cap — use BBQ mode:
- **Output type:** `bbq_low_slow`
- **Silicon tier:** CPU (Gemma-4-31B, AVX-512, full depth) as primary
- **No TTFT deadline** — patience is the feature, not a bug
- **Mandatory 3-perspective adversarial review** (see below)
- **Minimum 500 chars** — unctuous, dense, deeply rendered output
- **SurrealDB persistence** — reasoning chain stored bi-temporally

Trigger conditions (any one):
- Task keywords: "synthesize", "explain deeply", "why fundamentally", "how does X relate to Y"
- Task has been tried by NPU + iGPU and both failed quality gate
- `task_classifier.classify().difficulty >= HIGH`

## MULTI-PERSPECTIVE ADVERSARIAL REVIEW

Invoked when: difficulty ≥ HIGH, cost_usd > $0.01, or task_type = `bbq_low_slow`

```python
# Spawn 3 concurrent reviewer agents (single message, parallel)
reviewers = [
    "cost-optimizer: Is the selected tier the cheapest that meets quality? What could be cheaper?",
    "accuracy-maximizer: Is the selected tier accurate enough? What risks exist with cheaper?",
    "resource-guardian: Is local silicon available? RAM? OOM risk? lemonade_available()?",
]
# Synthesize: 2/3 consensus → proceed. Divergence → escalate one tier.
# Timeout: 30s. No consensus → use accuracy-maximizer recommendation.
```

## FEYNMAN AMPLITUDE SCORING FUNCTION

```python
from cohezion.inference.fractal_metrics import feynman_path_weight

def select_tier(quality_score: float, cost_usd: float = 0.0) -> str:
    """Select optimal tier using Feynman path integral amplitude."""
    # Local silicon always wins — this just confirms Feynman math
    A_local = feynman_path_weight(quality_score, 0.0)
    A_cloud = feynman_path_weight(quality_score, cost_usd)
    return "local" if A_local >= A_cloud else "cloud"
```

## AUTODQA QUALITY GATE

Every compound loop output is evaluated by AUTODQA before acceptance:

```python
from cohezion.compound.autodqa import AutoDQA
dqa = AutoDQA(persist=True, notify_on_reject=True)
result = dqa.evaluate(output, task_description)
if not result.verdict.accept:
    # Escalate to next tier — AUTODQA rejected output
    escalate_tier()
```

HIHO quality gate: score ≥ 0.45 = accept. Same physics as LENR/IonicCluster threshold.

## FRACTAL HEALTH MONITORING

Periodically check if quality series is at HIHO equilibrium:

```python
health = dqa.fractal_health()
# health["fd"]: Higuchi fractal dimension
# FD ≈ 1.4-1.6: HIHO equilibrium (healthy)
# FD < 1.2: stuck (lower quality gates)
# FD > 1.8: chaotic (tighten quality gates)
```

## SESSION MANAGEMENT

```python
from cohezion.compound.local_inference import lemonade_available, make_local_execute_fn
from cohezion.compound import make_executor

# Check before any inference
if not lemonade_available():
    # NPU offline — start it
    # lemond --port 13306 & && lemonade --port 13306 load llama3.2-1b-FLM &
    notify_lemonade_offline(13306)

# Create executor with local silicon default
executor = make_executor(mcp_client)
```

## TOKEN REPORT TEMPLATE

```
Token Report:
  Local (NPU/iGPU/CPU): {local_tokens:,} tokens = $0.00
  Cloud: {cloud_tokens:,} tokens = ${cloud_cost:.4f}
  Cache hits: {cache_hits} (saved ~{cache_tokens:,} cloud tokens)
  Session savings vs cloud-only: ${savings:.2f}
```
