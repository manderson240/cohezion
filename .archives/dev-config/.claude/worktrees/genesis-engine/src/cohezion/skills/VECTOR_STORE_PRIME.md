# SKILL: VECTOR_STORE_PRIME

## DOMAIN EXPERTISE
You are an authority on **persistent vector storage** for semantic retrieval. You understand the operational, performance, and data‑integrity aspects of local and remote vector stores, including Mem0 MCP, FAISS, Chroma, and SQLite‑based embeddings.

## KEY TEXTS & CONCEPTS
- **Mem0 MCP** – lightweight HTTP API that can ingest arbitrary dense vectors, supports collections, upserts, and similarity queries.
- **FAISS** – high‑performance C++/Python library for nearest‑neighbor search on large (10⁶+) vector sets; works best with GPU acceleration.
- **Chroma** – Python‑native vector DB that stores vectors in a local directory; easy to embed in a single‑process app.
- **SQLite + HNSW** – a pure‑SQL approach using the `hnswlib` extension; useful when a full DB engine is already present.

## INSTRUCTION
1. **Determine Scale** –  
   - ≤ 200 vectors → use the built‑in JSON file (`skill_embeddings.json`).  
   - 200 – 5 000 vectors → use **Chroma** (no external server).  
   - > 5 000 vectors or need cross‑process access → spin up a **Mem0 MCP** container.  
   - > 100 000 vectors or require GPU speed → integrate **FAISS** with an IVF‑PQ index.
2. **Provision the Store** –  
   - For Mem0: `docker run -p 8000:8000 mem0/mcp` (or start via `mem0 serve`).  
   - For Chroma: instantiate `chromadb.Client()` pointing to `./vector_store`.  
   - For FAISS: create an index with `faiss.IndexIVFFlat` and train on a sample of vectors.
3. **Schema Definition** – Store at least the following fields for each skill:  
   - `id` (skill name)  
   - `vector` (dense embedding)  
   - `metadata` (JSON with `path`, `description`, `keywords`).
4. **Upsert Routine** –  
   ```python
   def upsert_skill(name, vector, meta):
       # Choose backend based on configuration
       if backend == "mem0":
           client.upsert(collection="skills", ids=[name], vectors=[vector], metadatas=[meta])
       elif backend == "chroma":
           collection.add(ids=[name], embeddings=[vector], metadatas=[meta])
       # etc.
   ```
5. **Query Routine** –  
   ```python
   def query_skills(query_vector, top_k=10):
       if backend == "mem0":
           return client.query(collection="skills", query_vector=query_vector, top_k=top_k)
       # analogous for other backends
   ```
6. **Persistence & Backup** –  
   - For Mem0: mount a host volume (`-v ./mem0_data:/data`).  
   - For Chroma/FAISS: regularly copy the storage directory to a backup location or snapshot the SQLite file.
7. **Monitoring** – Expose health endpoints (`/healthz`) for the service and log latency metrics for each query; set alerts if 95th‑percentile latency exceeds 200 ms.

## VERSION
v0.1

## SEE ALSO
- EMBEDDING_STRATEGY_PRIME.md
- COMPOUND_ENGINEERING_PRIME.md
- SKILL_GENERATOR_PRIME.md