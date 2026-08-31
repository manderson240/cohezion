# Multi-Perspective Adversarial Review: Sovereign Spinning Plates Protocol

**Timestamp**: 2026-08-17 22:06:20 EDT

**Evaluators**: `deepseek-v4-pro:cloud`, `qwen3.5:397b-cloud`, `glm-5.2:cloud`

---

## Perspective: deepseek-v4-pro:cloud — Red Team Concurrency, Memory & Subprocess Security Specialist


## Adversarial Red Team Review: Cohezion Sovereign Spinning Plates Protocol

### 1. CRITICAL VULNERABILITIES & CONCURRENCY BOTTLENECKS

#### 1.1 Task Cancellation Leak & Unretrieved Exceptions
**Severity: CRITICAL**

`start_spinning_plates()` cancels tasks but never awaits them. This causes:

- Pending tasks to be destroyed with `Task was destroyed but it is pending!` warnings.
- Exceptions raised inside tasks (including `CancelledError`) are never retrieved, leading to `Task exception was never retrieved` warnings.
- If a task is blocked in a synchronous operation or `run_in_executor`, cancellation does not stop the underlying thread, leaking resources.
- No guarantee that all plates have actually stopped when the method returns.

**Proof:**
```python
if duration_sec is not None:
    await asyncio.sleep(duration_sec)
    self.running = False
    for t in tasks:
        t.cancel()          # <-- not awaited
    logger.info("✓ Completed ...")
```

**Fix:**
```python
if duration_sec is not None:
    await asyncio.sleep(duration_sec)
    self.running = False
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)  # await cancellation
    logger.info("✓ Completed ...")
```

#### 1.2 No Stop Mechanism for Indefinite Run
**Severity: HIGH**

When `duration_sec=None`, `start_spinning_plates()` returns immediately after creating tasks. The tasks run forever, but there is no public method to stop them. The only way to stop is to set `governor.running = False` externally, which is fragile and not thread-safe.

**Fix:** Add a `stop()` method and use an `asyncio.Event` for clean shutdown.

```python
def __init__(self, ...):
    self._stop_event = asyncio.Event()
    self.running = False

async def start_spinning_plates(self, duration_sec=None):
    self.running = True
    self._stop_event.clear()
    tasks = [...]
    if duration_sec is not None:
        await asyncio.sleep(duration_sec)
        await self.stop()
    # else: return, tasks continue until stop() called

async def stop(self):
    self.running = False
    self._stop_event.set()
    # optionally cancel and await tasks if stored
```

#### 1.3 Uncaught Exceptions Kill Plates Silently
**Severity: CRITICAL**

Every plate loop (`spin_plate_ast_verification`, `spin_plate_poincare_calibration`, etc.) lacks a `try/except` around its work. If any operation raises (e.g., `verifier.verify_code()` fails, `frechet_aggregator.compute_frechet_mean()` throws, `OOMGuard.get_memory_state()` errors), that task dies. The plate stops spinning, but `self.running` remains `True`, so other plates continue unaware. The system violates its own “all plates active” invariant.

**Fix:** Wrap each iteration in a robust exception handler with backoff.

```python
async def spin_plate_ast_verification(self):
    while self.running:
        try:
            t0 = time.perf_counter()
            code_sample = "..."
            res = await asyncio.to_thread(self.verifier.verify_code, code_sample)
            dt = (time.perf_counter() - t0) * 1000.0
            p = self.plates["ast_verifier"]
            p.iterations += 1
            p.last_duration_ms = round(dt, 3)
            p.last_outcome = f"Verified Valid (Score {res.score})"
        except asyncio.CancelledError:
            raise
        except Exception as exc:
            logger.exception("Plate ast_verifier failed: %s", exc)
            p.last_outcome = f"ERROR: {type(exc).__name__}"
        await asyncio.sleep(2.0)
```

#### 1.4 Blocking the Event Loop with CPU-Bound Work
**Severity: CRITICAL**

The following plates perform synchronous, CPU‑intensive work directly inside `async` functions:

