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
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation|Decision: Agent Orchestration Design — 3-Tier Hot/Warm/Cold Model Rotation]]
- [[2026-02-09-ai-model-strategy|Decision: AI Model Strategy]]
- [[2026-02-09-ollama-mcp-server|Decision: Ollama MCP Server]]
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]] — SOTA model selection that determined which models fill each tier (GLM-4.7-Flash as hot/warm, phi4-mini-reasoning as routing tier)
- [[2026-02-14-modelpoolmanager-3-tier-lifecycle-management|Experiment: ModelPoolManager 3-Tier Lifecycle Management]] — experimental validation of the implementation

## Scientific Foundation

- [[agentic-ai-memory-hierarchies]] — the hardware KV-cache hierarchy problem described there (HBM → DRAM → PCIe bottleneck) is exactly what this Hot/Warm/Cold pattern solves at the software layer: hot models stay in GPU VRAM (fast tier), warm models in system RAM (medium tier), cold models on NVMe (slow tier). This pattern is a direct software implementation of the memory hierarchy principles the paper identifies as the critical constraint for agentic AI. The "intelligent memory management software" the paper calls for IS this pattern.
- [[lesson-29-batch-cache-two-phase]] — the two-phase cache lookup (check before compute) is the micro-level equivalent of the tier-selection logic: always query the hottest available tier before descending to a slower one. Both prevent unnecessary cold-start latency.
