# SKILL: MASS_SIMULATION_PRIME

## DOMAIN EXPERTISE
Running large-scale (10k+) simulations locally without resource exhaustion.

## CRITICAL PATTERNS
1.  **Chunking:** Never process all items in one list. Process in batches (e.g., `chunk_size=500`).
2.  **Garbage Collection:** Explicitly clear memory and run `gc.collect()` between chunks.
3.  **Checkpointing:** Save results to disk after every N chunks. If it crashes, resume from last checkpoint.
4.  **Resource Monitoring:** Check RAM/CPU usage before starting a new chunk. Pause or abort if limits are exceeded.
5.  **Aggregation:** Keep light statistics in memory; offload heavy details to disk immediately.

## ANTI-PATTERNS
- Loading entire dataset into RAM.
- synchronous processing of CPU-bound tasks (use `ProcessPoolExecutor` if possible, or careful async).
- Infinite loops without safety caps.

## USAGE
See `src/cohezion/swarm/mass_simulator.py` for reference implementation.
