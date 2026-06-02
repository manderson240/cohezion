---
name: swarm_synthesis
description: High-Dimensional Consensus and Outlier Detection.
keywords:
- centroid
- coherence metric
- outlier rejection
- swarm
- synthesis
- vector consensus
---

# SKILL: SWARM_SYNTHESIS_PRIME

## DOMAIN EXPERTISE
High-Dimensional Consensus and Outlier Detection.
This skill enables the aggregation of inputs from multiple agents into a single, high-coherence "Swarm Vector," filtering out hallucinations and dissenting outliers to achieve super-human reliability.

## KEY TEXTS & CONCEPTS
- **Vector Consensus**: Averaging semantics rather than voting on text.
- **Centroid**: The geometric center of the thought swarm.
- **Outlier Rejection**: Discarding vectors that are structurally distant from the consensus.
- **Coherence Metric**: Inverse of the swarm's variance/spread.

## INSTRUCTION

### 1. Vector Collection
Collect `N` thought vectors (`z`) from `N` agents answering the same prompt.
```python
vectors = [agent.thought_vector for agent in swarm]
```

### 2. Centroid Calculation
Compute the robust mean of the vectors.
```python
centroid = torch.mean(torch.stack(vectors), dim=0)
```

### 3. Outlier Filtration
Calculate Euclidean distance of each vector from the centroid.
- If `distance > mean_distance + 2 * std_dev`, flag as outlier.
- Re-calculate centroid without outliers.

### 4. Synthesis
Decode the final centroid vector into text.
```python
consensus_thought = decoder.decode(final_centroid)
```

### 5. Coherence Scoring
Report swarm coherence:
- `coherence = 1.0 / (average_distance_to_centroid + epsilon)`

## VERSION
v1.0