- `spin_plate_ast_verification` → `self.verifier.verify_code(code_sample)`
- `spin_plate_poincare_calibration` → `self.frechet_aggregator.compute_frechet_mean(...)`
- `spin_plate_multimodal_uma_guard` → `OOMGuard.get_memory_state()` (may be quick, but still synchronous)

Because these operations do not `await`, they block the entire event loop. While one plate is computing, **all other plates and the rest of the application are frozen**. This defeats the purpose of concurrent spinning plates and can cause timeouts in external systems.

**Fix:** Offload blocking calls to a thread or process executor using `asyncio.to_thread` or `loop.run_in_executor`.

```python
# Example for AST verification
res = await asyncio.to_thread(self.verifier.verify_code, code_sample)

# Example for Poincaré
centroid = await asyncio.to_thread(
    self.frechet_aggregator.compute_frechet_mean, [p1, p2], max_iter=5
)
```

#### 1.5 Cloud Researcher Thread Leak on Cancellation
**Severity: HIGH**

`spin_plate_cloud_researcher` uses `loop.run_in_executor(None, _fetch)`. If the task is cancelled while the executor thread is running (e.g., during shutdown), the thread continues until the `urllib` timeout (5 seconds) expires. This can leak threads and delay program exit.

**Fix:** Use `asyncio.wait_for` to enforce an overall timeout and handle cancellation gracefully.

```python
try:
    resp_data = await asyncio.wait_for(
        loop.run_in_executor(None, _fetch), timeout=5.0
    )
except asyncio.TimeoutError:
    outcome = "Cloud request timed out"
except asyncio.CancelledError:
    # Optionally cancel the underlying future if possible
    raise
```

#### 1.6 No Hardware Concurrency Control
**Severity: HIGH**

`HardwareFleetLockApicalConcurrencyGovernor` is instantiated but **never used**. All plates run simultaneously without any locking or resource arbitration. On a system with limited NPU/iGPU/CPU resources, this can cause contention, thrashing, or even OOM kills.

**Fix:** Acquire the appropriate fleet lock before executing hardware‑specific work.

```python
async with self.fleet_lock.acquire("modelload"):
    # perform NPU/GPU work
```

### 2. HARDWARE-UMA OR MATHEMATICAL VIOLATIONS

#### 2.1 UMA Memory Starvation – `min_available_gb` Ignored
**Severity: CRITICAL**

The constructor accepts `min_available_gb=20.0` and the documentation states that all plates must respect a 20 GiB floor. However, **this value is never used**. Plate 4 only *monitors* memory but does not enforce any threshold. Other plates do not check memory at all. Under load, the system can exhaust UMA memory, causing OOM kills or system instability.

**Fix:** Before each plate iteration, check `OOMGuard.get_memory_state()` and skip or delay if available memory is below the threshold.

```python
async def _check_memory_safety(self) -> bool:
    mem = OOMGuard.get_memory_state()
    if mem.available_gb < self.min_available_gb:
        logger.warning("Insufficient UMA memory: %.1f GiB < %.1f GiB",
                       mem.available_gb, self.min_available_gb)
        return False
    return True

# Inside each plate loop:
if not await self._check_memory_safety():
    await asyncio.sleep(10.0)  # backoff
    continue
```

#### 2.2 Poincaré Plate Uses 3D Instead of 2048D
**Severity: HIGH**

The documentation and class name claim “2048D Poincaré Fréchet & CTAC Geodesic Streamer”, but the code projects points into **3 dimensions**:

```python
p1 = PoincareManifoldND.project((0.15, 0.25, 0.05), target_dim=3)
p2 = PoincareManifoldND.project((-0.10, 0.18, -0.05), target_dim=3)
```

This is a direct violation of the stated mathematical domain. It also does not validate that the resulting centroid has norm < 1 (inside the Poincaré ball), which is required for hyperbolic geometry.

**Fix:** Use `target_dim=2048` and validate the norm.

```python
p1 = PoincareManifoldND.project((0.15, 0.25, 0.05), target_dim=2048)
p2 = PoincareManifoldND.project((-0.10, 0.18, -0.05), target_dim=2048)
centroid = await asyncio.to_thread(
    self.frechet_aggregator.compute_frechet_mean, [p1, p2], max_iter=5
)
if centroid.norm >= 1.0:
    logger.error("Poincaré centroid escaped unit ball: norm=%.4f", centroid.norm)
```

