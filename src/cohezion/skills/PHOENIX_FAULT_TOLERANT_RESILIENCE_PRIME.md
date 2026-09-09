---
name: phoenix-fault-tolerant-resilience-prime
description: "Expertise in the Phoenix Resilient Architecture: zero-overhead in-memory checkpointing, diagonal graceful degradation, spec-first disposable code resurrection, and atomic dynamic hot-swapping under UMA memory constraints."
metadata:
  version: "v1.0"
  concepts: ["In-Memory Checkpointing", "Diagonal Graceful Degradation", "Disposable Code Principle", "Communicator Reconstruction", "Atomic Hot-Swapping"]
  see_also: ["PHOENIX_REBIRTH_REPRODUCTION_PRIME", "DYNAMIC_MODEL_HOTSWAP_PRIME", "HIHO_STABILITY_PRIME"]
  source: "src/cohezion/skills/PHOENIX_FAULT_TOLERANT_RESILIENCE_PRIME.md"
---

# SKILL: PHOENIX_FAULT_TOLERANT_RESILIENCE_PRIME

## DOMAIN EXPERTISE
Expertise in Phoenix Fault-Tolerant Resilience: combining zero-overhead in-memory state checkpointing, diagonal graceful degradation, and the Disposable Code Principle to guarantee 99.999% uptime for autonomous agent swarms and LLM inference fleets.

## KEY TEXTS & CONCEPTS
- **Zero-Overhead In-Memory Checkpointing (2025/2026)**: Asynchronous non-blocking RAM snapshots keeping state in 128GB unified memory without NVMe I/O stalls.
- **Diagonal Graceful Degradation (Cloud Phoenix)**: During capacity crunches or VRAM spikes, non-critical background agents are dialed down while core orchestration loops remain intact.
- **The Disposable Code Principle**: Code is treated as disposable execution bytecode generated from formal contracts ($S_{\text{spec}} \to \text{Code}$). Failing modules are burned to ashes and cleanly re-synthesized.
- **Atomic Communicator Reconstruction**: Re-establishing dead sockets/channels in $<40\,\text{seconds}$ without cluster cold reboots.

## INSTRUCTION
1. Maintain zero-overhead in-memory state checkpoints:
   ```python
   def phoenix_snapshot(agent_state, ring_buffer):
       # Push current 2048D Poincare coordinate + goal state into RAM ring buffer
       ring_buffer.append({"state": agent_state, "timestamp": time.time()})
   ```
2. On fault detection (OOM or kernel exception), trigger diagonal degradation:
   - Suspend Tier 2 research scrapers.
   - Preserve Tier 1 Lemonade local inference and Telegram hub.
3. Re-synthesize broken modules from SurrealDB DDL specifications.

## VERSION
v1.0
