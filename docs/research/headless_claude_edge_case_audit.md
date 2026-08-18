# Headless Claude Edge-Case Audit & Resilience Report

## Current Architecture Summary
Cohezion's runtime operates across 4 core engines:
1. **Spinning Plates Protocol**: A background scheduler maintaining 6 concurrent asynchronous tasks (Plates) to maximize hardware utilization (NPU/iGPU/CPU).
2. **Atomic Model Hot-Swapper**: A FleetLock-gated component managing local VRAM by cleanly unloading models before allocating memory for new inference targets.
3. **AutoHarness Policy Engine**: A deterministic, zero-latency AST evaluation engine to pre-verify `CodeAsAction` against bounds, safety rules, and functional complexity.
4. **Unified Hybrid Router**: A tiered router shifting workloads across Local Silicon (Tier 1) and Ollama Cloud (Tier 2) using circuit breakers and memory guards.

## Risks and Constraints (Edge-Case Findings)

### 1. Spinning Plates Protocol
- **Memory Boundary Fluctuation (20.0 GiB):** Plate 4 detects memory falling below `min_available_gb` and correctly flags `is_safe = False`, but **only logs a warning**. It fails to exert true backpressure (e.g., suspending other plates or pausing the aggregator), allowing OOM events if other threads ignore the log.
- **Network Partitioning / Daemon Crashes:** If Ollama Cloud crashes, Plate 5's `urllib` call times out. The exception is swallowed and stringified into `last_outcome`, causing the thread to continue polling every 3.0s in a busy-wait failure loop instead of applying exponential backoff.
- **Fréchet Gradient Race Conditions:** While thread-local `v1` and `v2` prevent data races, if the centroid diverges (`norm >= 1.0`) due to hyperbolic boundary limits, `compute_frechet_mean` may output NaNs. The check `centroid.norm < 1.0` is only used for string logging; math instability is not handled or bounded.

### 2. Atomic Model Hot-Swapper
- **Lemonade Server HTTP 500 / Hangs:** `unload_active_models()` catches `urllib` exceptions and returns `False` if Lemonade 500s or times out. However, `hotswap_model()` completely ignores this return value. It proceeds to `gc.collect()` and checks memory. If the model didn't unload, the memory floor check might subsequently fail, causing unnecessary hot-swap rejections.
- **Emergency Swap under FleetLock:** `FleetLock("modelload")` is a standard asyncio single-flight mutex with no priority queuing. If an emergency priority swap is requested while a massive 30B parameter model is mid-load (or hung), the emergency thread is completely blocked indefinitely with no preemption mechanism.

### 3. AutoHarness Policy Engine
- **Malicious AST Bypasses:** The AST verifier is highly vulnerable to indirect execution. It blocks direct `eval()` and explicit imports (e.g., `import os`), but misses `__import__("os")`, `importlib.import_module`, and function aliasing (`e = eval; e(x)`). A malicious agent can easily bypass the static import checks.
- **Resource Exhaustion & Recursion Bombs:** While AST nodes are limited to 500, memory-exhausting constructs like `x = [0] * 10**9` or deep recursion (no static check for self-calling functions) easily bypass the check, converting small valid ASTs into catastrophic memory bombs at execution.

### 4. Unified Hybrid Router
- **Simultaneous Unreachability:** If both Lemonade and Ollama Cloud fail, the router gracefully degrades. It falls through to Tier 0, returning a synthetic unverified string response detailing memory headroom (`[Local Silicon & Cloud Standby] Backends offline...`). It does not crash.
- **Cascading Retry Storms:** The router protects Lemonade via an intelligent `get_circuit()` circuit breaker (3 failures -> 20s timeout). **However, Ollama Cloud has no circuit breaker.** If the cloud backend hangs, every single Tier 2 fallback request will individually hang for the full 60.0s `httpx` timeout, rapidly exhausting file descriptors and causing a total concurrency stall.

## Proposed Design with Rationale

**Option 1: The Apical Governor Pattern (Recommended)**
- **Spinning Plates:** Introduce an `asyncio.Event` or global pause flag triggered by Plate 4 to actively freeze computationally heavy plates.
- **Hot-Swapper:** Implement a Priority-Aware FleetLock (`PriorityMutex`) allowing emergency swaps to cancel active lower-priority hot-swaps.
- **AutoHarness:** Replace naive AST traversal with an execution sandbox (e.g., restricted `globals()` dictionary during `exec`), neutralizing indirect execution and enforcing memory limits natively.
- **Router:** Wrap the `aquery_ollama_cloud` transport in the existing `get_circuit("ollama_cloud")` logic to prevent HTTP timeout storms.

**Option 2: Strict Isolation Pattern**
- Push code actions into a separate hardened Docker container rather than AST parsing.
- Let OS-level Cgroups handle memory limits rather than manual Plate/Hot-Swap polling.
*Tradeoff:* Adds massive latency, breaking the 0ms verification requirement.

**Why Option 1 is Safest:** It preserves the zero-latency, local-first architecture while patching the most critical vulnerabilities (indirect execution, missing circuit breakers, and unforced OOMs).

## Implementation Handoff Checklist
- [x] `docs/research/headless_claude_edge_case_audit.md` generated and saved.
- [ ] Add `get_circuit("ollama_cloud")` to `UnifiedHybridRouter`.
- [ ] In `dynamic_hotswapper.py`, check `unload_active_models()` return value before proceeding.
- [ ] In `SpinningPlatesGovernor`, propagate the `is_safe` backpressure event from Plate 4 to pause compute plates.