#### 2.3 Cloud Researcher Uses Localhost Instead of Cloud
**Severity: MEDIUM**

The URL is `http://localhost:11434/api/generate`, which points to a **local** Ollama instance, not a cloud service. The documentation explicitly says “Ollama Cloud Frontier Bleeding-Edge Research Cascade”. This means the plate is not actually using cloud resources, defeating its purpose.

**Fix:** Use the correct cloud endpoint (e.g., `https://api.ollama.cloud/...`) or rename the plate to reflect local usage.

#### 2.4 Sheaf Consistency Gate Unused
**Severity: LOW**

`SheafConsistencyGate` is instantiated but never called. If the protocol is meant to enforce sheaf consistency, this is a missing safety check.

### 3. CONCRETE HARDENING RECOMMENDATIONS

#### 3.1 Robust Task Supervision with Restart
Implement a supervisor that monitors plate tasks and restarts them if they die unexpectedly.

```python
async def _supervise_plate(self, coro_factory, plate_name):
    while self.running:
        task = asyncio.create_task(coro_factory())
        try:
            await task
        except asyncio.CancelledError:
            break
        except Exception as exc:
            logger.error("Plate %s crashed: %s. Restarting in 5s.", plate_name, exc)
            await asyncio.sleep(5)
```

#### 3.2 Enforce Timeouts on All Plate Work
Wrap every plate’s core operation in `asyncio.wait_for` to prevent hangs.

```python
try:
    res = await asyncio.wait_for(
        asyncio.to_thread(self.verifier.verify_code, code_sample),
        timeout=10.0
    )
except asyncio.TimeoutError:
    p.last_outcome = "TIMEOUT"
```

#### 3.3 Use `asyncio.Event` for Clean Shutdown
Replace the boolean `self.running` with an `asyncio.Event` to allow multiple tasks to wait for shutdown without polling.

```python
def __init__(self, ...):
    self._shutdown_event = asyncio.Event()
    self.running = False

async def start_spinning_plates(self, duration_sec=None):
    self.running = True
    self._shutdown_event.clear()
    tasks = [...]
    if duration_sec is not None:
        await asyncio.sleep(duration_sec)
        await self.stop()
        await asyncio.gather(*tasks, return_exceptions=True)

async def stop(self):
    self.running = False
    self._shutdown_event.set()
```

#### 3.4 Integrate Fleet Lock and OOM Guard
Acquire hardware locks and check memory before each iteration.

```python
async def spin_plate_poincare_calibration(self):
    while self.running:
        if not await self._check_memory_safety():
            await asyncio.sleep(10)
            continue
        async with self.fleet_lock.acquire("npu"):
            try:
                # ... compute ...
            except Exception as exc:
                logger.exception("Poincaré plate failed: %s", exc)
        await asyncio.sleep(3.0)
```

#### 3.5 Fix Poincaré Dimension and Validation
Use 2048 dimensions and validate the centroid norm.

```python
p1 = PoincareManifoldND.project((0.15, 0.25, 0.05), target_dim=2048)
p2 = PoincareManifoldND.project((-0.10, 0.18, -0.05), target_dim=2048)
centroid = await asyncio.to_thread(
    self.frechet_aggregator.compute_frechet_mean, [p1, p2], max_iter=5
)
if centroid.norm >= 1.0:
    logger.error("Invalid Poincaré centroid: norm=%.4f", centroid.norm)
```

### 4. FINAL ADVERSARIAL VERDICT

**BLOCKED**

The Spinning Plates Governor in its current form contains **critical task lifecycle leaks**, **uncaught exception propagation**, **event-loop blocking**, **UMA memory starvation**, and **mathematical domain violations**. These defects can lead to resource exhaustion, silent plate death, system freezes, and violation of the protocol’s own safety guarantees. The code must be hardened according to the recommendations above before it can be considered production‑ready.


---

## Perspective: qwen3.5:397b-cloud — Principal Distributed Scheduling & Heterogeneous UMA Hardware Architect


