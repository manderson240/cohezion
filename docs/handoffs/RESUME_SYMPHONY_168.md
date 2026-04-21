# Handoff: Project Symphony-168 & Eigent Integration

## Current System State (as of April 20, 2026)

### 1. Active Mission: Symphony-168
- **Objective**: 7-day (168-hour) autonomous loop combining latent mapping, code self-healing, transient validation, and infrastructure SRE.
- **Agents Active**:
  - `Cartographer` (Manifold Analyst): Mapping 12D topological drift.
  - `Surgeon` (Code Surgeon): Static/Semantic audit of 967 files.
  - `Verifier` (QA Automator): Orchestrating ephemeral test lanes (Ports 8081-8090).
  - `Autonomous SRE` (Reliability Engineer): Reacting to `service_down` events via EventBus.
- **Persistence**: 
  - Hourly checkpoints in `data/eigent/checkpoints/`.
  - Real-time logs in **SurrealDB** (`journey_logs` table).

### 2. Infrastructure Registry (Managed by Fleet Monitor)
| Service | Port | Type | Health URL |
| :--- | :--- | :--- | :--- |
| **SurrealDB** | 8001 | systemd | `http://localhost:8001/health` |
| **Cohezion API** | 8080 | process | `http://localhost:8080/health` |
| **Lemonade Server**| 13307| systemd | `http://localhost:13307/v1/models` |
| **Ollama** | 11434| process | `http://localhost:11434/api/tags` |

### 3. Key Architectural Changes
- **SurrealDB 3.0 Compatibility**: Updated `src/cohezion/core/persistence/surreal_client.py` with robust `live()` query support and 3.0 response parsing.
- **Event-Driven Fleet Monitor**: New service in `src/cohezion/governance/fleet_monitor.py` that bridges SurrealDB Live Queries and the system `EventBus`.
- **Eigent workforce**: API exposed at `/api/eigent/workforce`.

### 4. V-Model Verification Status
- **Harness**: `tests/verify_fleet_monitor_vmodel.py`
- **Result**: **PASSED** (Unit, Module, and System Validation).
- **Verified Invariant**: System correctly reacts to a manual service kill in <100ms via EventBus.

## Resumption Instructions
1.  **Check Services**: `curl http://localhost:8080/api/fleet/status` to confirm the monitor is alive.
2.  **Verify Mission**: `ls -l data/eigent/checkpoints/` to see the latest iteration counts.
3.  **Tail Logs**: `tail -f /tmp/cohezion_api.log` for real-time agent reasoning turns.
4.  **Query Data**:
    ```bash
    echo "SELECT * FROM journey_logs ORDER BY time DESC LIMIT 10;" | surreal sql --endpoint http://localhost:8001 --ns cohezion --db universe
    ```

## Critical Notes
-   **Port 8001 Conflict**: Resolved. Lemonade was moved to 13307 via systemd override. **Do not move it back.**
-   **Missing Dependency**: `camel-ai[eigent]` is installed in the `.venv` but must be checked if the environment is recreated.
