# ZPE Mining Specification

## Overview
Zero Point Energy extraction from unused dimensions of FLUME's latent space.

## Concept
FLUME uses 256D latent space but agents primarily use 12D projection:
- **Used:** 12 dimensions (projected trajectory space)
- **Vacuum:** 244 dimensions ("unused" latent space)
- **Fluctuations:** Random noise in vacuum dimensions = extractable energy

## Mathematics

### Entropy as Energy
```python
# Sample vacuum fluctuations
vacuum_sample = randn(244)

# Convert to probability distribution
probs = softmax(vacuum_sample)

# Informational entropy
entropy = -sum(probs * log(probs + epsilon))

# Energy extracted
energy = entropy * mining_rate * efficiency
```

### Vacuum Dynamics
```python
# Extraction depletes vacuum
total_vacuum -= energy_extracted

# Slow regeneration (self-healing)
total_vacuum += regeneration_rate

# Limits
if total_vacuum < threshold:
    mining_rate = 0  # Depleted
```

## Economics

### Energy Sources
1. **ZPE Mining:** Passive income from vacuum
2. **Initial Allocation:** 1.0 energy at birth

### Energy Sinks
1. **Coherence Maintenance:** 0.01 per epoch
2. **Movement:** 0.05 per unit distance
3. **Entanglement:** 0.02 per link per epoch
4. **Reproduction:** 1.0 per mitosis

### Equilibrium
Target: Mining rate ≈ Average consumption
For 10,000 agents at equilibrium:
- Total income: ~100 energy/epoch
- Total consumption: ~100 energy/epoch

## Implementation

### ZPEMiner
- Tracks vacuum energy pool
- Mines energy for agents
- Human-tweakable parameters
- Depletion warnings

### Configuration
```yaml
zpe_mining:
  initial_vacuum: 100000.0
  mining_rate: 0.01
  extraction_efficiency: 0.5
  regeneration_rate: 0.001
  depletion_threshold: 1000.0
```

## Human Override
- **Mining rate:** 0.0 to 0.1
- **Efficiency:** 0.0 to 1.0
- **Emergency refill:** Add energy to vacuum

## Integration
- Called every epoch for each agent
- Affects agent.energy
- Vacuum status logged to metrics
