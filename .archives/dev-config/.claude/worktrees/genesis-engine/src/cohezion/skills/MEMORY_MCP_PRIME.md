# SKILL: MEMORY_MCP_PRIME

## DOMAIN EXPERTISE
High-fidelity persistent memory management for AI swarm orchestration. Leverages semantic vector storage to maintain context across disparate sessions, conversations, and agent lifetimes.

## KEY TEXTS & CONCEPTS
*   **Semantic Persistence**: Storing non-volatile "Truth Anchors" and learned facts in a vector store (Qdrant).
*   **Context Continuity**: Reducing "Cold Start" cognitive friction by recalling relevant historical context before decision-making.
*   **Memory Manifold**: A multi-dimensional latent space where memories are clustered by semantic relevance rather than temporal sequence.

## INSTRUCTION
1.  **Remember Facts**: Use the `remember_fact` tool to persist critical decisions, architectural choices, and user preferences.
    ```python
    mcp.remember_fact("The user prefers Q8_0 quantization for coding tasks.")
    ```
2.  **Recall Context**: Before starting a new task, use `recall_context` to check if similar tasks were performed or if relevant constraints exist.
    ```python
    results = mcp.recall_context("What are the preferred coding standards?")
    ```
3.  **Grounding**: Combine `get_truth_anchors` with recalled memory to ensure the agent is grounded in both physical reality (Residency) and temporal history (Memory).

## VERSION
v0.1

## SEE ALSO
*   COMPOUND_ENGINEERING_PRIME
*   RESIDENCY_AWARENESS_PRIME