# ARCHITECTURAL REVIEW: COHEZION SPINNING PLATES PROTOCOL
**Reviewer:** Principal Distributed Systems & Strix Halo Hardware Architect
**Date:** 2024-05-21
**Subject:** Adversarial Critique of `SpinningPlatesGovernor` Implementation
**Verdict:** **BLOCKED**

---

## 1. CRITICAL VULNERABILITIES & CONCURRENCY BOTTLENECKS

### 1.1 Event Loop Starvation (Severity: CRITICAL)
The implementation assumes `asyncio` provides parallelism. It does not. It provides concurrency on a **single thread**.
*   **The Flaw:** `spin_plate_poincare_calibration` (Plate 2) and `spin_plate_ast_verification` (Plate 1) execute synchronous, CPU-bound mathematics (`compute_frechet_mean`, `verify_code`) directly on the event loop thread.
*   **The Consequence:** If Plate 2 takes 200ms to compute geodesics, **all 5 other plates are frozen** for that duration. This violates the "100% utilization" claim by creating serialized bottlenecks on the main thread. The `asyncio.sleep` drift compounds this, causing scheduling jitter across the entire "fleet."
*   **Evidence:**
    ```python
    # BLOCKING CALL ON EVENT LOOP
    centroid = self.frechet_aggregator.compute_frechet_mean([p1, p2], max_iter=5)
    await asyncio.sleep(3.0)
    ```

### 1.2 Hardware Lane Hallucination (Severity: HIGH)
The code claims explicit hardware lane assignment (`hardware_lane="NPU"`, `"iGPU"`), but implements **zero hardware affinity or offloading**.
*   **The Flaw:** AMD Strix Halo NPU execution requires specific runtime bindings (e.g., `ryzen-ai` SDK, DirectML, or ONNX Runtime with Vitis AI). Pure Python math (`PoincareManifoldND`) runs on CPU cores (AVX512), not the NPU.
*   **The Consequence:** The system will thrash CPU L3 cache while the NPU sits idle. Claiming "NPU" usage in telemetry while executing scalar Python math is observability fraud.
*   **Evidence:** `PlateStatus` defines `hardware_lane="NPU"`, but `spin_plate_poincare_calibration` contains no NPU kernel invocations.

### 1.3 Backpressure Void (Severity: HIGH)
`Plate 4` (UMA Guard) monitors memory but **never acts** on the data.
*   **The Flaw:** `OOMGuard.get_memory_state()` returns `is_safe`, but the loop ignores it. If memory drops below `min_available_gb`, Plates 1, 2, and 3 continue allocating tensors/buffers.
*   **The Consequence:** In a high-load scenario, the system will OOM kill the process despite the "Guard" plate reporting "Unsafe" in telemetry until the crash occurs.
*   **Evidence:**
    ```python
    mem = OOMGuard.get_memory_state()
    # ... logging ...
    await asyncio.sleep(4.0) # Continues regardless of mem.is_safe
    ```

### 1.4 Cancellation & Resource Leak (Severity: MEDIUM)
*   **The Flaw:** `start_spinning_plates` calls `t.cancel()` on tasks. The `while self.running` loops do not catch `asyncio.CancelledError`.
*   **The Consequence:** Tasks die immediately mid-execution. If Plate 5 is mid-HTTP request or Plate 2 is mid-matrix op, resources (sockets, temporary buffers) may not be gracefully released. Telemetry finalization is skipped.

---

## 2. HARDWARE-UMA & MATHEMATICAL VIOLATIONS

### 2.1 Dimensionality Mismatch (Math Integrity)
*   **Claim:** Docstring states "2048D Hyperbolic Fréchet Calibration".
*   **Reality:** Code passes 3-tuples: `PoincareManifoldND.project((0.15, 0.25, 0.05), target_dim=3)`.
*   **Violation:** You are not calibrating a 2048D manifold; you are normalizing 3D vectors. This invalidates any downstream physics engine (`CTACEngine`) relying on high-dimensional topology.

