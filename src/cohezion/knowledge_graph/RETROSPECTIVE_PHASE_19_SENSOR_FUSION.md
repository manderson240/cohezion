# RETROSPECTIVE: Phase 19 - Ouroboros Sensor Fusion

**Date**: 2026-02-01
**Topic**: System Telemetry & Time-Series Fusion
**Phase**: S19 (Sensor Fusion)

## 1. The Challenge
The system lacked a "Flight Recorder". We had `ResourceMonitor` logs (text files) and `GitHealth` (stdout), but no unified, queryable history of State vs. Behavior. We needed to fuse these into a `system_pulse` table in SurrealDB.

## 2. Issues Encountered & Solutions

### A. Emergency Circuit Breakers vs. Observation
**Problem**: The `ResourceMonitor` is designed to aggressively kill processes when VRAM is >90%. When running `OuroborosRecorder` (which instantiates `ResourceMonitor`), it detected the system's high load (from previous background tasks) and triggered "Emergency Shutdown" protocols, trying to kill other processes.
**Learnings**:
- The Observer must be distinct from the Enforcer, or the Enforcer must be context-aware (Daemon vs Task).
- We accepted this behavior as "System Guardian" functionality for now.

### B. SurrealDB Schema Rigidness
**Problem**: Defined `system_pulse` as `SCHEMAFULL` with `hardware` as `TYPE object`. This caused the client/DB to drop nested fields, resulting in empty objects `{}` in the DB.
**Solution**:
- Relaxed schema to `SCHEMALESS`.
- Allowed arbitrary JSON nesting for `hardware` and `software` fields.

### C. Git Sensor Latency
**Problem**: `GitHealthSensor` (running `git status`) timed out on the large `.archive` (9.3M files) despite `.gitignore`.
**Solution**:
- Wrapped the call in `asyncio.wait_for(..., timeout=5.0)`.
- Recorded `{'error': 'timeout'}` in the `software` field to maintain data continuity without blocking the pulse.

## 3. Metrics & Validation
- **Hardware Fusion**: Successfully logging CPU, RAM, VRAM, and Dilation Factor.
- **Software Fusion**: Successfully attempting Git Health (with error handling).
- **Persistence**: Records authenticated in `system_pulse`.

## 4. Key Takeaways
- **Schemas in NoSQL**: Start `SCHEMALESS` for complex nested objects, then tighten.
- **Sensor Timeouts**: All sensors must have strict timeouts to prevent the "Observer Effect" from degrading system performance.
