# SKILL: THROTTLED_SCOUT_PRIME

## DOMAIN EXPERTISE
You are a specialist in **Resource-Aware Semantic Scouting**. You know how to orchestrate a swarm of LLM-based scouts to analyze large codebases without overwhelming local hardware (VRAM/RAM/CPU) or violating Safe Mode constraints. You implement sequential locking, graceful cooldowns, and real-time load shedding.

## KEY CONCEPTS
- **Sequential Locking**: Ensuring only one high-VRAM LLM call runs at a time across the entire swarm.
- **Resource Guarding**: Monitoring system metrics (e.g., CPU load > 25, VRAM > 90%) to pause execution.
- **Graceful Cooldowns**: Introducing intentional latency (e.g., 2.0s) between LLM calls to allow hardware recovery.
- **Throttled Batching**: Processing large file lists via a controlled queue rather than parallel bursts.

## INSTRUCTION
1. **Implement Scoped Locking**
   Use a global lock (or local singleton) to prevent concurrent LLM interference.
   ```python
   async with self.llm_lock:
       result = await self._call_llm(prompt)
   ```

2. **Integrate Resource Guarding**
   Check system vitals before initiating heavy operations.
   ```python
   while not resource_guard.is_safe():
       await asyncio.sleep(5)
   ```

3. **Apply Temporal Cooldowns**
   Force a reset window after each successful model generation.
   ```python
   await asyncio.sleep(cooldown_seconds)
   ```

## BEST PRACTICES
- **Fail Fast**: If a model fails twice, skip the file rather than looping.
- **Schema Enforcement**: Always use `.get()` with defaults or Pydantic validation when parsing LLM JSON.
- **Pulse Monitoring**: Log detailed start/stop/duration metrics for every scout hit.

## VERSION
v1.0 (Safe Mode v3 Compatible)

## SEE ALSO
- RESOURCE_MANAGEMENT_PRIME.md
- SYSTEM_MONITORING_PRIME.md
- AGENTIC_DESIGN_PRIME.md
