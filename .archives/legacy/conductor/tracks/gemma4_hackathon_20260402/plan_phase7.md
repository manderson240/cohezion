# Implementation Plan: Gemma 4 Rich Multimodal Synthesis (Phase 7) - UPDATED

## Objective
To enable Gemma 4 (via `EcoResilienceAgent`) to generate rich multimodal assets—including ecosystem diagrams, resilience map prompts, and sonification parameters—grounded in the official Gemma 4 Model Card technical specifications, and to verify these components through a full simulation run.

## Key Files & Context
- `src/cohezion/knowledge_graph/GEMMA4_MODEL_CARD.md` (New grounding artifact)
- `src/cohezion/agents/ecoresilience_agent.py` (To be updated with multimodal synthesis methods)
- `src/web/anima_dashboard/src/components/EcoResilienceView.tsx` (To be updated to display generated assets)
- `scripts/test_resonance_mission.py` (New script for end-to-end testing)
- https://ai.google.dev/gemma/docs/core/model_card_4 (Official Reference)

## Implementation Steps

### Phase 7: Rich Multimodal Synthesis & Actual Testing
- [ ] **Task: Knowledge Graph Grounding (Gemma 4 Model Card)**
    - [ ] Create `src/cohezion/knowledge_graph/GEMMA4_MODEL_CARD.md` with extracted specs:
        - 256K Context Window support.
        - Hybrid Attention mechanism (Global + Sliding Window).
        - "Thinking Mode" for step-by-step reasoning.
        - Per-Layer Embeddings (PLE) details for on-device optimization.
        - Native audio support in E2B/E4B variants.
    - [ ] Update `MISSION_JOURNAL.md` to reference the new model card grounding.
- [ ] **Task: Gemma 4 Visual Component Synthesis**
    - [ ] Update `EcoResilienceAgent` to generate precise DALL-E/Stable Diffusion prompts for ecosystem "Resilience Maps".
    - [ ] Integrate with `nanobanana` to generate actual images during simulations.
    - [ ] Add a `generate_diagram` method to the agent using Mermaid.js syntax for ecosystem flowcharts.
- [ ] **Task: Sonification Parameter Generation**
    - [ ] Update `EcoResilienceAgent` to output `Tone.js` parameters based on 12D state transitions.
    - [ ] Connect the agent's output to the dashboard's audio engine for "Resonance Sonification".
- [ ] **Task: "Resonance Mission" Execution Script**
    - [ ] Create `scripts/test_resonance_mission.py` to run a full multi-agent scenario.
    - [ ] Generate real assets (Images, Diagrams, Audio Params) during the script execution.
    - [ ] Capture these assets in `src/web/anima_dashboard/public/generated/`.
- [ ] **Task: Final Multimodal Dashboard Validation**
    - [ ] Update `EcoResilienceView.tsx` to display generated images and diagrams.
    - [ ] Perform a full "Night Run" validation to ensure all components resonate.
- [ ] **Task: Conductor - User Manual Verification 'Phase 7: Rich Multimodal Synthesis' (Protocol in workflow.md)**

## Verification & Testing
- **Knowledge Grounding**: Ensure `EcoResilienceAgent` uses the specs from `GEMMA4_MODEL_CARD.md` in its system prompt (e.g., maximizing context usage).
- **Multimodal Generation**: Verify that Gemma 4 produces valid image prompts and Mermaid.js syntax.
- **Image Integration**: Confirm that images generated via `nanobanana` are correctly saved and accessible by the frontend.
- **Dashboard Feedback**: Use the Genesis dashboard to visually and auditorily confirm the simulation's resonance.
- **Mission Success**: Ensure `scripts/test_resonance_mission.py` completes without errors and produces all expected artifacts.
