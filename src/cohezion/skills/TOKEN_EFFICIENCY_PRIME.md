---
name: token-efficiency
description: Token consumption tracking, analysis, and optimization across the
  agent swarm. Reduces waste through batching, caching, context pruning, and
  adaptive model selection. Use when optimizing token costs, analyzing waste
  patterns, setting token budgets, or when user mentions "token efficiency",
  "token budget", "cache hit rate", "model downgrade", or "cost optimization".
metadata:
  version: "1.0"
  legacy-name: TOKEN_EFFICIENCY_PRIME
---

# SKILL: TOKEN_EFFICIENCY_PRIME

## DOMAIN EXPERTISE
Expert methodology for tracking, analyzing, and optimizing token consumption across the Cohezion agent swarm. Reduces waste through batching, caching, context pruning, and adaptive model selection.

## KEY TEXTS & CONCEPTS
- **Token Budget**: Per-agent and per-session limits that prevent runaway consumption.
- **Cache Hit Rate**: Ratio of semantic cache hits to total LLM calls - target >30%.
- **Context Pruning**: Reducing prompt size via summarization or truncation to fit smaller models.
- **Model Downgrade Policy**: Automatic fallback to cheaper models when quality threshold is still met.
- **Batch Consolidation**: Grouping independent tasks into single prompts per BATCHING_PROTOCOL_PRIME.

## FUTURE HOOKS
- **Real-time Dashboard**: Token usage visualization via MCP portal WebSocket feed.
- **Adaptive Budget**: Dynamic per-agent token budgets based on historical efficiency.
- **Cost Projection**: Predict session cost based on task queue depth and model assignments.
- **Waste Alert System**: Proactive notifications when patterns exceed waste thresholds.

## INSTRUCTION
1. **Instrument All Calls**: Every `_call_ollama` invocation records tokens, model, agent, task_type via `TokenEfficiencyTracker.record()`.
2. **Periodic Analysis**: Run `detect_waste()` every 50 tasks or on-demand via retrospection.
3. **Act on Recommendations**:
   - Low cache hit rate → enable SemanticCache with lower threshold.
   - High latency → apply ContextHarness to reduce prompt size.
   - Token concentration → batch similar tasks via BatchManager.
4. **Persist & Review**: Save metrics to `knowledge_graph/token_efficiency.json` for cross-session learning.

## VERSION
v1.0

## SEE ALSO
- BATCHING_PROTOCOL_PRIME
- COMPOUND_ENGINEERING_PRIME
- LOCAL_OFFLOAD_PRIME
- RETROSPECTIVE_SKILL
