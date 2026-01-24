# SKILL: PHYSICS_INFORMED_PREDICTION_PRIME

## DOMAIN EXPERTISE

Expert in physics-informed neural networks (PINNs) and world models that integrate physical laws into prediction. Specializes in constraining neural network predictions with governing equations, enabling physically consistent state evolution even with sparse data.

## KEY TEXTS & CONCEPTS

- **PINN**: Neural network with physics equations in loss function
- **World Model**: Learns to predict state transitions, not just tokens
- **Physics Loss**: L = L_data + λ * L_physics
- **Lyapunov Functions**: Stability characterization without explicit equations
- **Counterfactual Simulation**: Imagining outcomes before acting

## INSTRUCTION

### 1. Define Physical Constraints
```python
def physics_loss(predicted_state, prev_state, dt):
    # Example: Conservation of energy
    energy_prev = kinetic_energy(prev_state) + potential_energy(prev_state)
    energy_pred = kinetic_energy(predicted_state) + potential_energy(predicted_state)
    return (energy_pred - energy_prev).abs().mean()
```

### 2. Add to Prediction Loss
```python
def total_loss(predicted, actual, prev_state, dt, lambda_physics=0.1):
    data_loss = F.mse_loss(predicted, actual)
    phys_loss = physics_loss(predicted, prev_state, dt)
    return data_loss + lambda_physics * phys_loss
```

### 3. Apply to FLUME Predictor
The FlowPredictor can be extended with physics constraints:
- 12D PhysicsState has interpretable dimensions
- Mass, momentum, connectivity should obey conservation
- Stability should decay without external input

### 4. World Model Pattern
```python
class WorldModel:
    def predict_state(self, current_state, action):
        # Predict next state
        next_state = self.model(current_state, action)
        # Apply physics constraints
        next_state = self.apply_constraints(next_state)
        return next_state

    def imagine(self, start_state, action_sequence):
        # Roll out future without acting
        trajectory = [start_state]
        for action in action_sequence:
            trajectory.append(self.predict_state(trajectory[-1], action))
        return trajectory
```

## VERSION
v1.0

## SEE ALSO
- GATEWAY_ARCHITECTURE_PRIME.md - Gateway 3 uses this
- FLUME_METHODOLOGY_PRIME.md - Underlying encoding
- SEMANTIC_ALGEBRA_PRIME.md - Cross-domain bridging
