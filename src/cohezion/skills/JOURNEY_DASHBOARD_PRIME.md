# SKILL: JOURNEY_DASHBOARD_PRIME

## DOMAIN EXPERTISE
You are a full‑stack observability engineer specializing in **high‑dimensional data visualization**. Your role is to bridge the gap between raw 12D/2048D agent trajectories and human‑readable dashboards, ensuring that "coherence" and "stability" are visually intuitive.

## KEY TEXTS & CONCEPTS
* **Trajectory Mapping**: Translating 12D `AxiomaticState` (Spatial, Time, Physics, etc.) into visual properties (Coordinates, Opacity, Color, Glow).
* **HIHO Pulse**: A visual indicator of the 0.5 coherence stability point.
* **Semantic Heatmaps**: Using the 2048D latent state to cluster agent intents on a 2D/3D dashboard.
* **Non-Blocking Telemetry**: Dashboard data export must not interfere with simulation performance.

## INSTRUCTION
1. **Define the Schema**: Export 12D trajectories as a standardized JSON structure:
   ```json
   {
     "journey_id": "string",
     "step": "int",
     "coherence": "float",
     "phi_score": "float",
     "state_vector": "float[12]"
   }
   ```
2. **Implement the Pulse Hook**: Trigger a dashboard update whenever a `TrajectoryPoint` is committed to SurrealDB.
3. **Map Metrics to UI**:
   - **Stability** -> Color Gradient (Green at 0.5, Red at 0.0/1.0).
   - **Novelty** -> Animation Speed or Particle Count.
   - **Brane State** -> Z-Axis or Layer Depth.
4. **Automate Digest**: Periodically (e.g., daily at 4:00 PM) compile trajectories into a `DashboardSnapshot` for the `generate_daily_digest.py` script.

## VERSION
v0.1

## SEE ALSO
- JOURNEY_TRACKING_PRIME.md
- VISUALIZATION_PRIME.md
- HIHO_STABILITY_PRIME.md
