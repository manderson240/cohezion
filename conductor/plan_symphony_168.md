# Implementation Plan: Project Symphony-168 (Unified Long-Horizon)

## Background & Motivation
**Symphony-168** is the ultimate demonstration of the Cohezion ecosystem. It combines latent space simulation, codebase self-healing, and autonomous infrastructure management into a single, high-integrity 168-hour journey.

## Objective
To orchestrate a 4-agent workforce running in a closed-loop system for 7 days:
1.  **Cartographer (NPU)**: Continuously simulates the 12D manifold and records topological snapshots.
2.  **Surgeon (GPU)**: Audits the codebase, using the manifold's "complexity attractors" to prioritize targets.
3.  **Verifier (GPU/CPU)**: Spins up transient API instances on different ports to validate refactorings.
4.  **SRE (CPU)**: Monitors the Fleet Monitor; reacts to latency or downtime by rebalancing workloads.

## Key Files & Context
-   `src/cohezion/governance/fleet_monitor.py`: Event-driven health source.
-   `src/cohezion/swarm/agents/eigent_agent.py`: Multi-role logic.
-   `src/cohezion/core/event_bus.py`: Inter-agent communication bus.
-   `data/eigent/checkpoints/`: Persistent state.

## Proposed Solution
### The "Symphony" Loop
1.  **Event-Reaction**: SRE agent subscribes to `SYSTEM_HEALTH` events. If a "Lemonade" lane slows down, it signals the workforce to throttle reasoning.
2.  **Data Flow**: Cartographer snapshots flow into SurrealDB -> Surgeon uses them as "Semantic Context" -> Verifier runs the V-Model.
3.  **Transient Orchestration**: Fleet Monitor will be enhanced to manage "Ephemeral Services" (temporary API mocks for testing).

## Implementation Steps
### 1. Enhance FleetMonitor
-   Add `spawn_ephemeral_service(name, port)` and `reap_service(name)` methods.
-   Implement `sudo systemctl restart` triggers for the SRE agent.

### 2. Upgrade EigentAgent
-   Implement the `SRE` role logic (EventBus subscriber).
-   Implement the `Verifier` role logic (Subprocess pytest execution).
-   Cross-link agents: Agents will now "Wait for Verifier" before marking a code mutation as `verified`.

### 3. Launch Mission
-   Script: `scripts/launch_symphony_168.py`
-   Provisioning: Ensure port range 8081-8090 is reserved for Transient Test Lanes.

## Verification & Testing
1.  **The "Kill Test"**: Manually stop a service and verify the SRE agent detects the event and attempts a recovery.
2.  **Persistence**: Verify SurrealDB `journey_logs` contain inter-agent handshakes (e.g., "Surgeon passed mutation to Verifier").
3.  **Continuity**: Confirm the system resumes correctly after a simulated crash at Hour 1.
