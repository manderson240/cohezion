# Expansion Plan: Gemma 4 & EcoResilience Synthesis (Phase 5+)

## Objective
To evolve the existing Gemma 4 & EcoResilience track from a functional prototype into a production-grade, swarm-integrated, and data-grounded simulation engine for the Cohezion ecosystem.

## Key Files & Context
- `conductor/tracks/gemma4_hackathon_20260402/plan.md` (Original plan)
- `src/cohezion/agents/ecoresilience_agent.py` (Implementation from Phase 3)
- `src/web/anima_dashboard/` (Genesis dashboard for visualization)
- `src/cohezion/providers/gemma4.py` (Gemma 4 provider)
- `conductor/tracks.md` (Tracks registry)

## Implementation Steps

### Phase 5: Advanced Resonance & Swarm Integration
- [ ] **Task: Multi-Agent Resonance Loop (Swarm)**
    - [ ] Create `tests/swarm/test_ecoresilience_swarm_loop.py` for collaborative tasks.
    - [ ] Implement a specialized `SwarmOrchestrator` sub-protocol where `EcoResilienceAgent` (Gemma 4) leads a trio with `PhysicsAgent` (Ollama) and `BiologistAgent` (Mistral).
    - [ ] Define the "Resonance Protocol" for cross-agent 12D state vector sharing.
    - [ ] Verify coherence with `HIHOStabilityResolver`.
- [ ] **Task: Real-world Data Grounding (Data)**
    - [ ] Design and implement `src/cohezion/mcp/env_data_mcp.py` to fetch real-time data from NOAA and Copernicus APIs.
    - [ ] Update `EcoResilienceAgent` to use this MCP server for "Ground Truth" grounding during simulations.
    - [ ] Write integration tests for data-driven agent reasoning.
- [ ] **Task: Anima Dashboard Genesis Integration (Visual)**
    - [ ] Create `src/web/anima_dashboard/components/EcoResilienceView.tsx` in the Next.js frontend.
    - [ ] Implement real-time Three.js visualization for 12D manifold trajectories and HIHO stability indicators.
    - [ ] Add SSE (Server-Sent Events) streaming from the `ecoresilience` API endpoint to the dashboard.
- [ ] **Task: Gemma 4 QLoRA Specialization (ML)**
    - [ ] Prepare a training dataset from the `cohezion/knowledge_graph/` and `cohezion/physics/` domains.
    - [ ] Set up a QLoRA fine-tuning script `scripts/ml/finetune_gemma4_cohezion.py` (compatible with the G4 Blackwell/AMD setup).
    - [ ] Evaluate the fine-tuned model against the baseline for "Unified Physics" reasoning and TEK synthesis.
- [ ] **Task: Conductor - User Manual Verification 'Phase 5: Advanced Resonance & Swarm Integration' (Protocol in workflow.md)**

## Verification & Testing
- **Swarm Tests**: Run collaborative agent scenarios to ensure zero-lock resonance.
- **Data Tests**: Verify that the MCP server correctly fetches and parses NOAA/Copernicus data.
- **UI Tests**: Perform Playwright E2E tests for the Genesis dashboard view.
- **ML Evaluation**: Use the `QualityBenchmarkReport` to compare the specialized Gemma 4 model against the generic version.
