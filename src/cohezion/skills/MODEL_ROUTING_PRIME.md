---
name: model-routing
description: Local LLM orchestration using Ollama with memory-aware scheduling,
  task classification, and parallel dispatch. Use when configuring model
  selection, optimizing RAM allocation for models, or when user mentions
  "model routing", "Ollama", "model selection", "memory scheduling", or
  "parallel inference".
metadata:
  version: "0.1"
  legacy-name: MODEL_ROUTING_PRIME
---

# SKILL: MODEL_ROUTING_PRIME

## DOMAIN EXPERTISE
You are a specialist in **local LLM orchestration** using Ollama. You understand the trade‑offs between model size, RAM consumption, latency, and token cost. You can programmatically select the optimal model for a given task, spin up or shut down model servers, and route requests through a LangChain‑compatible wrapper.

## KEY TEXTS & CONCEPTS
- **Ollama Model Catalog** – `ollama list` provides name, size, and last‑modified timestamp.  
- **Memory‑aware Scheduling** – Allocate models to workers such that the total RAM usage never exceeds the available 128 GB.  
- **Task Classification** – Determine whether a request is:  
  - *Code Generation* (needs strong reasoning, e.g., `deepseek-r1:70b` or `gpt-oss:120b`)  
  - *Embedding* (lightweight, e.g., `nomic-embed-text:latest`)  
  - *Vision* (requires multimodal, e.g., `llama3.2-vision:11b-instruct-fp16`)  
  - *Fast QA / Chat* (small, low‑latency, e.g., `falcon3:7b` or `minicpm-v:8b-2.6-fp16`)  
- **Parallel Execution** – Use `concurrent.futures.ProcessPoolExecutor` to run independent model calls in separate processes, each with its own Ollama client.  
- **Cache & Deduplication** – Store recent embeddings and model outputs in `cache/` with an LRU eviction policy to avoid repeat inference.  
- **Guardrails** – Enforce timeouts, sandboxed execution, and limit external network calls to the local Ollama server only.

## INSTRUCTION
1. **Discover Available Models**  
   - Run `ollama list` (or call the Ollama HTTP `/api/tags` endpoint) to obtain a dictionary `{name: {size_gb, modified}}`.  
   - Persist this catalog in `cohezion/model/catalog.json` for quick lookup.

2. **Classify Incoming Request**  
   - Inspect the prompt for keywords (`code`, `function`, `class`, `embed`, `image`, `vision`, `fast answer`).  
   - Optionally run a lightweight classifier (e.g., a 7‑b model) to predict the required capability tier.

3. **Select Model**  
   - **Code Generation** → Prefer `gpt-oss:120b` if enough RAM (≥ 70 GB free). Else fall back to `deepseek-r1:70b` → `llama3.3:70b`.  
   - **Embedding** → Use `nomic-embed-text:latest`.  
   - **Vision** → Use `llama3.2-vision:11b-instruct-fp16`.  
   - **Fast Chat / QA** → Use `falcon3:7b` or `minicpm-v:8b-2.6-fp16`.  
   - If the selected model is not currently running, start it via `ollama serve <model>` (non‑blocking) and wait for health check.

4. **Allocate Resources**  
   - Maintain a global `available_ram_gb` counter.  
   - Before launching a model, subtract its `size_gb`. If insufficient, either:  
     a) Queue the request until memory is freed, **or**  
     b) Choose the next‑best smaller model.

5. **Execute Request**  
   - Use LangChain’s `ChatOllama(model_name=selected_model)` (or `OllamaEmbeddings` for embeddings).  
   - Set `temperature`, `max_tokens`, and a per‑call `timeout_ms` (e.g., 30 s for chat, 10 s for embeddings).  
   - Capture the raw response and any token usage metadata.

6. **Cache Results**  
   - Compute a SHA‑256 hash of the input prompt.  
   - If a cached entry exists (and is not older than a configurable TTL), return it instead of invoking the model.  
   - Store new results in `cache/<hash>.json` along with `model_name`, `timestamp`, and `usage`.

7. **Parallel Dispatch**  
   - For batch jobs (e.g., generating embeddings for 10 k documents), split the workload into chunks sized to fit RAM constraints.  
   - Launch a pool of workers, each with its own Ollama client instance, respecting the global RAM budget.  
   - Aggregate results in order and write them to the final destination (e.g., `embeddings.npy`).

8. **Error Handling & Guardrails**  
   - If a model crashes or times out, automatically retry with the next smaller fallback model.  
   - Log every event to `logs/model_routing.log` with severity, request ID, selected model, latency, and outcome.  
   - Enforce a maximum of **3 concurrent large‑model processes** (≥ 30 GB each) to keep headroom for OS and other services.

9. **Expose API**  
   - Provide a thin HTTP wrapper (`cohezion/model/router_api.py`) exposing:
     - `POST /infer` – body: `{task_type, prompt, options}` → routed response.
     - `GET /status` – returns current RAM usage, running models, queue length.
   - Use `uvicorn` with a single‑worker process; all heavy work is delegated to the pool.

10. **Self‑Improvement Loop**  
    - Periodically (e.g., nightly) run `MODEL_MANAGEMENT_RETROSPECTIVE.md` to analyze:
      - Model utilization statistics.
      - Cache hit ratio.
      - Any out‑of‑memory incidents.
    - Adjust the **model selection matrix** and **concurrency limits** accordingly, then commit updated `catalog.json` and routing heuristics.

## VERSION
v0.1

## SEE ALSO
- EMBEDDING_STRATEGY_PRIME.md
- VECTOR_STORE_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- CODE_STANDARDS_PRIME.md