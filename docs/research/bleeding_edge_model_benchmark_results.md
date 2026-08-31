# Bleeding-Edge Frontier Model Benchmark Results (2026)

| Candidate Model | Backend / Tier | Frontier Composite Score | Formal Code Verification | Entropy Density | Avg Speed |
|---|---|:---:|:---:|:---:|:---:|
| **Qwen3-Coder-30B-A3B** | `lemonade` | **0.5 / 1.00** | 0.00 | 4.14 bits/char | 53.75 tok/s |
| **deepseek-r1-0528-8b-FLM** | `lemonade` | **0.51 / 1.00** | 0.00 | 4.53 bits/char | 9.66 tok/s |
| **deepseek-v4-pro:cloud** | `ollama` | **0.65 / 1.00** | 0.00 | 4.84 bits/char | 95.05 tok/s |
| **qwen3.5:397b-cloud** | `ollama` | **0.58 / 1.00** | 0.00 | 4.84 bits/char | 67.37 tok/s |

## Complete Empirical Telemetry
```json
[
  {
    "name": "Qwen3-Coder-30B-A3B",
    "type": "lemonade",
    "tasks": [
      {
        "task": "EXP-001_poincare_lru",
        "formal_score": 0.0,
        "entropy_bits": 4.1361,
        "latency_ms": 14005.22,
        "tps": 24.99,
        "composite_score": 0.28
      },
      {
        "task": "EXP-002_chern_euler_proof",
        "formal_score": 0.6,
        "entropy_bits": 5.0041,
        "latency_ms": 4241.34,
        "tps": 82.52,
        "composite_score": 0.72
      }
    ],
    "final": {
      "frontier_score": 0.5,
      "avg_tps": 53.75,
      "avg_latency_ms": 9123.28
    }
  },
  {
    "name": "deepseek-r1-0528-8b-FLM",
    "type": "lemonade",
    "tasks": [
      {
        "task": "EXP-001_poincare_lru",
        "formal_score": 0.0,
        "entropy_bits": 4.5283,
        "latency_ms": 39234.47,
        "tps": 8.92,
        "composite_score": 0.3
      },
      {
        "task": "EXP-002_chern_euler_proof",
        "formal_score": 0.6,
        "entropy_bits": 4.5171,
        "latency_ms": 33668.97,
        "tps": 10.4,
        "composite_score": 0.72
      }
    ],
    "final": {
      "frontier_score": 0.51,
      "avg_tps": 9.66,
      "avg_latency_ms": 36451.72
    }
  },
  {
    "name": "deepseek-v4-pro:cloud",
    "type": "ollama",
    "tasks": [
      {
        "task": "EXP-001_poincare_lru",
        "formal_score": 0.0,
        "entropy_bits": 4.8384,
        "latency_ms": 4045.67,
        "tps": 86.51,
        "composite_score": 0.3
      },
      {
        "task": "EXP-002_chern_euler_proof",
        "formal_score": 1.0,
        "entropy_bits": 4.8054,
        "latency_ms": 3378.91,
        "tps": 103.58,
        "composite_score": 1.0
      }
    ],
    "final": {
      "frontier_score": 0.65,
      "avg_tps": 95.05,
      "avg_latency_ms": 3712.29
    }
  },
  {
    "name": "qwen3.5:397b-cloud",
    "type": "ollama",
    "tasks": [
      {
        "task": "EXP-001_poincare_lru",
        "formal_score": 0.0,
        "entropy_bits": 4.8354,
        "latency_ms": 5173.6,
        "tps": 68.04,
        "composite_score": 0.3
      },
      {
        "task": "EXP-002_chern_euler_proof",
        "formal_score": 0.8,
        "entropy_bits": 4.8306,
        "latency_ms": 5278.51,
        "tps": 66.69,
        "composite_score": 0.86
      }
    ],
    "final": {
      "frontier_score": 0.58,
      "avg_tps": 67.37,
      "avg_latency_ms": 5226.06
    }
  }
]
```
