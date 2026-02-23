---
title: 3-Tier Hot/Warm/Cold Model Rotation for Local LLM Orchestration
date: 2026-02-23
tags: [pattern, ollama, performance, model-selection]
status: stub
---

# 3-Tier Hot/Warm/Cold Model Rotation for Local LLM Orchestration

Pattern for routing agent tasks to the appropriate local model tier:
- **Hot** (fast, always loaded): small models for classification/routing
- **Warm** (loaded on demand): mid-size models for standard tasks
- **Cold** (slow startup): large models for complex reasoning

## Related
- [[lesson-06-ollama-latency]]
- [[mcp-infrastructure-architecture]]
