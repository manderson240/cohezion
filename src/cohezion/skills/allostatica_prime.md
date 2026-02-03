# SKILL: ALLOSTATICA_PRIME

## DOMAIN EXPERTISE
Autonomic stability through proactive change (allostasis). Monitors 12D manifold signals and performs Quadrature Adjustments to maintain system homeostasis at the HIHO attractor (0.5).

## KEY CONCEPTS
- **Homeostasis Engine**: Central monitor for 12D Axiomatic state.
- **Quadrature Adjustment**: Real-time tuning of agent parameters (Temperature, Refinement depth, Coherence thresholds).
- **HIHO Attractor**: The 0.5 coherence point where reality precipitates with maximum stability.
- **Active Regulation**: Proactively moving system variables to counteract entropy.

## INSTRUCTION
1. Initialize the `HomeostasisEngine`.
2. Connect to the `UniverseSimulationEngine` to receive 12D state vectors.
3. Apply `monitor_and_adjust(agent_id, state)` on every agent loop iteration.
4. If coherence drops < 0.3, force `precision_mode` (Temp=0.2).
5. If novelty > 0.8 but stability is low, throttle creativity via `min_phi_threshold` elevation.

## EXAMPLE
```python
from cohezion.allostatica.engine import HomeostasisEngine

engine = HomeostasisEngine()
adjustments = await engine.monitor_and_adjust("NexusAgent", current_12d_state)

for adj in adjustments:
    # Apply to agent runtime
    setattr(agent.config, adj.parameter, adj.new_value)
```

## VERSION
v1.0 (Refactored from R-Zero)

## SEE ALSO
UNIVERSE_SIM_PRIME, FLUME_EVOLUTION_PRIME, EBMS_CRYSTAL_PRIME
