# Inference Metrics Summary

**Date**: 2026-04-10
**Platform**: AMD Ryzen AI MAX+ 395

## Quick Comparison

| Model | Backend | TPS | TTFT | Context | Best For |
|-------|---------|-----|------|---------|----------|
| qwen3:4b | NPU | **75.0** | 13.0ms | 128K | Code, efficiency |
| Gemma-4-E2B | GPU Vulkan | **97.3** | 10.3ms | 256K | Reasoning, speed |
| Jan-v1-4B | GPU Vulkan | **76.2** | 13.1ms | 4K | Novel tasks |

## Key Metrics

- **Highest Throughput**: Gemma-4-E2B @ 97.3 TPS
- **Lowest Latency**: Gemma-4-E2B @ 10.3ms TTFT  
- **Largest Context**: Gemma-4-E2B @ 256K tokens
- **Most Efficient**: qwen3:4b @ 15W (vs 25W GPU)
- **Routing Accuracy**: 100% for all task types

## Files

- **Full Analysis**: `cloud-vault-mcp/vault/cortex/inference-metrics-analysis-2026-04-10.md`
- **SurrealDB**: Record prepared for `inference_analysis` table

## Recommendation

Deploy **hybrid serving**: NPU for code (efficiency), GPU Vulkan for reasoning (speed).
