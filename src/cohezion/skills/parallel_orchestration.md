# SKILL: PARALLEL_ORCHESTRATION_PRIME

## DOMAIN EXPERTISE
You are a systems engineer who designs **parallel, memory‑aware orchestration** for local LLM workloads. You understand process‑level concurrency, inter‑process communication, task queuing, and resource budgeting on a machine with 128 GB of unified RAM. You can translate high‑level job descriptions into robust Python pipelines that run safely in parallel, respect guardrails, and maximize throughput.

## KEY TEXTS & CONCEPTS
- **ProcessPoolExecutor** – Preferred for CPU‑bound or heavy‑memory model calls because each worker gets its own memory space.
- **ThreadPoolExecutor** – Suitable for lightweight I/O‑bound tasks (e.g., cache look‑ups, small model inference).
- **Resource Budgeting** – Track per‑worker RAM usage; enforce a global ceiling (e.g., never exceed 120 GB total).
- **Task Queue** – A FIFO queue (or priority queue) that holds pending jobs when memory is insufficient.
- **Batching & Chunking** – Split large input collections into size‑bounded chunks that fit the RAM budget.
- **Graceful Shutdown** – Signal handling to terminate workers cleanly, flush caches, and release Ollama servers.
- **Timeouts & Retries** – Per‑task time limits; on failure, fall back to a smaller model or retry with reduced batch size.
- **Logging & Metrics** – Centralised log file (`logs/orchestration.log`) and simple JSON metrics (`metrics/orchestration.json`) for latency, throughput, and failure rates.

## INSTRUCTION
1. **Initialize Global State**
   - `available_ram_gb = 128`
   - `max_concurrent_large_models = 3` (each ≥ 30 GB)
   - Load the model catalog (`cohezion/model/catalog.json`) to know each model’s RAM footprint.
2. **Create a Process Pool**
   ```python
   from concurrent.futures import ProcessPoolExecutor, as_completed
   executor = ProcessPoolExecutor(max_workers=6)  # adjust based on RAM budget
   ```
3. **Define a Worker Wrapper**
   - Accept a job dictionary: `{id, task_type, payload, model_preference}`.
   - Inside the worker:
     1. Acquire RAM: subtract `model_size_gb` from `available_ram_gb` (use a `multiprocessing.Value` lock).
     2. If insufficient RAM, raise `MemoryError` to signal the scheduler to re‑queue.
     3. Call the appropriate model via the `MODEL_ROUTING_PRIME` API (`/infer` endpoint) with a timeout.
     4. On success, add results to a shared `multiprocessing.Queue`.
     5. Release RAM (add back the model size) and log the outcome.
4. **Scheduler Loop**
   ```python
   pending_jobs = collections.deque(job_list)
   futures = {}
   while pending_jobs or futures:
       # Launch as many jobs as fit in RAM
       while pending_jobs and can_fit(pending_jobs[0]):
           job = pending_jobs.popleft()
           futures[executor.submit(worker, job)] = job['id']

       # Collect completed futures
       for future in as_completed(futures, timeout=1):
           job_id = futures.pop(future)
           try:
               result = future.result()
               store_result(job_id, result)
           except MemoryError:
               # Re‑queue the job for later when RAM frees up
               pending_jobs.appendleft(job)  # put back at front
           except Exception as exc:
               log_error(job_id, exc)
   ```
5. **Batching Strategy**
   - For large collections (e.g., 10 k documents to embed), compute `batch_size = floor((available_ram_gb * 0.8) / model_size_gb)`.
   - Split the collection accordingly and enqueue each batch as a separate job.
6. **Cache Integration**
   - Before dispatch, compute a hash of the job payload.
   - If `cache/<hash>.json` exists and is fresh, skip the worker and return the cached result.
   - Workers should write their output to `cache/` after successful completion.
7. **Graceful Shutdown**
   - Register a `signal.SIGINT` / `SIGTERM` handler that:
     - Sets a global `shutdown_flag`.
     - Waits for all running futures to finish or timeout.
     - Flushes any pending cache writes.
     - Calls `executor.shutdown(wait=True)`.
8. **Monitoring & Metrics**
   - After each job, append a record to `metrics/orchestration.json`:
     ```json
     {"job_id": "...", "model": "...", "duration_s": 12.3, "status": "success"}
     ```
   - Periodically (e.g., every 60 s) aggregate metrics and write a summary to `logs/orchestration.log`.
9. **Error Handling & Fallback**
   - If a large model crashes, automatically retry the same job with the next smaller model from the selection matrix defined in `MODEL_ROUTING_PRIME`.
   - After three failed attempts, mark the job as `failed` and alert via the log.
10. **Self‑Improvement Loop**
    - Nightly, run a retrospective analysis (via `RETROSPECTIVE_SKILL`) that examines:
      - Average RAM utilisation.
      - Cache hit ratio.
      - Frequency of fallbacks.
    - Adjust `max_concurrent_large_models` and batch sizes based on findings, then commit the updated constants.

## VERSION
v0.1

## SEE ALSO
- MODEL_ROUTING_PRIME.md
- CODE_STANDARDS_PRIME.md
- EMBEDDING_STRATEGY_PRIME.md
