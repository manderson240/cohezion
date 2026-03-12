---
type: antigravity-artifact
session_id: d9c1fcdb-69db-458c-b64a-f26e49625c33
date: 2026-03-04
title: "Architecture Microservices Draft"
aspect: doer
neural:
  activation: 0.331
  stage: embryo
  cluster: Agents
---

# Architecture: FLUME Microservices (Draft)

## Vision
Transition Cohezion from a monolithic "Ball of Mud" to a crystalized array of specialized microservices, governed by the FLUME (Fluid Latent Understanding through Manifold Encoding) protocol.

## Core Services

### 1. Nexus Core (Orchestrator)
- **Role**: The Brain stem. Coordinates state, handles Ouroboros prioritization, and manages the "Heartbeat".
- **Tech**: Python (FastAPI + WebSocket).
- **Responsibility**: 
    - Maintains the 12D System State.
    - Routes signals between Sensorium and Cortex.
    - Hosting the `Gateway` logic.

### 2. Cortex (Intelligence)
- **Role**: The Thinking Machine. dedicated model inference.
- **Tech**: Python (LitServe or vLLM).
- **Responsibility**:
    - **Model Wrangler**: Loads/Unloads agents (Phi-4, Qwen, DeepSeek).
    - **Inference**: Exposes standardized API for "Prompt -> Response".
    - **Task Execution**: Runs `swarm_worker` instances.

### 3. Sensorium (Input/Output)
- **Role**: The Nervous System.
- **Tech**: Rust (for high-thruput) or Python (Async).
- **Responsibility**:
    - **Sheet Watcher**: Polling Google Sheets.
    - **Mission Crawler**: Scraping inputs.
    - **Telemetry**: Broadcasting metrics to Frontend.

### 4. Memory (Substrate)
- **Role**: The Akasha.
- **Tech**: SurrealDB.
- **Responsibility**: 
    - `universe_nodes`: Knowledge Graph.
    - `swarm_tasks`: Global TODO Board.
    - `agent_journeys`: Experience Replay.

## FLUME Protocol (The Bus)
- Agents communicate via **Standardized State Vectors** (12D).
- Instead of "Calling a function", they "Precipitate a Request" into the Memory.
- Specialized Workers pick up requests based on Similarity (R-Zero).

## Migration Path
1.  **Extract Storage**: Ensure all state is in SurrealDB (Done).
2.  **Containerize Cortex**: Isolate LLM loading into a separate process/container.
3.  **Sever Nexus**: Strip `main.py` down to just routing.

## Related Vault Notes

- [[cohezion]]
- [[surrealdb]]
