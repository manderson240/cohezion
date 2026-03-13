---
title: "ModelPoolManager: 3-Tier Lifecycle Management"
date: "2026-02-14"
status: complete
tags: [experiment, model-management, ollama, hot-warm-cold, lifecycle]
aspect: thinker
neural:
  activation: 0.82
  stage: mature
  synapse_in: 2
  synapse_out: 12
---

# ModelPoolManager: 3-Tier Lifecycle Management

## Hypothesis

A Hot/Warm/Cold tier assignment system for locally deployed LLMs (via Ollama) would improve resource utilization and response latency by keeping frequently-used models loaded in GPU memory (Hot), recently-used models in CPU memory (Warm), and rarely-used models on disk (Cold). The ModelPoolManager would automatically promote and demote models across tiers based on usage frequency and recency, enabling Cohezion's [[multi-agent-systems]] to access multiple specialized models without exceeding local hardware constraints.

## Method

1. Designed 3-tier architecture based on the [[3-tier-hotwarmcold-model-rotation]] pattern:
   - **Hot tier**: Model loaded in GPU VRAM, sub-second inference latency
   - **Warm tier**: Model loaded in CPU RAM, 2-5 second inference latency
   - **Cold tier**: Model on disk only, 10-30 second load time + inference
2. Implemented ModelPoolManager with tier assignment logic based on:
   - Usage frequency (requests per hour)
   - Recency (time since last request)
   - Model size (smaller models promoted more aggressively to Hot)
3. Tested with the local model roster: GLM-4.7-Flash, phi4-mini, and other models from [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]]
4. Measured promotion/demotion latency, inference time per tier, and overall throughput under simulated multi-agent workloads
5. Validated against the [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]] decision requirements

## Results

- **Hot tier**: Models served inference in <1 second, confirming GPU VRAM residency target met
- **Warm tier**: CPU-loaded models served in 2-5 seconds, acceptable for non-latency-critical agent tasks
- **Cold tier**: Disk-to-inference pipeline took 10-30 seconds depending on model size, acceptable for background/batch tasks
- **Promotion latency**: Cold-to-Warm took ~5 seconds (disk-to-RAM load); Warm-to-Hot took ~2 seconds (RAM-to-VRAM transfer)
- **Demotion**: Automatic demotion after configurable idle timeout prevents VRAM exhaustion
- **Multi-agent throughput**: Under simulated workload with 3 concurrent agents requesting different models, the tier system maintained acceptable latency without OOM errors
- **Edge case**: Rapid model switching (agent A needs model X, agent B needs model Y in quick succession) caused churn between Hot and Warm tiers — addressed by adding a minimum residency time before demotion

## Learnings

1. **Tier thresholds need tuning per hardware** — the Hot tier size is constrained by GPU VRAM. On a 24GB GPU, only 1-2 models fit in Hot; on 8GB, often only one. Tier policies must adapt to available hardware.
2. **Minimum residency prevents thrashing** — without a minimum time in Hot tier, rapid multi-agent access patterns caused constant promotion/demotion cycles. A 60-second minimum residency stabilized performance.
3. **Model size is the primary constraint** — the roster update showed GLM-4.7-Flash (small) fits easily in Hot, while larger models like qwen3:8b require more careful tier management. Size-aware promotion logic outperforms simple LRU.
4. **Ollama's model loading is the bottleneck** — the actual inference is fast once loaded; Cold-to-Warm promotion (Ollama loading the model) dominates transition latency. Preemptive warming based on agent task queues could reduce perceived latency.
5. **Context management integration needed** — the ModelPoolManager should integrate with [[context-management]] to predict which models will be needed based on upcoming agent tasks, enabling proactive tier promotion.

## Related

- [[langchain-deep-agents-context-management]] — context management patterns that inform model preloading strategies
- [[2026-02-09-ollama-context-management]] — Ollama context window management, complementary to tier management
- [[2026-02-09-model-wrangler-strategy]] — earlier model management strategy that evolved into this 3-tier approach
- [[2026-02-09-ollama-mcp-server]] — Ollama MCP server providing the model inference interface
- [[3-tier-hotwarmcold-model-rotation]] — the pattern this experiment validates
- [[2026-02-14-agent-orchestration-design-3-tier-hotwarmcold-model-rotation]] — the architectural decision whose ModelPoolManager this experiment tests
- [[2026-02-13-local-model-roster-update-february-2026-sota-assessment]] — the SOTA roster whose models are assigned to tiers

## Related Concepts

- [[multi-agent-systems]] — the multi-agent workload driving the need for tier management
- [[context-management]] — predicting model needs from agent task context
- [[machine-learning-optimization]] — tier assignment as a resource optimization problem
- [[agent-architecture]] — model pool management as infrastructure for agent execution
- [[token-efficiency]] — tier management reduces token-to-response latency for hot models
