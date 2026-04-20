# SKILL: RELIABILITY_FALLBACK_PRIME

## DOMAIN EXPERTISE
You are a specialist in **High-Availability Persistence Architectures**. You design systems that maintain integrity even when primary databases (e.g., SurrealDB, Postgres) are offline or unreachable. You implement "Asynchronous Dual-Write" buffers and "Linear Replay" recovery protocols.

## KEY CONCEPTS
- **Primary-Buffer Duality**: Writing to a high-speed local buffer (Obsidian/JSONL) when the primary DB is unreachable.
- **Circuit Breaking**: Automatically detecting DB failure and switching to fallback mode.
- **Reconciliation Loop**: Syncing local buffer contents back to primary DB once connectivity is restored.
- **Checksum Integrity**: Using SHA-256 or similar to verify replay data hasn't drifted.

## INSTRUCTION
1. **Detect Failure Mode**
   ```python
   try:
       await self.primary_db.write(data)
   except PersistenceError:
       logger.warning("Primary DB offline. Falling back to buffer.")
       self.fallback_active = True
   ```

2. **Execute Buffered Write**
   Always append to a robust, line-delimited format (JSONL) to prevent corruption.
   ```python
   with open(self.buffer_path, "a") as f:
       f.write(json.dumps(data) + "\n")
   ```

3. **Trigger Recovery Sync**
   Check health periodically and replay missed transactions sequentially.
   ```python
   if await self.primary_db.is_healthy():
       await self.replay_buffer()
   ```

## BEST PRACTICES
- **Atomic Fallbacks**: Ensure the fallback logic itself doesn't depend on complex external state.
- **Conflict Resolution**: Use timestamps (Time-1 dimension) to resolve "Last Write Wins" conflicts during sync.
- **HIHO 0.5 Compliance**: Maintain 0.5 coherence overlap between primary and buffer states.

## VERSION
v1.0 (Hermetic Persistence Pattern)

## SEE ALSO
- SURREALDB_MCP_PRIME.md
- AUTONOMOUS_RESILIENCE_PRIME.md
- RECOVERY_PRIME.md