### 2.2 UMA Buffer Misrepresentation
*   **Claim:** "Multimodal Zero-Copy UMA Buffer Health".
*   **Reality:** `OOMGuard.get_memory_state()` typically reads `/proc/meminfo` (system RAM). It does not inspect VRAM carve-outs or specific UMA reservation registers on Strix Halo.
*   **Violation:** System RAM availability ≠ UMA Buffer Health. The iGPU could be starving while System RAM is free.

### 2.3 Network Topology Contradiction
*   **Claim:** "Ollama Cloud Frontier... `deepseek-v4-flash:cloud`".
*   **Reality:** URL is `http://localhost:11434`.
*   **Violation:** `localhost` is not Cloud. This is a local Ollama instance. If the intent is to call actual cloud APIs, the endpoint is wrong. If the intent is local, the labeling "Cloud Frontier" is misleading observability.

---

## 3. CONCRETE HARDENING RECOMMENDATIONS

### 3.1 Offload CPU-Bound Work (Fix Starvation)
Move heavy math and verification to a thread pool to prevent event loop blocking.

```python
# src/cohezion/proactive/spinning_plates_protocol.py

async def spin_plate_poincare_calibration(self):
    loop = asyncio.get_running_loop()
    while self.running:
        t0 = time.perf_counter()
        # OFFLOAD TO EXECUTOR TO PREVENT LOOP BLOCKING
        p1, p2 = (0.15, 0.25, 0.05), (-0.10, 0.18, -0.05)
        centroid = await loop.run_in_executor(
            None, 
            lambda: self.frechet_aggregator.compute_frechet_mean(
                [PoincareManifoldND.project(p1, 3), PoincareManifoldND.project(p2, 3)], 
                max_iter=5
            )
        )
        # ... update state ...
```

### 3.2 Implement Active Backpressure (Fix OOM Risk)
The Governor must halt non-essential plates when memory thresholds are breached.

```python
# src/cohezion/proactive/spinning_plates_protocol.py

async def spin_plate_multimodal_uma_guard(self):
    while self.running:
        mem = OOMGuard.get_memory_state()
        # ACTIVE BACKPRESSURE SIGNAL
        if not mem.is_safe:
            logger.warning("⚠️ UMA CRITICAL: Pausing heavy plates...")
            self.fleet_lock.acquire_lock("memory_pressure") # Hypothetical lock
        
        # ... update state ...
        
        if not mem.is_safe:
            await asyncio.sleep(1.0) # Poll faster during pressure
        else:
            await asyncio.sleep(4.0)
```

### 3.3 Fix Hardware Lane Affinity (Strix Halo Specific)
If claiming NPU usage, you must invoke the NPU. If not, label it CPU.

```python
# src/cohezion/proactive/spinning_plates_protocol.py

def __init__(self, ...):
    # ...
    self.plates: dict[str, PlateStatus] = {
        # CORRECTED LANES BASED ON ACTUAL IMPLEMENTATION
        "poincare_calibrator": PlateStatus(..., hardware_lane="CPU (AVX512)"), 
        "multimodal_uma_guard": PlateStatus(..., hardware_lane="CPU (System RAM)"),
        # ...
    }
```

### 3.4 Graceful Cancellation & Sleep Drift Correction
Handle `CancelledError` and use fixed-interval scheduling.

```python
# src/cohezion/proactive/spinning_plates_protocol.py

async def spin_plate_ast_verification(self):
    next_run = time.perf_counter()
    while self.running:
        try:
            # ... work ...
            
            # DRIFT CORRECTION
            next_run += 2.0
            sleep_time = max(0, next_run - time.perf_counter())
            await asyncio.sleep(sleep_time)
            
        except asyncio.CancelledError:
            logger.info(f"Plate {self.plates['ast_verifier'].name} shutting down gracefully...")
            # Final telemetry flush here
            raise
```

---

## 4. FINAL ADVERSARIAL VERDICT

**STATUS:** **BLOCKED**

**RATIONALE:**
The current implementation is a **simulation of concurrency**, not a production-grade distributed systems protocol. It fails the primary architectural mandate of "Strix Halo Hardware Optimization" by ignoring actual hardware affinity (NPU/iGPU), risking event loop starvation via blocking calls, and implementing a passive OOM guard that offers no safety guarantee. The mathematical discrepancy (2048D vs 3D) undermines the scientific validity of the physics engine integration.

