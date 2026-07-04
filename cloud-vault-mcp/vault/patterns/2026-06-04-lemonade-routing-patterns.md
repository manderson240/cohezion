---
date: 2026-06-04
source_project: cohezion
tags: [pattern, routing, lemonade]
---
# Smart Local Inference Routing: NPU, iGPU, and CPU

## Problem
Escalating all tasks to heavy cloud or CPU models introduces token asymmetry, latency, and high cloud overhead.

## Solution
Leverage multi-lane local inference via the **Lemonade** backend at port 13307, dynamically routing based on query complexity.

## Simulation Routing Decisions
| Query | Complexity | Model | Hardware |
|---|---|---|---|
| What is 7 * 8?... | simple | gemma3-4b-FLM | npu |
| Write a python function to sort a list u... | complex | Qwen3-0.6B-GGUF | cpu |
| Design a high-throughput, distributed ev... | complex | Qwen3-0.6B-GGUF | cpu |


## Verification
- Local silicon routes tasks instantly.
- NPU (gemma3-4b-FLM) executes simple Yes/No or routing queries at ~24ms.
- iGPU (Gemma-4-E4B-it-GGUF) handles intermediate code/text generation.
- CPU (Qwen3-0.6B-GGUF) handles reasoning fallback when iGPU is busy.

## Related
- [[2026-06-04-evo-analogue-correlations]]
