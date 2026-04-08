# Overnight Mission: The Akashic Sprint (Kaggle/AIMO Horizon)

## Objective
Execute a long-horizon autonomous session to monitor the NVIDIA Nemotron Blackwell sprint and evolve the AIMO Math Reasoning Swarm (MRS) using recently scraped SOTA insights.

## Key Targets
1.  **Monitor Nemotron v28**: Poll `nemotron-lora-blackwell-v28` every 30 minutes.
    *   If `COMPLETE`: Download adapter weights, extract metrics, and log to SurrealDB.
    *   If `ERROR`: Download logs, perform failure analysis using the "Blackwell Handshake" rubric, and prepare a `v29` patch.
2.  **Evolve AIMO MRS (v40)**: Refactor `src/cohezion/compound/aimo_reasoning.py` to include **Weighted Entropy Consensus**.
    *   Implement entropy-based weighting for beam search nodes.
    *   Add "KernelPool" pre-compilation logic (simulated for now).
3.  **ARC-AGI Audit**: Run a background Spinor Symmetry audit on Phase 4 encoders.
4.  **Akashic Logging**: Record hourly 12D snapshots into the SurrealDB knowledge graph.

## Implementation Steps

### 1. Orchestration Script
Create `MISSION_AKASHIC_SPRINT.py` to manage the loop.
- Use `cohezion.integrations.kaggle_api` for polling.
- Use `cohezion.db.surreal_client` for persistence.
- Duration: Until 8:00 AM local time.

### 2. AIMO v40 Logic
- Modify `AIMOScaler` to calculate Shannon Entropy over candidate answer distributions.
- Adjust `evaluate_step` to incorporate uncertainty-based pruning.

### 3. Verification
- Validate script imports.
- Confirm SurrealDB connection.
- Check Kaggle API credentials.

## Success Metrics
- [ ] Nemotron v28 metrics captured or v29 patch staged.
- [ ] `aimo_reasoning.py` updated with Weighted Entropy.
- [ ] 8+ snapshots recorded in SurrealDB.
- [ ] Summary report generated for the user in the morning.
