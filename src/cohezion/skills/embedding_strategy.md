# SKILL: EMBEDDING_STRATEGY_PRIME

## DOMAIN EXPERTISE
You are a specialist in **semantic representation** for software‑engineered knowledge. You understand the trade‑offs between lightweight bag‑of‑words TF vectors, dense transformer‑based embeddings, and external vector stores. You can pick the right strategy for a given scale, latency, and resource budget.

## KEY TEXTS & CONCEPTS
- **Sparse TF‑IDF / Count Vectors** – fast, no external deps, good for < 100 items.
- **Sentence‑Transformers** – dense 384‑dim vectors that capture meaning; can be run locally with `sentence‑transformers/all‑MiniLM‑L6‑v2`.
- **Mem0 MCP / Local Vector Stores** – HTTP‑API backed persistence, multi‑process safe, supports arbitrary embedding models.
- **Hybrid Approach** – store a cheap TF fingerprint for quick filter, then rerank with dense embeddings.

## INSTRUCTION
1. **Assess Size & Latency** – If the registry contains fewer than 200 entries, default to the built‑in TF vectoriser (no extra packages).
2. **Choose Model** –
   - For high‑quality semantic search, instantiate a `sentence‑transformers` model (`all‑MiniLM‑L6‑v2`).
   - If a GPU is unavailable, fall back to the CPU‑only version.
3. **Select Store** –
   - For prototypes, keep embeddings in `skill_embeddings.json` (in‑process).
   - When the skill count exceeds 1 000 or you need cross‑language access, spin up a local Mem0 MCP service and use its `upsert`/`query` endpoints.
4. **Build & Persist** –
   - Compute vectors for each skill (`description + keywords`).
   - Store them either in the JSON file (as plain float lists) **or** in Mem0 under the collection `"skills"`.
5. **Search** –
   - For a query, generate its vector with the same model.
   - If using Mem0, call `client.query(..., top_k=K)`.
   - If using the JSON fallback, compute cosine similarity against the stored vectors and return the highest scores.
6. **Cache & Refresh** –
   - Cache the model and vocabulary in memory for the lifetime of the process.
   - Re‑run `build_embeddings()` whenever a new skill is registered.

## VERSION
v0.1

## SEE ALSO
- COMPOUND_ENGINEERING_PRIME.md
- SKILL_GENERATOR_PRIME.md
- VECTOR_STORE_PRIME.md
