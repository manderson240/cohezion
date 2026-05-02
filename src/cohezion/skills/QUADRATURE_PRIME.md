---
name: quadrature-prime
description: "Autonomous Governance & Strategic Alignment. The \"Quadrature\" is the consensus mechanism of the Swarm. It prevents hallucinated, dangerous, or inefficient actions by forcing every major decision through 4 opposing perspectives."
metadata:
  version: "v1.0 (Integration of The Will)"
  concepts: ["The Nexus", "The 4 Voices", "Architect", "Engineer", "Ethicist", "Resource", "Consensus"]
  source: "src/cohezion/skills/QUADRATURE_PRIME.md"
---

# SKILL: QUADRATURE_PRIME

## DOMAIN EXPERTISE
**Autonomous Governance & Strategic Alignment.**
The "Quadrature" is the consensus mechanism of the Swarm. It prevents hallucinated, dangerous, or inefficient actions by forcing every major decision through 4 opposing perspectives.

## KEY CONCEPTS
- **The Nexus**: The meeting place of the 4 Voices.
- **The 4 Voices**:
    1.  **Architect**: "What is beautiful and structurally sound?" (Gemini).
    2.  **Engineer**: "What is efficient and possible?" (DeepSeek/Qwen).
    3.  **Ethicist**: "What is safe and aligned?" (Claude/Llama).
    4.  **Resource**: "What can we afford?" (ResourceMonitor).
- **Consensus**: Action is only taken when Alignment > 0.85.

## INSTRUCTION
### The Nexus Loop
1.  **Propose**: An agent proposes an action (e.g., "Rewrite the Database Layer").
2.  **Debate**: The 4 Voices critique the proposal.
3.  **Vote**: Weighted voting based on recent success.
4.  **Ratify**: If passed, it becomes a `STRATEGIC_DIRECTIVE`.

## IMPLEMENTATION
```python
consensus = await nexus.debate(proposal)
if consensus.score > 0.85:
    return consensus.directive
else:
    return consensus.rejection_reason
```

## VERSION
v1.0 (Integration of The Will)