**REQUIRED ACTIONS FOR RE-APPROVAL:**
1.  **Refactor** all CPU-bound math into `run_in_executor` or separate processes.
2.  **Implement** active backpressure logic that pauses plates on memory warnings.
3.  **Correct** hardware lane labels to match actual execution units (or implement actual NPU offloading).
4.  **Fix** mathematical dimensionality consistency in `PoincareManifoldND`.
5.  **Add** graceful shutdown handlers for `CancelledError`.

Do not deploy this to sovereign hardware until these structural integrity issues are resolved. The current state risks system instability under load.

**Signed,**
*Principal Architect, Distributed Systems*


---

## Perspective: glm-5.2:cloud — Formal Category Theorist & Symplectic Invariant Evaluator


Here is the exhaustive, adversarial, and uncompromising code review of the Cohezion Sovereign Spinning Plates Protocol, analyzed through the lens of formal mathematical physics, category theory, and systems concurrency.

### 1. CRITICAL VULNERABILITIES & CONCURRENCY BOTTLENECKS

**A. Catastrophic Event Loop Blocking (The "Fake Concurrency" Problem)**
The most severe vulnerability is that Plates 1, 2, and 4 execute synchronous, CPU-bound operations directly within the `asyncio` event loop. 
- `self.verifier.verify_code(code_sample)` (Plate 1)
- `PoincareManifoldND.project(...)` and `self.frechet_aggregator.compute_frechet_mean(...)` (Plate 2)
- `OOMGuard.get_memory_state()` (Plate 4)

Because Python's `asyncio` is single-threaded, these synchronous calls will block the event loop entirely. The "concurrent" plates will actually execute serially. The `await asyncio.sleep()` calls are the only asynchronous points, meaning the system is effectively a sequential loop with sleep delays, completely failing the "100% utilization via concurrency" mandate.

**B. Silent Task Death and Missing Exception Boundaries**
None of the `while self.running:` loops contain `try...except` blocks. If `verify_code` throws a `SyntaxError`, or if the Fréchet aggregator encounters a numerical instability (e.g., points too close to the Poincaré boundary causing a division by zero), the task will crash silently. The plate will stop spinning, but `self.running` remains `True`, and the governor will report a stale "last_outcome" indefinitely.

**C. Improper Task Cancellation and Zombie Tasks**
In `start_spinning_plates`, when the duration expires, the code calls `t.cancel()` but never awaits the tasks. If a task is currently blocked in a synchronous call (which it will be, per point A), it cannot process the `CancelledError` until it reaches the next `await`. Furthermore, without `asyncio.gather(*tasks, return_exceptions=True)`, the `CancelledError` will propagate and potentially crash the caller, leaving dangling coroutines.

**D. Thread Pool Exhaustion (Plate 5)**
Plate 5 uses `loop.run_in_executor(None, _fetch)`, utilizing the default `ThreadPoolExecutor`. If the Ollama endpoint hangs or the network drops, the thread is occupied indefinitely (up to the 5.0s timeout). If multiple plates start using the default executor, it will become a severe bottleneck. 

### 2. HARDWARE-UMA OR MATHEMATICAL VIOLATIONS

**A. Mathematical Misrepresentation: The "2048D" Fallacy**
The docstring and skill file explicitly claim "2048D Poincaré Hyperbolic Fréchet Calibration". However, the code explicitly projects to `target_dim=3`:
```python
p1 = PoincareManifoldND.project((0.15, 0.25, 0.05), target_dim=3)
```
This is a blatant violation of the stated mathematical constraints. Reducing to 3D destroys the topological properties required for high-dimensional hierarchical embeddings.

**B. Fréchet Mean Convergence Failure**
The Fréchet mean on the Poincaré ball is computed via Riemannian gradient descent, which is highly sensitive to the manifold's sectional curvature ($-1$) and the distance of points from the origin. Hardcoding `max_iter=5` provides zero convergence guarantees. If the gradient norm does not fall below a threshold $\epsilon$, the resulting "centroid" is mathematically meaningless and may lie outside the valid geodesic convex hull of the input points.

