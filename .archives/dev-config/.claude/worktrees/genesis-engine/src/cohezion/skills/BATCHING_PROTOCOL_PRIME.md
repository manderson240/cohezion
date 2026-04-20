# SKILL: BATCHING_PROTOCOL_PRIME

## DOMAIN EXPERTISE
Expert methodology for consolidating multiple independent, menial tasks into high-density prompts for local SLM execution, significantly reducing context load and token waste.

## KEY TEXTS & CONCEPTS
- **Task Consolidation**: The process of gathering multiple queries (e.g., "document A", "rephrase B") into a single prompt session.
- **Density-Optimized Prompt**: A prompt structure that uses clear delimiters (`[TASK_ID: <id>]`) to help SLMs separate and process multiple instructions.
- **Context Overhead**: The additional tokens consumed by repeating system prompts and truth anchors for multiple independent requests.
- **Throughput vs. Latency**: Batching increases throughput (tasks per second) while slightly increasing latency per batch, but drastically reduces overall resource consumption.

## INSTRUCTION
1. **Identify Batch Candidates**: Target tasks with low complexity (menial) that don't require immediate real-time response.
2. **Consolidate with Delimiters**:
    - Use clear Task IDs.
    - Provide a batch instructions header: "Respond to EACH task below in sequence."
    - Use the format: `[TASK_ID: <id>] RESPONSE: <text>`.
3. **Apply Context Harness**: One harness (system prompt + truth anchors) for the entire batch.
4. **Parse the Stream**: Use a regex or marker-based parser to distribute individual responses back to their respective task owners.

### Example Batch
```python
# Consolidation format
[TASK_ID: T1] QUERY: Add docstring to function X
[TASK_ID: T2] QUERY: Summarize error log Y
```

## VERSION
v1.0

## SEE ALSO
- LOCAL_OFFLOAD_PRIME
- COMPOUND_ENGINEERING_PRIME
- SEMANTIC_CACHING_PRIME
