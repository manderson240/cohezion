---
name: history-flux-scoring-compatibility
description: |
  Critical constraint: HistoryFlux uses word-overlap scoring (NOT semantic/embedding search).
  Use when: (1) intra-workflow compounding produces zero context (nodes don't see prior results),
  (2) relevance scores are ~0.33 and fail the 0.5 floor, (3) writing WorkflowEngine execution
  summaries, (4) writing tests for FLUX context bus, (5) designing NodeSpec descriptions for
  nodes that should share context. Root cause: structured formats like "[researcher]: keys=[...]"
  score ~0.33 against natural-language queries; natural-language format like "researcher completed
  — Research AI safety — outputs: papers" scores 0.7+ against related queries.
author: Claude Code
version: 1.0.0
---

# HistoryFlux Scoring Compatibility

## Problem

Intra-workflow compounding silently fails: Node B executes but receives no FLUX context from
Node A's prior execution, even though Node A completed successfully and wrote to HistoryFlux.

Relevance scores are ~0.33, below the 0.5 relevance floor, so blocks are dropped.

## Root Cause

`HistoryFlux` uses **word-overlap scoring** — not embeddings or semantic search. The scorer
counts shared words between the stored content and the query string.

```python
# HistoryFlux relevance scoring (simplified):
query_words = set(query.lower().split())
content_words = set(content.lower().split())
score = len(query_words & content_words) / max(len(query_words), 1)
```

If the execution summary uses a structured format with brackets, colons, or JSON-like syntax,
most "words" are punctuation artifacts that don't overlap with the natural-language query.

## The Scoring Compatibility Constraint

**Summaries must share vocabulary with the queries that will retrieve them.**

AgentNode builds its query from node description + input values:
```python
query = "Review AI safety research papers {topic}"
```

If the Node A summary looks like `[researcher]: outputs=['papers', 'findings']`, the overlap
is ~0 (brackets/quotes are noise). The summary fails the 0.5 floor and Node B gets nothing.

If the summary looks like `"researcher completed — Research AI safety papers and findings —
outputs: papers findings"`, the overlap is ~0.7 and the block passes the floor.

## The Fix: Natural-Language Summary Format

```python
# CORRECT — WorkflowEngine._record_to_flux()
parts = [f"{node_name} completed"]
if desc:
    parts.append(desc[:120])        # Use node's own description verbatim
parts.append(f"outputs: {' '.join(output_keys)}")
summary = " — ".join(parts)         # Natural language, space-separated words
```

```python
# WRONG — structured format, fails keyword overlap
summary = f"[{node_name}]: outputs={output_keys}"       # brackets = noise
summary = f"Node({node_id}) status=completed"           # equals/parens = noise
summary = json.dumps({"node": node_name, "keys": keys}) # JSON syntax = noise
```

## Impact on NodeSpec Descriptions

For intra-workflow compounding to work, **connected nodes must share domain vocabulary in
their descriptions**.

```python
# CORRECT — shared vocabulary enables overlap scoring
spec_a = NodeSpec(..., attributes={"description": "Research AI safety papers and findings"})
spec_b = NodeSpec(..., attributes={"description": "Review AI safety research papers"})
# Overlap: "research", "AI", "safety", "papers" — score ~0.75

# WRONG — no shared vocabulary, compounding silently fails
spec_a = NodeSpec(..., attributes={"description": "Gather information on the topic"})
spec_b = NodeSpec(..., attributes={"description": "Analyze the collected data"})
# Overlap: nearly zero
```

**Rule:** In connected workflow nodes (A → B), if B should receive A's context, their
descriptions should include 2-4 shared domain-relevant words.

## Impact on Test Design

Tests that validate intra-workflow compounding MUST use realistic vocabulary sharing:

```python
# CORRECT — tests pass because descriptions share vocabulary with queries
spec_a = _make_spec("a", "researcher", description="Research AI safety papers and findings")
spec_b = _make_spec("b", "reviewer", description="Review AI safety research papers")

# WRONG — tests fail silently (0 FLUX context blocks received, no assertion error)
spec_a = _make_spec("a", "researcher")   # No description → query = "researcher"
spec_b = _make_spec("b", "reviewer")    # No description → query = "reviewer"
# "researcher" has zero overlap with "researcher completed — outputs: papers"
```

The scoring failure is silent: Node B's `_execute_fn` runs with `inputs` that simply don't
contain `_flux_context`. No exception is raised.

## Relevance Score Reference

| Summary Format | Query | Score | Passes 0.5 floor? |
|---|---|---|---|
| `researcher completed — Research AI safety — outputs: papers` | `Review AI safety research papers` | ~0.7 | Yes |
| `researcher completed` (no desc, no outputs) | `Review AI safety research papers` | ~0.1 | No |
| `[researcher]: keys=['papers']` | `Review AI safety research papers` | ~0.2 | No |
| `node-42 completed — analyst — outputs: analysis trend` | `Analyze growth trends` | ~0.5 | Borderline |

## Verification

After recording summaries to HistoryFlux, query it directly to check scores:

```python
history = HistoryFlux()
history.record("researcher completed — Research AI safety papers — outputs: papers", {})
blocks = await history.get_context("Review AI safety research papers", top_k=5)
assert blocks[0].relevance_score >= 0.5, f"Score too low: {blocks[0].relevance_score}"
```

## Summary

The 0.5 relevance floor is correct — it filters noise. The scoring mechanism (word overlap)
is by design — lightweight, zero dependencies, predictable. The constraint is: **format
summaries as natural language that shares vocabulary with the role descriptions of nodes
that will consume the context**.

See `src/cohezion/graph/engine.py` (`_record_to_flux`) and
`tests/graph/test_context_bus.py` (`TestIntraWorkflowCompounding`).
