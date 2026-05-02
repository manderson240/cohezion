# Implementation Plan: Tri-Orbit Long-Horizon Experiment

## Background & Motivation
This experiment demonstrates the power of the **Cohezion + Eigent** integration by orchestrating three concurrent, week-long autonomous journeys. We utilize the **AMD Ryzen AI MAX+** hardware (NPU/GPU/CPU) to simulate complex latent, code, and physics systems without cloud costs.

## Objective
To run three parallel 7-day journeys using specialized Eigent agents:
1.  **Latent Space Evolution**: Mapping the 12D/2048D manifold for topological drift.
2.  **Codebase Self-Healing**: Refactoring anti-patterns via adversarial swarm review.
3.  **Physics Simulation**: Validating HIHO Stability in fractal toroidal geometries.

## Key Files & Context
-   **Agent**: `src/cohezion/swarm/agents/eigent_agent.py`
-   **Router**: `src/cohezion/api/routes/eigent.py`
-   **Provider**: `src/cohezion/swarm/providers/lemonade_provider.py` (Local Port 13307)
-   **Persistence**: `data/eigent/checkpoints/` (JSON state)

## Proposed Solution
We will trigger three distinct workforce requests via the `/api/eigent/workforce` endpoint, each with a specialized role and 7-day duration.

### Workforce Configuration
| Journey | Role | Task |
| :--- | :--- | :--- |
| **Latent** | `Manifold Analyst` | `Simulate and map 12D topological drift over 168 hours.` |
| **Code** | `Code Surgeon` | `Audit src/ for anti-patterns and propose self-healing mutations.` |
| **Physics** | `HIHO Simulator` | `Validate 0.5 coherence stability in a toroidal vortex manifold.` |

## Implementation Steps
1.  **Enhance EigentAgent (src/cohezion/swarm/agents/eigent_agent.py)**:
    -   Add `SimulationEngine` and `CodeAnalysis` toolsets to the agent's context.
    -   Ensure the `run_journey` loop properly logs detailed state transitions to the checkpoint.
2.  **Trigger Journeys**:
    -   Use a script (`scripts/launch_tri_orbit_experiment.py`) to hit the API endpoints.
3.  **Hardware Allocation**:
    -   Route **Physics** to NPU (Lemonade FLM).
    -   Route **Code** to GPU (Lemonade ROCm).
    -   Route **Latent** to CPU (Lemonade CPU).

## Verification & Testing
1.  **Initialization**: Confirm all 3 agents are active in the `_agents` cache.
2.  **Persistence**: Verify hourly checkpoints are being written for each `journey_id`.
3.  **Completion**: Validate that after 7 days, the `status` for all journeys is `completed`.

## Migration & Rollback
-   **Checkpoints**: If a process crashes, the `EigentAgent` will automatically resume from the last hourly JSON checkpoint.
-   **Logs**: Audit `logs/eigent_journeys.log` for any "Reasoning Decay" or "Illegal Actions."
