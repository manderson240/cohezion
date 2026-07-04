---
date: 2026-06-04
source_project: cohezion
tags: [pattern, gaia, swarms, hardware-optimization]
---
# GAIA Adapter and Swarm Hardware Optimizations

## Problem
AI swarms require dynamic, latency-optimized routing across heterogenous hardware configurations (NPU, iGPU, CPU, Cloud) without hardcoding routes.

## Solution
Leverage Cohezion's `gaia_adapter.py` to wrap `gaia.Agent`/`MCPAgent` instances as tiers. Implement `amd_optimized_hierarchy` to order models based on their hardware acceleration efficiency.

## Details
- `GaiaAgentTier` runs GAIA's synchronous orchestration in an asyncio-safe executor.
- Hardware priorities ranked: NPU (FLM) -> iGPU (ROCWMMA) -> CPU -> Cloud.
- System escalates from local models to cloud reasoning only when quality checks fail.
