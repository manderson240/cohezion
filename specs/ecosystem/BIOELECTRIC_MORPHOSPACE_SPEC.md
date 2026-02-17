# Bioelectric Morphospace Specification

## Overview
Michael Levin-inspired bioelectric navigation system where agents move toward "stability wells" using voltage gradients in 12D space.

## Core Concept
Cells (agents) navigate toward preferred morphologies (shapes) using bioelectric voltage gradients:
- **Voltage** = distance from stability well
- **Gradient** = direction to move
- **Force** = magnitude of movement

## Stability Wells

### HIHO_Origin
- Position: [0.5, 0.5, ..., 0.5] (12D)
- Description: Balanced stability (Half-In-Half-Out)
- Preferred by: Juvenile agents (age 0-9)

### Pure_Awareness  
- Position: [1.0, 0, 0, ..., 0]
- Description: Pure consciousness focus
- Preferred by: Elderly agents (age 50+)

### Creative_Mode
- Position: [0.3, 0.8, 0.8, 0.2, 0.9, 0.9, 0.8, 0.8, 0.1, 0.7, 0.6, 0.4]
- Description: High novelty generation
- Preferred by: Young mature (age 10-29)

### Analytical_Mode
- Position: [0.8, 0.2, 0.2, 0.9, 0.1, 0.1, 0.2, 0.2, 0.9, 0.1, 0.9, 0.9]
- Description: Precision and logic
- Preferred by: Prime mature (age 30-49)

## Mathematics

### Voltage Calculation
```python
voltage = tanh(distance * 2 - 1) * well_strength

where:
- distance = ||position - well||
- well_strength = human-tweakable parameter
```

Voltage range:
- -1.0: Far from stability (high force)
- 0.0: Perfect stability (equilibrium)
- 1.0: Too close/unstable

### Gradient Computation
```python
gradient = (well_position - agent_position) / ||well_position - agent_position||
```

### Movement
```python
if voltage < 0:
    move_magnitude = 0.1 * abs(voltage)  # Strong force
else:
    move_magnitude = 0.01  # Weak force

new_position = position + gradient * move_magnitude
```

## Implementation

### BioelectricMorphospace
- Stores well definitions
- Computes voltage/gradient
- Applies bioelectric force
- Human-tweakable parameters

### Integration
- Age determines preferred well
- Energy cost: 0.05 * movement
- Updates every epoch
- Logs voltage history

## Visualization
- **Well centers:** Glowing spheres (color = well type)
- **Voltage field:** Gradient coloring
- **Agent trails:** Paths through morphospace
- **Force vectors:** Arrows showing gradient direction
