# SKILL: PROPRIOCEPTIVE_CYBERNETICS_PRIME

## DOMAIN EXPERTISE
Proprioceptive cybernetics, somatosensory mechanoreceptors, corollary discharge, and autopoietic feedback loops. Provides real-time physiological telemetry monitoring over 12-dimensional state vectors ($\mathbf{x}_{\text{proprio}} \in \mathbb{R}^{12}$), muscle spindle rate-limiting $(\Delta L, \dot{L})$ across AST mutations, Golgi Tendon Organ (GTO) tensile load management $(\sigma_{\text{mem}}, \tau_{\text{aperture}}, F_{\text{compute}})$, P0 crossing-time rate reflexes ($t_{\text{cross}} = \frac{M - \text{Floor}}{|\dot{M}|}$), autogenic inhibition for thread shedding, and dynamic variable mechanical impedance modulation.

## KEY TEXTS & CONCEPTS
- **12D Somatosensory State Vector**: $[x, y, z, t, b_1, \dots, b_8]^T$ mapping AST complexity, nesting depth, lexical tokens, delta-time, memory pressure, GTT aperture load, GPU/NPU utilization, process tree strain, and IO bandwidth.
- **Muscle Spindles (Type Ia / II Afferents)**: Monitors AST length $L$ and velocity $\dot{L}$ of code mutations. Enforces critical damping $\zeta \ge 0.707$ to prevent runaway hallucination and oscillatory single-turn rewrites.
- **Golgi Tendon Organs (Ib Afferents)**: Measures tensile stress ($F_{\text{compute}}, \sigma_{\text{mem}}$). Triggers autogenic inhibition to shed speculative threads before catastrophic out-of-memory (OOM) or hardware faults.
- **P0 Rate Reflex & Crossing-Time Protocol**: Derivative-driven anticipatory reflex predicting $t_{\text{cross}} = \frac{M_t - \text{Floor}}{|\dot{M}|}$. If $\dot{M} < -0.8\text{ GiB/s}$ and $t_{\text{cross}} < 15.0\text{s}$, drops speculative load immediately without waiting for static threshold breaches.
- **Corollary Discharge & Efference Copy**: Motor commands emit a forward prediction ticket $\hat{S}_{t+1} = \mathcal{M}(S_t, a_t)$. Realized sensory state $S_{t+1}$ is compared against $\hat{S}_{t+1}$; discrepancy $\delta_{\text{eff}} = \|S_{t+1} - \hat{S}_{t+1}\| > \theta$ triggers a microsecond reflex halt.
- **Variable Mechanical Impedance**: Dynamic mechanical stiffness $K(t)$ and compliance $C(t)$ inversely coupled to somatic stress, tightening exploration into deterministic crystallizations under resource load.
- **Spinal Reflex Isolation Axiom**: Loop 0 protective reflexes must execute synchronously in $<1\text{ ms}$ entirely in local memory, never blocking on async queues, network calls, or database writes.

## INSTRUCTION

1. Sample the 12D somatosensory state vector:
   ```python
   from cohezion.cybernetics.proprioceptive_sensor import ProprioceptiveSensor

   sensor = ProprioceptiveSensor(memory_floor_gib=16.0)
   telemetry = sensor.sample()
   state_12d = telemetry.to_12d_vector()
   print(f"Proprioceptive State: {state_12d}, Stress Level: {telemetry.stress_level.name}")
   ```

2. Register and evaluate the P0 Crossing-Time Rate Reflex:
   ```python
   # The reflex calculates crossing time to prevent memory aperture exhaustion:
   # t_cross = (current_avail - floor) / |dM/dt|
   if telemetry.is_critical:
       print("GTO Autogenic Inhibition: Shedding speculative threads immediately!")
       # Trigger thread drop / memory release synchronously in Loop 0
   ```

3. Issue Corollary Discharge (Efference Copy) and verify sensory return:
   ```python
   # Issue efference copy prediction ticket before action
   predicted_state = sensor.predict_action_impact(action_type="ast_mutation", payload_size_tokens=1024)

   # Execute action
   actual_state = execute_subsystem_action()

   # Measure mismatch
   delta_eff = abs(actual_state.ram_used_gib - predicted_state.ram_used_gib)
   if delta_eff > 1.5:  # Tolerance threshold
       raise SystemHaltError(f"Efference copy mismatch: {delta_eff:.2f} GiB unexpected strain")
   ```

4. Modulate Mechanical Impedance (Stiffness vs. Compliance):
   ```python
   # Compliance C(t) scales inversely with hardware/AST strain:
   compliance = 1.0 - (telemetry.ram_used_gib / telemetry.ram_total_gib)
   exploration_temperature = max(0.1, min(1.0, compliance * 0.8))
   print(f"Operating compliance: {compliance:.3f}, temperature: {exploration_temperature:.2f}")
   ```

## VERSION
v1.0

## SEE ALSO
- `src/cohezion/cybernetics/proprioceptive_sensor.py`
- `scripts/fleet_sentry.py`
- `src/cohezion/skills/allostatica_prime.md`
- `src/cohezion/skills/physics_informed_prediction.md`