**C. Sheaf-Theoretic Vacuity**
The `SheafConsistencyGate` is instantiated but **never invoked**. The entire protocol claims to maintain "sheaf-theoretic consistency," but the plates operate in completely isolated silos. There is no gluing of local sections, no stalk verification, and no checking of cohomological obstructions ($\dim H^1 > 0$). The sheaf gate is dead code.

**D. Symplectic Phase-Space Absence**
The prompt and imports mention symplectic phase-space preservation and CTAC ODE geodesics. The `CTACEngine` is instantiated but never called. There is no symplectic integrator (e.g., implicit midpoint or Leapfrog) ensuring that the discrete flow map preserves the symplectic 2-form $\omega = \sum dp_i \wedge dq_i$. The physics engine is entirely disconnected from the execution loop.

**E. Hardware Aperture Ignored (UMA/NPU/iGPU)**
The `HardwareFleetLockApicalConcurrencyGovernor` is instantiated but never used. The `hardware_lane` attribute in `PlateStatus` is purely cosmetic string metadata. There is no actual acquisition of `FleetLock("modelload")`, no NPU offloading via OpenVINO/ONNX-RT, and no iGPU dispatch via ROCm/Vulkan. The protocol runs entirely on the CPU, violating the "Sovereign Local Inference" mandate.

### 3. CONCRETE HARDENING RECOMMENDATIONS

**Recommendation 1: Fix Event Loop Blocking via `asyncio.to_thread`**
Wrap all synchronous, CPU-bound operations to run in a dedicated thread pool.
```python
# Plate 1
res = await asyncio.to_thread(self.verifier.verify_code, code_sample)

# Plate 2
p1 = await asyncio.to_thread(PoincareManifoldND.project, (0.15, 0.25, 0.05), target_dim=2048)
p2 = await asyncio.to_thread(PoincareManifoldND.project, (-0.10, 0.18, -0.05), target_dim=2048)
centroid = await asyncio.to_thread(self.frechet_aggregator.compute_frechet_mean, [p1, p2], max_iter=100, tol=1e-6)
```

**Recommendation 2: Add Resilient Exception Handling and Proper Cancellation**
Wrap the plate loops and properly await task cancellation.
```python
async def spin_plate_ast_verification(self):
    while self.running:
        try:
            t0 = time.perf_counter()
            # ... execution logic ...
            await asyncio.sleep(2.0)
        except asyncio.CancelledError:
            logger.info("Plate 1 cancelled.")
            raise
        except Exception as exc:
            logger.error(f"Plate 1 crashed: {exc}", exc_info=True)
            self.plates["ast_verifier"].active = False
            await asyncio.sleep(5.0) # Backoff before retry or exit

# In start_spinning_plates:
if duration_sec is not None:
    await asyncio.sleep(duration_sec)
    self.running = False
    for t in tasks:
        t.cancel()
    await asyncio.gather(*tasks, return_exceptions=True)
```

**Recommendation 3: Enforce Sheaf Consistency and Hardware Locks**
Integrate the instantiated but unused components into the plate execution flow.
```python
# In Plate 2 (Poincaré Calibration)
async with self.fleet_lock.acquire("modelload"):
    centroid = await asyncio.to_thread(self.frechet_aggregator.compute_frechet_mean, [p1, p2])
    
    # Enforce sheaf consistency
    local_section = {"centroid_norm": centroid.norm}
    if not self.sheaf_gate.validate(local_section):
        logger.warning("Sheaf consistency violated in Plate 2. Aborting iteration.")
        continue
```

### 4. FINAL ADVERSARIAL VERDICT

**BLOCKED**

The implementation fundamentally fails to deliver on its core architectural and mathematical promises. The "concurrent" plates are serialized by synchronous event-loop blocking; the mathematical claims of 2048D hyperbolic spaces are explicitly violated by 3D projections; and the advanced physics/sheaf components (CTAC, Sheaf Gate, Fleet Lock) are instantiated as dead code. This protocol does not preserve symplectic structure, does not guarantee Fréchet convergence, and does not achieve sovereign hardware utilization. A complete refactor of the asynchronous dispatch logic and mathematical integration is required before this code can be merged.


---
