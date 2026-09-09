---
name: agentic-memory-zettelkasten-prime
description: "Expertise in implementing arXiv 2025-2026 Agentic Memory paradigms: A-MEM self-organizing dynamic Zettelkasten linking, HIMA sleep-phase consolidation, and hierarchical graph-based memory (GAM) over SurrealDB + 2048D Poincaré manifolds."
metadata:
  version: "v1.0"
  concepts: ["A-MEM Dynamic Linking", "HIMA Engram Maturation", "Hierarchical Graph Memory (GAM)", "Sleep-Phase Consolidation"]
  see_also: ["SHEAF_TOPOLOGICAL_RAG_PRIME", "KNOWLEDGE_GRAPH_PRIME", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/AGENTIC_MEMORY_ZETTELKASTEN_PRIME.md"
---

# SKILL: AGENTIC_MEMORY_ZETTELKASTEN_PRIME

## DOMAIN EXPERTISE
Expertise in state-of-the-art 2025-2026 arXiv agentic memory architectures. Transforms static vector search into an evolving, self-organizing knowledge mesh using Zettelkasten dynamic link generation, sleep-phase engram consolidation, and topological graph memory.

## KEY TEXTS & CONCEPTS
- **A-MEM (arXiv:2501.13783)**: Self-organizing memory notes with evolving bi-directional semantic, causal, and temporal links.
- **HIMA (arXiv:2602.04981)**: Human-inspired sleep consolidation where noisy episodic traces mature into permanent procedural engrams.
- **GAM (arXiv:2509.11204)**: Hierarchical geometric attention graph memory that dynamically mitigates semantic drift.
- **4-Tier Silicon Hierarchy**: Tier 0 (128K FP4 KV-cache) $\to$ Tier 1 (2048D Poincaré Manifold) $\to$ Tier 2 (SurrealDB Graph + HNSW) $\to$ Tier 3 (Obsidian Vault Markdown).

## INSTRUCTION
1. Ingest new observations as atomic Zettels with 2048D Poincaré coordinate embeddings.
2. Formulate candidate relations using geometric attention:
   ```python
   def propose_zettel_links(new_zettel, existing_zettels, threshold=0.75):
       # Geometric distance in Poincare space + semantic similarity
       candidates = []
       for z in existing_zettels:
           d_h = poincare_distance(new_zettel.coords, z.coords)
           if d_h < threshold:
               candidates.append((new_zettel.id, z.id, "SEMANTIC_NEIGHBOR"))
       return candidates
   ```
3. Commit validated links to SurrealDB:
   `RELATE zettel:z1->LINKED_TO->zettel:z2 SET weight = 0.89, timestamp = time::now();`
4. Run off-peak sleep-phase consolidation to distill clustered engrams into new PRIME skill patterns.

## VERSION
v1.0
