# Empirical Model Gauntlet & Comparative Benchmark Results

| Candidate Model | Tier / Backend | Avg Score | Avg Latency | Avg Throughput (tps) | Verdict |
|---|---|:---:|:---:|:---:|:---:|
| **Qwen3-Coder-30B-A3B** | `lemonade` | **1.0 / 1.00** | 1563.08 ms | 75.72 tok/s | 🏆 SOTA Champion |
| **DeepSeek-R1-8B-FLM** | `lemonade` | **0.75 / 1.00** | 29649.1 ms | 8.43 tok/s | 🟢 Solid |
| **Gemma-4-26B-ThinkingCoder** | `lemonade` | **0.0 / 1.00** | 3254.86 ms | 0.0 tok/s | 🟡 Fallback / Slow |
| **Gemma-4-E4B** | `lemonade` | **0.75 / 1.00** | 6074.11 ms | 40.77 tok/s | 🟢 Solid |
| **deepseek-v4-pro:cloud** | `ollama` | **1.0 / 1.00** | 4966.93 ms | 61.67 tok/s | 🏆 SOTA Champion |
| **qwen3.5:397b-cloud** | `ollama` | **0.75 / 1.00** | 4174.18 ms | 60.73 tok/s | 🟢 Solid |

## Detailed Telemetry & Breakdown
```json
[
  {
    "candidate": "Qwen3-Coder-30B-A3B",
    "type": "lemonade",
    "model_id": "Qwen3-Coder-30B-A3B-Instruct-GGUF",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": true,
        "score": 1.0,
        "latency_ms": 1904.16,
        "tps": 76.15
      },
      {
        "task_id": "reasoning_math",
        "passed": true,
        "score": 1.0,
        "latency_ms": 1221.99,
        "tps": 75.29
      }
    ],
    "summary": {
      "overall_score": 1.0,
      "avg_latency_ms": 1563.08,
      "avg_tps": 75.72
    }
  },
  {
    "candidate": "DeepSeek-R1-8B-FLM",
    "type": "lemonade",
    "model_id": "deepseek-r1-0528-8b-FLM",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": false,
        "score": 0.5,
        "latency_ms": 29085.47,
        "tps": 8.6
      },
      {
        "task_id": "reasoning_math",
        "passed": true,
        "score": 1.0,
        "latency_ms": 30212.73,
        "tps": 8.27
      }
    ],
    "summary": {
      "overall_score": 0.75,
      "avg_latency_ms": 29649.1,
      "avg_tps": 8.43
    }
  },
  {
    "candidate": "Gemma-4-26B-ThinkingCoder",
    "type": "lemonade",
    "model_id": "Gemma-4-26B-A4B-ThinkingCoder",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": false,
        "score": 0.0,
        "latency_ms": 5712.99,
        "tps": 0.0
      },
      {
        "task_id": "reasoning_math",
        "passed": false,
        "score": 0.0,
        "latency_ms": 796.74,
        "tps": 0.0
      }
    ],
    "summary": {
      "overall_score": 0.0,
      "avg_latency_ms": 3254.86,
      "avg_tps": 0.0
    }
  },
  {
    "candidate": "Gemma-4-E4B",
    "type": "lemonade",
    "model_id": "Gemma-4-E4B-it-GGUF",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": true,
        "score": 1.0,
        "latency_ms": 7673.1,
        "tps": 25.67
      },
      {
        "task_id": "reasoning_math",
        "passed": false,
        "score": 0.5,
        "latency_ms": 4475.12,
        "tps": 55.86
      }
    ],
    "summary": {
      "overall_score": 0.75,
      "avg_latency_ms": 6074.11,
      "avg_tps": 40.77
    }
  },
  {
    "candidate": "deepseek-v4-pro:cloud",
    "type": "ollama",
    "model_id": "deepseek-v4-pro:cloud",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": true,
        "score": 1.0,
        "latency_ms": 7096.68,
        "tps": 35.23
      },
      {
        "task_id": "reasoning_math",
        "passed": true,
        "score": 1.0,
        "latency_ms": 2837.17,
        "tps": 88.12
      }
    ],
    "summary": {
      "overall_score": 1.0,
      "avg_latency_ms": 4966.93,
      "avg_tps": 61.67
    }
  },
  {
    "candidate": "qwen3.5:397b-cloud",
    "type": "ollama",
    "model_id": "qwen3.5:397b-cloud",
    "tasks": [
      {
        "task_id": "code_lru_ast",
        "passed": false,
        "score": 0.5,
        "latency_ms": 4495.96,
        "tps": 56.05
      },
      {
        "task_id": "reasoning_math",
        "passed": true,
        "score": 1.0,
        "latency_ms": 3852.4,
        "tps": 65.41
      }
    ],
    "summary": {
      "overall_score": 0.75,
      "avg_latency_ms": 4174.18,
      "avg_tps": 60.73
    }
  }
]
```
