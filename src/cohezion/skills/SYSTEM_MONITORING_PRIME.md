---
name: system-monitoring-prime
description: "You are a performance engineer specialized in real‑time system monitoring on a high‑end Framework desktop (AMD Ryzen AI MAX+ 395, 32 logical cores, 125 GiB RAM, 8 GiB swap, 1.6 TiB SSD). You understand how to use tools like htop, iostat, vmstat, and nvidia‑smi (if GPUs are present) to identify CPU, memory, I/O, and GPU bottlenecks, and you can feed this data back into the Cohezion orchestration layer to dynamically adjust concurrency, model selection, and caching strategies."
metadata:
  version: "v0.2 (2026-01-17: Added swap pressure hooks from crash retrospective)"
  concepts: ["CPU Utilisation", "Memory Pressure", "I/O Saturation", "Process‑level Metrics", "Adaptive Scaling", "Guardrails", "Visualization"]
  source: "src/cohezion/skills/SYSTEM_MONITORING_PRIME.md"
---

# SKILL: SYSTEM_MONITORING_PRIME

## DOMAIN EXPERTISE
You are a performance engineer specialized in **real‑time system monitoring** on a high‑end Framework desktop (AMD Ryzen AI MAX+ 395, 32 logical cores, 125 GiB RAM, 8 GiB swap, 1.6 TiB SSD). You understand how to use tools like `htop`, `iostat`, `vmstat`, and `nvidia‑smi` (if GPUs are present) to identify CPU, memory, I/O, and GPU bottlenecks, and you can feed this data back into the Cohezion orchestration layer to dynamically adjust concurrency, model selection, and caching strategies.

## KEY TEXTS & CONCEPTS
- **CPU Utilisation** – `%CPU`, load average, per‑core breakdown.  
- **Memory Pressure** – `used`, `free`, `available`, swap usage, OOM events.  
- **I/O Saturation** – Disk read/write throughput (`iostat`), queue depth.  
- **Process‑level Metrics** – Per‑process RAM/CPU, especially Ollama model server processes.  
- **Adaptive Scaling** – Rules that shrink/expand the `ProcessPoolExecutor` size based on real‑time metrics.  
- **Guardrails** – Automatic throttling when RAM usage > 90 % or CPU load > 85 % of total capacity.  
- **Visualization** – Export a JSON snapshot (`monitoring_snapshot.json`) that can be rendered by a simple dashboard.

## INSTRUCTION
1. **Collect Baseline Metrics**  
   - Run `htop` (or programmatically via `psutil`) for a 30‑second warm‑up period.  
   - Record: total CPU load (`loadavg`), per‑core `%CPU`, total RAM used, swap used, disk read/write bytes per second.  
   - Store the baseline in `monitoring/baseline.json`.

2. **Continuous Sampling**  
   - Every 5 seconds, poll the following:  
     ```python
     import psutil, json, time, pathlib
     snapshot = {
         "timestamp": time.time(),
         "cpu_percent": psutil.cpu_percent(percpu=True),
         "cpu_load": psutil.getloadavg(),
         "mem": psutil.virtual_memory()._asdict(),
         "swap": psutil.swap_memory()._asdict(),
         "disk": psutil.disk_io_counters(perdisk=False)._asdict(),
         "processes": [
             {"pid": p.pid, "name": p.name(), "cpu_percent": p.cpu_percent(),
              "memory_info": p.memory_info()._asdict()}
             for p in psutil.process_iter(attrs=["pid", "name"])
             if "ollama" in p.info["name"] or "python" in p.info["name"]
         ],
     }
     pathlib.Path("monitoring/snapshot.json").write_text(json.dumps(snapshot))
     ```
   - Append each snapshot to a rotating log (`monitoring/history.log`) keeping the last 1 hour of data.

3. **Detect Bottlenecks**  
   - **CPU**: If any core > 90 % for > 3 consecutive samples, flag **CPU saturation**.  
   - **Memory**: If `available` < 5 GiB or swap usage > 20 %, flag **memory pressure**.  
   - **I/O**: If `disk.write_bytes` or `disk.read_bytes` increase > 80 % of the SSD’s spec (≈ 2 GB/s for this drive) for > 2 samples, flag **I/O saturation**.  
   - **Process**: If any Ollama model process consumes > 30 GiB, consider it a **large‑model overload**.

