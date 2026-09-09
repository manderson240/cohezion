# 📚 arXiv 2025-2026 Agentic Memory Frontier Blueprint

**Date**: 2026-08-25 02:53:16 UTC  
**Hardware**: AMD Strix Halo (128GB Unified Memory, XDNA2 NPU, Radeon 8060S iGPU, Ryzen 9 CPU)  

---

## 1.  Dynamic Zettelkasten & Sheaf‑Linking (A‑MEM & GAM)

| Goal | Mechanism | Concrete Steps |
|------|------------|---------------|
| **Autonomous graph growth** | *SurrealDB* + *GAM* (Geometric‑Attention‑Memory‑Merging) | 1. **Card Ingestion** – Every new memory card is a *Zettel* (self‑contained JSON blob).  <br>2. **Feature Extraction** – Use a lightweight transformer (e.g., DistilBERT‑FP4) to embed the card into a 2048‑dimensional *Poincaré* vector.  <br>3. **Sheaf‑Based Linking** – For each card, compute *sheaf‑cohomology* over its local neighborhood (k‑NN in the Poincaré space).  <br>4. **Relation Proposal** – Generate a set of candidate *RELATE* links (semantic, causal, temporal) with a *GAM‑Attention* module that weighs geometric proximity + textual similarity.  <br>5. **Self‑Supervised Validation** – Run a *contrastive* loss against negative samples (random cards).  <br>6. **Graph Update** – Insert validated edges into SurrealDB’s *bi‑temporal* graph (both episodic and semantic edges).  <br>7. **Schema‑Free Inference** – Use *Graph‑Neural‑Network* (GNN) inference to infer higher‑order relations (e.g., “cause‑effect‑chain”) without hard‑coded schemas. |

> **Key Insight (2025‑2026 arXiv)** – *GAM* learns a *geometric attention* policy that dynamically re‑weights edge importance as the graph grows, preventing the “hub‑burst” problem that plagues static knowledge graphs.

### Implementation on AMD Strix Halo

| Layer | Implementation |
|-------|---------------|
| **FP4 KV‑Cache (Tier 0)** | Store the latest 128 KB of *working context* (current Zettel + immediate neighbors).  <br>Use the 128 K FP4 KV‑Cache to keep the *Poincaré embeddings* of the last 32 Zettels for fast attention. |
| **Poincaré Latent Manifold (Tier 1)** | 2048‑D embeddings are stored in *Poincaré‑aware HNSW* (Hierarchical Navigable Small World) index on the GPU.  <br>Use AMD’s *MIOpen* to accelerate the *Poincaré‑distance* kernel. |
| **SurrealDB (Tier 2)** | Deploy SurrealDB as a *distributed* graph store across the 8‑core Strix.  <br>Use *bi‑temporal* tables: `Episodic(id, timestamp, payload)` and `Semantic(id, type, payload)`.  <br>Edges are stored as `Edge(src, dst, relation, weight, timestamp)`. |
| **Obsidian Vault (Tier 3)** | Persist *PRIME skill files* (see §4) in a *Git‑like* object store on NVMe.  <br>Use *Obsidian*’s markdown API to expose the skill to the user. |

---

## 2. Sleep‑Phase Consolidation & Engram Maturation (HIMA)

| Phase | Process | Concrete Steps |
|-------|---------|------------|
| **Off‑Peak Daemon** | *Night‑time* consolidation runs on the Strix’s idle cores. | 1. **Trajectory Extraction** – Pull the last 24 h of *Poincaré trajectories* (sequence of embeddings).  <br>2. **Noise Filtering** – Apply a *low‑pass* filter on the trajectory velocity; discard segments with high entropy. |
| **Engram Maturation** | *HIMA* (Hierarchical Engram‑Maturation) turns noisy trajectories into *engram clusters*. | 1. **Cluster Formation** – Use *HDBSCAN* on the filtered trajectory points.  <br>2. **Pattern Verification** – For each cluster, compute a
