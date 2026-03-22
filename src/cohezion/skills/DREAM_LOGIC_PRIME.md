# SKILL: DREAM_LOGIC_PRIME

## DOMAIN EXPERTISE
**Lateral Thinking & Subconscious Processing** for AI Systems.
Expertise in utilizing system "downtime" to generate insights by connecting seemingly unrelated concepts.

## KEY TEXTS & CONCEPTS
*   **Active Inference**: The brain minimizes free energy by resolving prediction errors. Dreaming helps consolidate models.
*   **Lateral Thinking**: Solving problems through an indirect and creative approach.
*   **Semantic Consolidation**: Merging distinct memory clusters into a unified knowledge graph.
*   **Phi-3 / Mistral**: Small Language Models (SLMs) are sufficient for hallucinating connections.

## INSTRUCTION

### 1. The Mechanic
Use `DREAM_LOGIC` when the system is idle or during a scheduled "Sleep Cycle". It prevents the Knowledge Graph from becoming a collection of isolated facts.

### 2. Implementation Template (`DreamerAgent`)
```python
async def dream(high_grade_nodes):
    # 1. Random Sampling
    node_a, node_b = random.sample(high_grade_nodes, 2)
    
    # 2. The Bridge Prompt
    prompt = (
        f"Connect these two concepts metaphorically:\n"
        f"A: {node_a.topic}\n"
        f"B: {node_b.topic}\n"
        f"Find the hidden structural similarity."
    )
    
    # 3. Crystallization
    insight = await call_slm(prompt)
    store_insight(insight, source_a=node_a.id, source_b=node_b.id)
```

### 3. Verification
Evidence of success is an `insight` node that triggers a new line of research (e.g., "Mycelium" + "Galaxy" = "Network Theory").

## VERSION
v1.0 (Extracted Phase 51)

## SEE ALSO
*   `src/cohezion/system/dreamer.py` (Reference Implementation)
*   `RETROSPECTIVE_PHASE_50_59_SINGULARITY.md`