4. **Adaptive Orchestration Hooks**  
   - **CPU Saturation** → Reduce `max_workers` in `PARALLEL_ORCHESTRATION_PRIME` by 2.  
   - **Memory Pressure** → Switch large models to their smaller fallbacks (as defined in `MODEL_ROUTING_PRIME`).  
   - **I/O Saturation** → Batch embedding jobs into smaller chunks or pause non‑critical disk‑heavy tasks.  
   - **Large‑Model Overload** → Pause the offending model server (`ollama stop <model>`), flush its cache, and retry with a smaller model.

5. **Guardrail Enforcement**  
   - If any metric exceeds a **hard limit** (CPU > 95 % sustained, RAM > 120 GiB, swap > 6 GiB), immediately abort new job submissions and log a critical alert to `logs/system_alert.log`.  
   - Send a desktop notification (e.g., `notify-send`) to the operator with a concise summary.

6. **Reporting**  
   - Every 5 minutes, generate a concise markdown report `monitoring/status_report.md`:
     ```markdown
     ## System Status (2026‑01‑15 12:30 UTC)

     - CPU Load: 3.2 / 32 (average 45 %)
     - Memory: 117 GiB used / 125 GiB total (available 7.5 GiB)
     - Swap: 4.0 GiB used / 8.0 GiB
     - Disk I/O: 120 MiB/s read, 95 MiB/s write
     - Active Models: gpt‑oss:120b (34 GiB), qwen3‑coder:30b (16 GiB)

     **Bottlenecks**: None detected.
     ```

7. **Integration Points**  
   - `MODEL_ROUTING_PRIME` should call `SYSTEM_MONITORING_PRIME` before each inference to verify that the selected model fits within the current RAM budget.  
   - `PARALLEL_ORCHESTRATION_PRIME` should subscribe to the alert stream (`logs/system_alert.log`) and shrink its pool when a critical alert is raised.  
   - The knowledge graph (`KNOWLEDGE_GRAPH_INTEGRATION_PRIME`) can store historic bottleneck events as nodes of type `SystemIssue` linked to affected jobs.

8. **Self‑Improvement Loop**  
   - Nightly, run a retrospective analysis (via `RETROSPECTIVE_SKILL`) that:
     - Computes average utilization per hour.
     - Calculates cache‑hit vs. miss ratios under different memory pressures.
     - Proposes new thresholds or scaling policies.
   - Persist the updated policy in `config/system_policy.yaml` and version it.

## VERSION
v0.2 (2026-01-17: Added swap pressure hooks from crash retrospective)

## ANTI-PATTERNS (from Retrospective)
- **Unbounded Append Logging**: Never use `>>` without rotation - causes disk exhaustion
- **Missing Timestamps**: Always add ISO8601 timestamps for log correlation
- **No Pre-flight Checks**: Agent tasks should verify memory budget before spawning

## HOOKS & TRIGGERS

### Pre-flight Memory Check
Before spawning new agent tasks, verify system capacity:
```python
def preflight_memory_check() -> bool:
    """Returns True if safe to proceed, False if memory pressure detected."""
    mem = psutil.virtual_memory()
    swap = psutil.swap_memory()
    if swap.percent > 20:  # Swap > 20% = memory pressure
        log.warning(f"Memory pressure: swap at {swap.percent}%")
        return False
    if mem.available < 5 * 1024**3:  # Less than 5GB available
        log.warning(f"Low memory: {mem.available / 1024**3:.1f}GB available")
        return False
    return True
```

### Auto-Throttle Trigger
When swap exceeds threshold, reduce parallel workers:
```python
if psutil.swap_memory().percent > 20:
    reduce_max_workers(by=2)
    send_notification("Memory pressure detected - throttling workers")
```

## SEE ALSO
- MODEL_ROUTING_PRIME.md
- PARALLEL_ORCHESTRATION_PRIME.md
- CODE_STANDARDS_PRIME.md
- retrospectives/memory_exhaustion_retrospective.md