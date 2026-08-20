# Multiperspective Adversarial Review (V2)

*Aggregated from Ollama Cloud (`gpt-oss:120b-cloud`, `kimi-k2.7-code:cloud`) & Local Silicon (`Bonsai-1.7B-gguf`)*

---

## Perspective 1: Security Audit (`gpt-oss:120b-cloud`)
**High‑Severity Findings**

| # | Module & Issue | Why it is Critical | Exploitation Scenario | Recommended Fix |
|---|----------------|--------------------|----------------------|-----------------|
| 1 | **`src/cohezion/core/bidirectional_event_bridge.py` – Correlation‑ID Spoof / Replay** | The bridge treats a `correlation_id` as an opaque token supplied by the *requesting* peer and does **not** bind it to the sender’s identity or enforce a lifetime. An attacker that can publish to the same EventBus can:<br>• Publish a forged reply that re‑uses a valid `correlation_id` from a prior request (replay).<br>• Publish a reply with a *chosen* `correlation_id` that collides with an in‑flight request, causing the original requester to process malicious data as its own response. | 1. Victim A sends `<request, correlation_id=1234>` to the bus.<br>2. Attacker B immediately publishes `<reply, correlation_id=1234, payload=malicious>` before the legitimate responder arrives.<br>3. A matches the reply to its request and processes the malicious payload, leading to arbitrary code execution or data corruption downstream. | * **Bind the ID to the sender** – include the requestor’s node/peer ID inside the envelope and verify it on receipt of a reply.<br>* **One‑time, cryptographically‑random IDs** – generate IDs with at least 128‑bit entropy (e.g., `uuid4().bytes`).<br>* **Expiration / replay cache** – keep a short‑lived (≈30 s) set of seen IDs; reject any reply whose ID is not present or has already been used.<br>* **Optional HMAC** – if the bus is not trusted, sign the whole envelope with a shared secret and verify the signature before processing the payload. |
| 2 | **`src/cohezion/inference/load_safety.py` – Command‑Injection in Kanban Bridge / SurrealDB Persistence** | `defer_to_kanban_on_memory_pressure()` builds a shell command string that interpolates *untrusted* fields (e.g., job name, user‑provided tags) and then executes it with `os.system` / `subprocess.run(..., shell=True)`. The same routine later constructs SurrealDB queries by concatenating the same fields into an SQL‑like string. If an attacker can influence the job description (common in CI pipelines), they can inject arbitrary shell commands **or** arbitrary SurrealDB statements (e.g., `DELETE FROM jobs;`). | 1. Attacker submits a job with name `evil; rm -rf /tmp/*`.<br>2. `defer_to_kanban_on_memory_pressure()` builds: `kanban enqueue --job "evil; rm -rf /tmp/*"` and runs it via `shell=True` → the `rm` runs on the host.<br>3. In the persistence path, the string `DELETE FROM jobs;` is concatenated into a SurrealDB query, wiping the database. | * **Never use `shell=True`** – pass a list of arguments to `subprocess.run` so the OS does not perform a shell parse.<br>* **Whitelist / sanitize inputs** – allow only alphanumeric, hyphen/underscore characters for job‑names, tags, etc., rejecting or escaping anything else.<br>* **Parameterized queries for SurrealDB** – use SurrealDB’s driver bindings (e.g., `db.query("CREATE job SET name = $name", {"name": job_name})`) instead of string interpolation. <br>* **Separate command construction from data** – build a data‑structure (e.g., dict) and let the Kanban client library serialize it, rather than hand‑crafting a CLI string. |
| 3 | **`src/cohezion/inference/lemonade_cli_monitor.py` – Unsanitized Subprocess Output & Event Publishing** | The monitor spawns the external Lemonade CLI with `subprocess.run(..., shell=True, capture_output=True, text=True)` and then forwards the **raw stdout/stderr** straight into an `Event.fleet_status` message. The CLI’s output can be influenced by the environment (e.g., by setting `LEMONADE_STATUS` or by an attacker controlling the Lemonade binary). Because the data is not validated, a maliciously‑crafted status line can embed JSON injection, HTML/JS payloads, or control characters that downstream consumers (web dashboards, log aggregators) will render without escaping, resulting in XSS or log‑injection attacks. | 1. Attacker replaces the Lemonade binary with a wrapper that prints `{"fleet":"<script>alert(1)</script>"}`.<br>2. The monitor receives the string and publishes it as `fleet_status`.<br>3. A downstream web UI that blindly `JSON.parse`s and injects the value into the DOM renders the script, achieving XSS. | * **Run the CLI without a shell** – `subprocess.run([binary_path, "--status"], capture_output=True, text=True, check=True)`.<br>* **Validate / whitelist the schema** – parse the output with a strict schema (e.g., `pydantic` model) and reject any fields that do not conform to expected types/lengths.<br>* **Escape before publishing** – if the event bus forwards the payload to text‑based sinks, ensure characters like `<`, `>`, `'`, `"` are JSON‑escaped or HTML‑escaped at the point of injection.\n* **Signature verification** – optionally sign the CLI binary and verify its checksum at startup to prevent binary substitution. |

---

### General Guidance for All Findings
1. **Defense‑in‑Depth** – combine input validation, proper API usage (no `shell=True`), and cryptographic guarantees (signatures/HMACs).  
2. **Unit‑Test Coverage** – add tests that attempt to replay a `correlation_id`, inject shell metacharacters, and feed malformed CLI output; ensure the system rejects them.  
3. **Audit Logging** – record rejected correlation IDs, command‑injection attempts, and malformed status payloads with source IP / peer ID to enable rapid incident response.  

