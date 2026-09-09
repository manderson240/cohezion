---
name: sheaf-topological-rag-prime
description: "Expertise in applying Sheaf Theory and Čech Cohomology to Retrieval-Augmented Generation (RAG). Detects epistemic contradictions, resolves obstruction 1-cocycles, and glues local document sections into globally consistent knowledge manifolds."
metadata:
  version: "v1.0"
  concepts: ["Sheaf Cohomology", "Čech 1-Cocycles", "Local-to-Global Gluing", "Obstruction Resolution"]
  see_also: ["SHEAF_COHOMOLOGY_ARC_PRIME", "KNOWLEDGE_GRAPH_PRIME"]
  source: "src/cohezion/skills/SHEAF_TOPOLOGICAL_RAG_PRIME.md"
---

# SKILL: SHEAF_TOPOLOGICAL_RAG_PRIME

## DOMAIN EXPERTISE
Expertise in sheaf-theoretic data structures for multi-document RAG, eliminating hallucinations and semantic contradictions by verifying local section compatibility across open cover overlaps.

## KEY TEXTS & CONCEPTS
- **Sheaf Condition (Gluing Axiom)**: If local sections $s_i \in \mathcal{F}(U_i)$ agree on all pairwise intersections $U_i \cap U_j$, there exists a unique global section $s \in \mathcal{F}(U)$ restricting to each $s_i$.
- **Čech Cohomology Obstruction ($H^1(\mathcal{U}, \mathcal{F})$)**: Non-zero 1-cocycles $\delta s_{ij} = s_i|_{U_{ij}} - s_j|_{U_{ij}} \neq 0$ quantify unresolvable factual contradictions across retrieved chunks.
- **Topological Invariant Filters**: Chunks with persistent homology drift are quarantined before LLM context injection.

## INSTRUCTION
1. Compute pairwise semantic overlap matrices $S_{ij} = \text{sim}(c_i, c_j)$ for retrieved document chunks.
2. Formulate the Čech boundary operator $\delta$:
   ```python
   def detect_cohomological_obstructions(chunks, threshold=0.35):
       obstructions = []
       for i in range(len(chunks)):
           for j in range(i+1, len(chunks)):
               # Check if documents contradict on shared entities
               if chunks[i].has_overlap(chunks[j]) and chunks[i].assertion != chunks[j].assertion:
                   obstructions.append((i, j))
       return obstructions
   ```
3. Resolve obstruction cocycles before prompt assembly to guarantee zero-hallucination RAG.

## VERSION
v1.0
