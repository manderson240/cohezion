---
name: agent-context-injection
description: |
  Design pattern for injecting role-scoped context into LLM agent nodes in multi-agent workflows.
  Use when: (1) adding context retrieval (RAG, memory, FLUX) to agent execution, (2) evaluating
  whether context injection improves token efficiency, (3) the naive signal/token ratio looks
  marginal (~1.05x) but you suspect the design is flawed. Key insight: "zero useful tokens >
  many noise tokens" — a relevance floor filter transforms marginal gains into structural guarantees.
author: Claude Code
version: 1.0.0
---

# Agent Context Injection Pattern

## Problem

When injecting retrieved context into LLM agent nodes, the naive approach (inject top-K results)
often has poor useful-token efficiency. Raw signal/token ratios look marginal (1.05-1.2x) because
many injected blocks are generic noise rather than role-specific signal.

## Core Insight

**Not all tokens are created equal.** A single high-relevance, role-specific block is worth more
than 10 generic blocks. The metric to optimize is "useful token percentage" (blocks above relevance
threshold / total blocks), not raw signal/token ratio.

**Zero tokens > noise tokens.** Injecting nothing is better than injecting irrelevant context that
the LLM must filter. Add a relevance floor — blocks below threshold are dropped entirely.

## Design Pattern

### Three Components

**1. Role-Scoped Query (not generic query)**
```python
def _build_context_query(self, inputs: dict[str, Any]) -> str:
    parts: list[str] = []
    # Primary: structural scope (what this node IS)
    desc = self.spec.attributes.get("description", "")
    parts.append(desc if desc else self.spec.name)
    # Secondary: dynamic scope (what this node is doing RIGHT NOW)
    for value in inputs.values():
        if isinstance(value, str) and len(value) > 3:
            parts.append(value)
            if len(parts) >= 3:
                break
    return " ".join(parts)
```

**2. Relevance Floor Filter**
```python
_FLUX_MIN_RELEVANCE = 0.5  # Drop noise, inject only signal

context_strings = [
    block.content
    for block in ctx.blocks
    if block.relevance_score >= self._FLUX_MIN_RELEVANCE
]
# If no blocks pass the floor, inject nothing (don't inject empty list)
if context_strings:
    enriched["_flux_context"] = context_strings
```

**3. Non-Blocking Failure**
```python
async def _get_flux_context(self, inputs) -> list[str]:
    try:
        query = self._build_context_query(inputs)
        ctx = await self._flux.get_context(query, top_k=self._FLUX_TOP_K)
        return [b.content for b in ctx.blocks if b.relevance_score >= self._FLUX_MIN_RELEVANCE]
    except Exception:
        logger.debug("Context injection failed for node '%s' (non-blocking)", self.spec.id)
        return []  # Degrade gracefully — never crash the workflow
```

## Evaluating Effectiveness

The right metrics (NOT raw signal/token ratio):

| Metric | Formula | Target |
|--------|---------|--------|
| Overhead % | (context tokens / execution budget) × 100 | <5% |
| Useful token % | blocks_above_threshold / total_blocks | ~100% |
| Waste rate | blocks_below_threshold / total_blocks | ~0% |
| Cross-contamination | context from wrong role | 0% |
| Avg relevance | mean(block.relevance_score) | >0.7 |

**Execution budget baseline**: ~3000 tokens per agent execution.
**Rule of thumb**: 3 blocks × ~13 tokens = ~39 tokens = 1.3% overhead at 100% useful.

## The Compound Flywheel

Context injection becomes more valuable over time because:
1. Execution → vault logs → FLUX history provider
2. Next execution of same role → history provider returns better blocks
3. Role-specific context improves → better completions → better vault entries

The pattern pays compound interest: early executions have lower relevance, later executions
converge to high relevance as the vault accumulates role-specific knowledge.

## Implementation Checklist

- [ ] Query scoped to node's role (description or name), not generic
- [ ] Relevance floor (0.5 default) — never inject below threshold
- [ ] Non-blocking failure (try/except, return empty list)
- [ ] Backward compatible (`flux_aggregator: X | None = None`)
- [ ] `_flux_context` key removed from result before propagating downstream
- [ ] Inject only when non-empty (`if context_strings:`)

## Gotcha: Context Leak

`_flux_context` injected into inputs must NOT propagate through edge outputs.
Strip it from results before returning:

```python
result = await self._execute_fn(enriched)
result_dict = result if isinstance(result, dict) else {"output": result}
result_dict.pop("_flux_context", None)  # Don't propagate internal context
return result_dict
```

## Example: AgentNode with FLUX

See `src/cohezion/graph/nodes.py` — `AgentNode` class.
Tests in `tests/graph/test_flux_injection.py`.
