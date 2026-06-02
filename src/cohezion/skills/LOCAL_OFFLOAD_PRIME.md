---
name: local-offload-prime
description: "Expert methodology for offloading menial, low-complexity, or supportive tasks to local Small Language Models (SLMs) using a Context Harness to maximize token efficiency. Use when: delegating classification, summarization, or formatting tasks to local SLMs to reduce cloud cost. Skip: for Ollama model catalog configuration use MODEL_ROUTING_PRIME; for Lemonade/triune tiered routing use LOCAL_INFERENCE_ROUTING; for token budget tracking use TOKEN_EFFICIENCY_PRIME."
metadata:
  version: "v1.0"
  concepts: ["Menial Task", "Context Harness", "Sovereign Execution", "Token Efficiency"]
  see_also: ["HALLUCINATION_RESOLVER_PRIME", "PERSISTENT_QUALITY_PRIME", "COHEZION_BRIDGE_PRIME"]
  source: "src/cohezion/skills/LOCAL_OFFLOAD_PRIME.md"
---

# SKILL: LOCAL_OFFLOAD_PRIME

## DOMAIN EXPERTISE
Expert methodology for offloading menial, supportive, or low-complexity tasks to local Small Language Models (SLMs) using a "Context Harness" to maximize token efficiency and maintain sovereign execution.

## KEY TEXTS & CONCEPTS
- **Menial Task**: A task characterized by high redundancy, low logical complexity, or purely supportive nature (e.g., documentation, formatting, summarization).
- **Context Harness**: A pre-processing layer that prunes non-essential context, injects "Truth Anchors," and applies instruction-specialization templates for local SLMs.
- **Sovereign Execution**: The ability to complete a task locally without relying on external APIs, reducing latency, cost, and data leakage.
- **Token Efficiency**: Minimizing the use of "Cortex-Tier" (premium) tokens by appropriately routing tasks based on required reasoning depth.

## INSTRUCTION
1. **Classify the Task**: Use the `OffloadManager` or analyze for menial keywords (docstrings, formatting, summaries).
2. **Apply the Harness**:
    - Prune context to the SLM's sweet spot (e.g., 12k for Phi-4-mini).
    - Inject [TRUTH ANCHORS] from the `HallucinationResolver`.
    - Apply model-specific instructions (e.g., "be extremely concise").
3. **Execute Locally**: Invoke the task via `offload_to_local` or the `offload_task` MCP tool.
4. **Verify Quality**: Ensure the local output meets the required standard; fallback to premium models only if high-fidelity logic is required.

### Example Offload
```python
# In an Agent's process method
if self._offload_mgr.is_offloadable(query):
    result = await self.offload_to_local(query)
    return result
```

## VERSION
v1.0

## SEE ALSO
- HALLUCINATION_RESOLVER_PRIME
- PERSISTENT_QUALITY_PRIME
- COHEZION_BRIDGE_PRIME