Implementing the patches above will close the attack surface that currently allows remote attackers to hijack RPC flows, execute arbitrary host commands, corrupt the SurrealDB store, and inject malicious payloads into fleet‑status events—each a **High** severity vector.

---

## Perspective 2: Concurrency & Memory Audit (`kimi-k2.7-code:cloud`)
## Finding 1 — TOCTOU race in `defer_to_kanban_on_memory_pressure()`  
**Modules:** `src/cohezion/inference/load_safety.py` (triggered by `lemonade_cli_monitor.py` bursts)

**Issue:** The memory-pressure read and the kanban enqueue are separate, unguarded steps. Under high load, N workers can simultaneously see “memory OK” (or the same queue depth) and all defer, oversubscribing kanban or deferring the same task repeatedly.

**Fix:** Wrap the decision + enqueue in a single lock and make deferral idempotent/bounded.

```python
_lock = asyncio.Lock()
_deferred_ids = weakref.WeakSet()  # or TTL-set of task ids


async def defer_to_kanban_on_memory_pressure(task, threshold_gb=2.0, max_q=1000):
    async with _lock:
        # idempotency + bounded queue + cooldown/hysteresis
        if task.id in _deferred_ids or kanban.qsize() >= max_q:
            return False
        if available_memory_gb() < threshold_gb:
            await kanban.defer(task)
            _deferred_ids.add(task.id)
            return True
    return False
```

Also add cooldown/hysteresis so the system doesn’t flap around the threshold.

---

## Finding 2 — EventBus consumer deadlock on request–reply futures  
**Modules:** `src/cohezion/core/bidirectional_event_bridge.py`

**Issue:** If an EventBus handler calls `bridge.request(...)` and awaits the reply future, the reply event can never be dispatched because the same event-bus consumer thread/loop is blocked waiting for the handler to complete.

**Fix:** Never block the bus handler on the RPC future. Offload the request–reply wait to a background task, and always use a timeout.

```python
async def on_bus_event(evt):
    # hand off so the consumer can keep dispatching replies
    asyncio.create_task(_handle_with_rpc(evt))


async def _handle_with_rpc(evt):
    try:
        result = await bridge.request(evt.payload, timeout=5.0)
    except asyncio.TimeoutError:
        logger.warning("RPC reply timed out", exc_info=True)
```

The bridge itself must keep reply handling on a path independent of any blocked requester.

---

## Finding 3 — Memory leak / unsafe `_pending_requests` map  
**Modules:** `src/cohezion/core/bidirectional_event_bridge.py`

**Issue:** `_pending_requests` can grow unbounded if replies are lost, the caller is cancelled, or the bridge is shut down without cleanup. Concurrent access from sender and reply handler is also unsafe without synchronization.

**Fix:** Protect the map, pop entries in `finally`, cancel stale futures, and drain on shutdown.

```python
class BiDirectionalEventBridge:
    def __init__(self):
        self._pending: dict[str, asyncio.Future] = {}
        self._lock = asyncio.Lock()

    async def request(self, payload, timeout=10.0):
        cid = uuid.uuid4().hex
        fut = asyncio.get_running_loop().create_future()
        async with self._lock:
            self._pending[cid] = fut
        try:
            await self.bus.publish(Request(correlation_id=cid, payload=payload))
            return await asyncio.wait_for(fut, timeout=timeout)
        finally:
            async with self._lock:
                self._pending.pop(cid, None)

    def on_reply(self, event):
        with threading.RLock():  # if bus may call back cross-thread
            fut = self._pending.pop(event.correlation_id, None)
        if fut and not fut.done():
            loop = fut.get_loop()
            loop.call_soon_threadsafe(fut.set_result, event.payload)

    async def close(self):
        async with self._lock:
            for fut in self._pending.values():
                if not fut.done():
                    fut.cancel()
            self._pending.clear()
```

Also add a periodic TTL sweeper to cancel futures whose replies never arrive.

---

**Note:** `src/cohezion/flume/scalar_manifold_coordinates.py` appears to be a pure, stateless math function (`C_0.5 = max(0.0, 1.0 - 2.0*|c-0.5|)`). It has no shared mutable state and is safe under concurrent execution unless a mutable cache is added later.

---

## Perspective 3: Physics & FLUME Manifold Audit (`Bonsai-1.7B-gguf`)
1. **Mathematical Derivative Continuity at c = 0.5**:  
   The function `C_0.5 = max(0.0, 1.0 - 2.0 * |c - 0.5|)` is a scalar manifold stability bound. At `c = 0.5`, the derivative of `C_0.5` with respect to `c` is zero, indicating a **kink** in the manifold's stability. This suggests that the manifold may be unstable at the critical point `c = 0.5`, potentially leading to **numerical instability** or **singular behavior**. A recommendation would be to **validate the derivative continuity** at `c = 0.5` to ensure that the manifold's stability is consistent with the given formula.

2. **Numerical Underflow in P_precip**:  
   The formula `P_precip = C_0.5 * exp(-entropy)` introduces a **numerical underflow** if `entropy` is very large, leading to a very small `P_precip`. This is a concern for **numerical stability** in high-entropy scenarios. A recommendation would be to **validate the entropy input** and **use a robust numerical stability check** (e.g., Taylor expansion or logarithmic scaling) to prevent underflow and ensure numerical accuracy.

3. **12D Manifold Stability Bounds Under High Entropy Gradients**:  
   The `C_0.5` scalar is used to define a stability bound for the 12D manifold. Under high entropy gradients, the exponential term `exp(-entropy)` becomes very small, which can cause **numerical underflow** in the stability calculation. A recommendation would be to **use a more robust stability check** that accounts for high entropy, such as **logarithmic scaling** or **adaptive stability bounds** that adjust based on entropy values, to maintain numerical integrity and avoid underflow.
